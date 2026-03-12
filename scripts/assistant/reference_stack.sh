#!/bin/bash
# Manage a bootstrapped self-host assistant reference stack.

set -euo pipefail

RUNTIME_DIR=""
COMMAND=""
TAIL_LINES="40"

usage() {
  cat <<'EOF'
Assistant Reference Stack

Usage:
  bash scripts/assistant/reference_stack.sh --runtime-dir DIR <start|stop|restart|status|logs> [component]

Commands:
  start     Start assistant-api, assistant-web, worker, and Telegram polling when enabled
  stop      Stop every stack component started from this runtime dir
  restart   Stop and then start the stack
  status    Show per-component state and log paths
  logs      Tail stack logs (all components or one component name)

Telegram mode:
  ASSISTANT_RUNTIME_TELEGRAM_MODE=auto      start Telegram only when a bot token is present
  ASSISTANT_RUNTIME_TELEGRAM_MODE=enabled   require a bot token and start Telegram polling
  ASSISTANT_RUNTIME_TELEGRAM_MODE=disabled  never start Telegram polling

Operator mode:
  ASSISTANT_RUNTIME_OPERATOR_MODE=self-host            local reference-stack defaults
  ASSISTANT_RUNTIME_OPERATOR_MODE=managed-quickstart   same runtime path with hosted-ready env/secret contract
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --runtime-dir)
      RUNTIME_DIR="${2:?missing value for --runtime-dir}"
      shift 2
      ;;
    --tail-lines)
      TAIL_LINES="${2:?missing value for --tail-lines}"
      shift 2
      ;;
    start|stop|restart|status|logs)
      COMMAND="$1"
      shift
      break
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$RUNTIME_DIR" ]]; then
  CANDIDATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "$CANDIDATE_DIR/assistant-runtime.env" ]]; then
    RUNTIME_DIR="$CANDIDATE_DIR"
  else
    echo "--runtime-dir is required when assistant-runtime.env is not next to this script." >&2
    exit 1
  fi
fi

if [[ -z "$COMMAND" ]]; then
  COMMAND="start"
fi

RUNTIME_DIR="$(cd "$RUNTIME_DIR" && pwd)"
ENV_FILE="$RUNTIME_DIR/assistant-runtime.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "assistant runtime env not found: $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

RUN_DIR="$ASSISTANT_RUNTIME_STATE_DIR/run"
LOG_DIR="$ASSISTANT_RUNTIME_STATE_DIR/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"

component_pid_path() {
  local component="$1"
  echo "$RUN_DIR/$component.pid"
}

component_log_path() {
  local component="$1"
  echo "$LOG_DIR/assistant-$component.log"
}

read_pid() {
  local pid_path="$1"
  if [[ -f "$pid_path" ]]; then
    tr -d '[:space:]' < "$pid_path"
  fi
}

is_pid_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
}

cleanup_stale_pid() {
  local component="$1"
  local pid_path
  pid_path="$(component_pid_path "$component")"
  local pid
  pid="$(read_pid "$pid_path")"
  if [[ -n "$pid" ]] && ! is_pid_running "$pid"; then
    rm -f "$pid_path"
  fi
}

component_pid() {
  local component="$1"
  cleanup_stale_pid "$component"
  read_pid "$(component_pid_path "$component")"
}

component_is_running() {
  local component="$1"
  local pid
  pid="$(component_pid "$component")"
  is_pid_running "$pid"
}

wait_for_http() {
  local url="$1"
  local timeout_seconds="${2:-20}"
  python3 - "$url" "$timeout_seconds" <<'PY'
from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request

url = sys.argv[1]
deadline = time.time() + float(sys.argv[2])
last_error = "no response"

while time.time() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:  # noqa: S310
            if 200 <= response.status < 400:
                raise SystemExit(0)
            last_error = f"unexpected status {response.status}"
    except urllib.error.HTTPError as exc:
        if 200 <= exc.code < 400:
            raise SystemExit(0)
        last_error = f"unexpected status {exc.code}"
    except Exception as exc:  # pragma: no cover - shell helper
        last_error = str(exc)
    time.sleep(0.2)

print(last_error, file=sys.stderr)
raise SystemExit(1)
PY
}

wait_for_process() {
  local component="$1"
  local timeout_seconds="${2:-10}"
  python3 - "$timeout_seconds" "$(component_pid_path "$component")" <<'PY'
from __future__ import annotations

import os
import pathlib
import signal
import sys
import time

deadline = time.time() + float(sys.argv[1])
pid_path = pathlib.Path(sys.argv[2])

while time.time() < deadline:
    if pid_path.exists():
        raw_pid = pid_path.read_text(encoding="utf-8").strip()
        if raw_pid:
            try:
                os.kill(int(raw_pid), 0)
            except OSError:
                pass
            else:
                raise SystemExit(0)
    time.sleep(0.2)

raise SystemExit(1)
PY
}

show_log_tail() {
  local component="$1"
  local log_path
  log_path="$(component_log_path "$component")"
  if [[ -f "$log_path" ]]; then
    echo "--- ${component} log tail ---" >&2
    tail -n "$TAIL_LINES" "$log_path" >&2 || true
  fi
}

assistant_api_local_base_url() {
  echo "http://127.0.0.1:${ASSISTANT_RUNTIME_API_PORT}"
}

show_deployment_contract() {
  python3 "$ASSISTANT_RUNTIME_REPO_ROOT/scripts/assistant/deployment_contract.py" --format status
}

stop_component() {
  local component="$1"
  local pid_path
  pid_path="$(component_pid_path "$component")"
  local pid
  pid="$(read_pid "$pid_path")"
  if [[ -z "$pid" ]]; then
    rm -f "$pid_path"
    echo "$component: stopped"
    return
  fi

  if is_pid_running "$pid"; then
    kill "$pid" >/dev/null 2>&1 || true
    wait "$pid" 2>/dev/null || true
  fi
  rm -f "$pid_path"
  echo "$component: stopped"
}

stack_component_names() {
  printf '%s\n' api web worker
}

telegram_mode() {
  local raw_mode="${ASSISTANT_RUNTIME_TELEGRAM_MODE:-auto}"
  local normalized_mode
  normalized_mode="$(printf '%s' "$raw_mode" | tr '[:upper:]' '[:lower:]')"
  case "$normalized_mode" in
    auto)
      echo "auto"
      ;;
    1|true|yes|on|enabled|polling)
      echo "enabled"
      ;;
    0|false|no|off|disabled)
      echo "disabled"
      ;;
    *)
      echo "invalid"
      ;;
  esac
}

telegram_should_start() {
  local mode
  mode="$(telegram_mode)"
  case "$mode" in
    enabled)
      if [[ -z "${ASSISTANT_API_TELEGRAM_BOT_TOKEN:-}" ]]; then
        echo "ASSISTANT_RUNTIME_TELEGRAM_MODE=enabled requires ASSISTANT_API_TELEGRAM_BOT_TOKEN." >&2
        exit 1
      fi
      return 0
      ;;
    disabled)
      return 1
      ;;
    auto)
      [[ -n "${ASSISTANT_API_TELEGRAM_BOT_TOKEN:-}" ]]
      ;;
    *)
      echo "invalid ASSISTANT_RUNTIME_TELEGRAM_MODE: ${ASSISTANT_RUNTIME_TELEGRAM_MODE:-}" >&2
      exit 1
      ;;
  esac
}

telegram_disabled_reason() {
  local mode
  mode="$(telegram_mode)"
  case "$mode" in
    enabled)
      if [[ -z "${ASSISTANT_API_TELEGRAM_BOT_TOKEN:-}" ]]; then
        echo "enabled but missing ASSISTANT_API_TELEGRAM_BOT_TOKEN"
      else
        echo "enabled"
      fi
      ;;
    disabled)
      echo "disabled by ASSISTANT_RUNTIME_TELEGRAM_MODE"
      ;;
    auto)
      if [[ -z "${ASSISTANT_API_TELEGRAM_BOT_TOKEN:-}" ]]; then
        echo "auto-disabled until ASSISTANT_API_TELEGRAM_BOT_TOKEN is set"
      else
        echo "auto"
      fi
      ;;
    *)
      echo "invalid ASSISTANT_RUNTIME_TELEGRAM_MODE=${ASSISTANT_RUNTIME_TELEGRAM_MODE:-}"
      ;;
  esac
}

start_component() {
  local component="$1"
  local runner="$RUNTIME_DIR/run-assistant-$component.sh"
  local log_path
  log_path="$(component_log_path "$component")"
  local pid_path
  pid_path="$(component_pid_path "$component")"

  if [[ ! -x "$runner" ]]; then
    echo "Missing component launcher: $runner" >&2
    exit 1
  fi

  if component_is_running "$component"; then
    echo "$component: already running (pid=$(component_pid "$component"))"
    return
  fi

  "$runner" >"$log_path" 2>&1 &
  local pid=$!
  echo "$pid" > "$pid_path"
  echo "$component: started (pid=$pid)"
}

verify_component() {
  local component="$1"
  case "$component" in
    api)
      wait_for_http "$(assistant_api_local_base_url)/openapi.json" 20 || {
        show_log_tail "$component"
        return 1
      }
      ;;
    web)
      wait_for_http "http://127.0.0.1:${ASSISTANT_RUNTIME_WEB_PORT}/" 20 || {
        show_log_tail "$component"
        return 1
      }
      ;;
    worker|telegram)
      wait_for_process "$component" 10 || {
        show_log_tail "$component"
        return 1
      }
      ;;
    *)
      echo "Unknown component: $component" >&2
      return 1
      ;;
  esac
}

start_stack() {
  local started_components=()
  for component in api web worker; do
    if ! component_is_running "$component"; then
      started_components+=("$component")
    fi
    start_component "$component"
    verify_component "$component" || {
      echo "Failed to verify $component startup." >&2
      for started_component in "${started_components[@]}"; do
        stop_component "$started_component" >/dev/null 2>&1 || true
      done
      exit 1
    }
  done

  local telegram_reason
  telegram_reason="$(telegram_disabled_reason)"
  if telegram_should_start; then
    if ! component_is_running telegram; then
      started_components+=("telegram")
    fi
    start_component telegram
    verify_component telegram || {
      echo "Failed to verify telegram startup." >&2
      for started_component in "${started_components[@]}"; do
        stop_component "$started_component" >/dev/null 2>&1 || true
      done
      exit 1
    }
  else
    stop_component telegram >/dev/null 2>&1 || true
    echo "telegram: skipped (${telegram_reason})"
  fi

  echo "reference-stack: running"
  echo "assistant-api: ${ASSISTANT_API_PUBLIC_BASE_URL}"
  echo "assistant-api-local: $(assistant_api_local_base_url)"
  echo "assistant-web: http://127.0.0.1:${ASSISTANT_RUNTIME_WEB_PORT}"
  echo "worker log: $(component_log_path worker)"
  echo "telegram log: $(component_log_path telegram)"
  show_deployment_contract
}

stop_stack() {
  for component in telegram worker web api; do
    stop_component "$component"
  done
  echo "reference-stack: stopped"
}

status_stack() {
  local stack_status="running"
  for component in api web worker; do
    if component_is_running "$component"; then
      echo "$component: running pid=$(component_pid "$component") log=$(component_log_path "$component")"
    else
      stack_status="degraded"
      echo "$component: stopped log=$(component_log_path "$component")"
    fi
  done

  if component_is_running telegram; then
    echo "telegram: running pid=$(component_pid telegram) log=$(component_log_path telegram)"
  else
    local telegram_reason
    telegram_reason="$(telegram_disabled_reason)"
    echo "telegram: disabled reason=${telegram_reason} log=$(component_log_path telegram)"
  fi

  echo "reference-stack: ${stack_status}"
  echo "assistant-api: ${ASSISTANT_API_PUBLIC_BASE_URL}"
  echo "assistant-api-local: $(assistant_api_local_base_url)"
  echo "assistant-web: http://127.0.0.1:${ASSISTANT_RUNTIME_WEB_PORT}"
  show_deployment_contract
}

show_logs() {
  if [[ $# -gt 0 ]]; then
    local component="$1"
    local log_path
    log_path="$(component_log_path "$component")"
    if [[ ! -f "$log_path" ]]; then
      echo "log file not created yet: $log_path"
      return 0
    fi
    tail -n "$TAIL_LINES" "$log_path"
    return
  fi

  for component in api web worker telegram; do
    local log_path
    log_path="$(component_log_path "$component")"
    echo "--- ${component} (${log_path}) ---"
    if [[ -f "$log_path" ]]; then
      tail -n "$TAIL_LINES" "$log_path"
    else
      echo "log file not created yet"
    fi
  done
}

case "$COMMAND" in
  start)
    start_stack
    ;;
  stop)
    stop_stack
    ;;
  restart)
    stop_stack
    start_stack
    ;;
  status)
    status_stack
    ;;
  logs)
    show_logs "$@"
    ;;
  *)
    echo "Unknown command: $COMMAND" >&2
    usage >&2
    exit 1
    ;;
esac
