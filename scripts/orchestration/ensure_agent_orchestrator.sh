#!/bin/zsh

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
RUNTIME_DIR="$REPO_ROOT/.agent-orchestrator/runtime"
PROMPT_FILE="$REPO_ROOT/NEXT_SESSION_PROMPT.md"
CONFIG_FILE="$REPO_ROOT/.agent-orchestrator/config.json"
STATE_FILE="$RUNTIME_DIR/state.json"
LOG_FILE="$RUNTIME_DIR/watchdog.log"
LOCK_DIR="$RUNTIME_DIR/watchdog.lock"
MAX_SESSIONS="${AGENT_ORCHESTRATOR_MAX_SESSIONS:-20}"
STALL_SECONDS="${AGENT_ORCHESTRATOR_STALL_SECONDS:-240}"
STOP_MARKERS_REGEX='^(SESSION_CHAIN_COMPLETE|NO_FURTHER_SESSION|ORCHESTRATOR_STOP|SESSION_CHAIN_PAUSE)$'

mkdir -p "$RUNTIME_DIR"

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
  print -r -- "[$(timestamp)] $*" >> "$LOG_FILE"
}

if [[ ! -f "$CONFIG_FILE" || ! -f "$PROMPT_FILE" ]]; then
  log "missing config or prompt file; skipping"
  exit 1
fi

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  log "watchdog lock is already held; skipping"
  exit 0
fi
trap 'rmdir "$LOCK_DIR" >/dev/null 2>&1 || true' EXIT

if grep -Eq "$STOP_MARKERS_REGEX" "$PROMPT_FILE"; then
  log "stop marker found in NEXT_SESSION_PROMPT.md; no restart needed"
  exit 0
fi

STATUS_JSON="$(agent-orchestrator status 2>/dev/null || true)"
ACTION="$(STATUS_JSON="$STATUS_JSON" PROMPT_FILE="$PROMPT_FILE" STATE_FILE="$STATE_FILE" RUNTIME_DIR="$RUNTIME_DIR" STALL_SECONDS="$STALL_SECONDS" python3 - <<'PY'
import json
import os
import time
from pathlib import Path

status_raw = os.environ.get("STATUS_JSON", "").strip()
prompt_path = Path(os.environ["PROMPT_FILE"])
state_path = Path(os.environ["STATE_FILE"])
runtime_dir = Path(os.environ["RUNTIME_DIR"])
stall_seconds = int(os.environ["STALL_SECONDS"])

prompt_mtime = prompt_path.stat().st_mtime if prompt_path.exists() else 0.0
state_mtime = state_path.stat().st_mtime if state_path.exists() else 0.0


def latest_runner_mtime() -> float:
    logs_dir = runtime_dir / "logs"
    if not logs_dir.exists():
        return 0.0

    dirs = sorted((path for path in logs_dir.iterdir() if path.is_dir()), key=lambda path: path.name)
    if not dirs:
        return 0.0

    latest_dir = dirs[-1]
    candidates = [
        latest_dir / "runner.stderr.log",
        latest_dir / "runner.stdout.log",
        latest_dir / "last-message.txt",
        latest_dir / "prompt.md",
    ]
    mtimes = [path.stat().st_mtime for path in candidates if path.exists()]
    return max(mtimes) if mtimes else 0.0

if not status_raw:
    print("run:no-status")
    raise SystemExit

try:
    status = json.loads(status_raw)
except json.JSONDecodeError:
    print("run:bad-status")
    raise SystemExit

if status.get("status") == "running" and status.get("alive") is True:
    latest_mtime = latest_runner_mtime()
    if latest_mtime and (time.time() - latest_mtime) > stall_seconds:
        print(f"restart:stalled-{int(time.time() - latest_mtime)}s")
        raise SystemExit
    print("skip:already-running")
    raise SystemExit

stop_reason = str(status.get("stopReason") or "").lower()
if "unchanged" in stop_reason and prompt_mtime <= state_mtime:
    print("skip:prompt-unchanged")
    raise SystemExit

print(f"run:{stop_reason or 'stopped'}")
PY
)"

case "$ACTION" in
  skip:*)
    log "${ACTION#skip:}"
    exit 0
    ;;
  restart:*)
    log "stall detected (${ACTION#restart:}); stopping orchestrator before restart"
    agent-orchestrator stop >> "$LOG_FILE" 2>&1 || true
    sleep 2
    log "restarting orchestrator after stall"
    if agent-orchestrator start --max-sessions "$MAX_SESSIONS" >> "$LOG_FILE" 2>&1; then
      log "restart command accepted"
      exit 0
    fi
    log "restart command failed"
    exit 1
    ;;
  run:*)
    log "starting orchestrator because ${ACTION#run:}"
    if agent-orchestrator start --max-sessions "$MAX_SESSIONS" >> "$LOG_FILE" 2>&1; then
      log "start command accepted"
      exit 0
    fi
    log "start command failed"
    exit 1
    ;;
  *)
    log "unexpected watchdog action: $ACTION"
    exit 1
    ;;
esac
