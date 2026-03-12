#!/bin/bash
# Smoke test for developer install + assistant reference stack bootstrap
# Usage: bash tests/test_install_smoke.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

TEST_HOME="$(mktemp -d)"
BOOTSTRAP_ROOT="$(mktemp -d)"
BOOTSTRAP_TARGET=""
STACK_STARTED="0"
MANAGED_BOOTSTRAP_TARGET=""

cleanup() {
  if [ "$STACK_STARTED" = "1" ] && [ -n "$BOOTSTRAP_TARGET" ] && [ -x "$BOOTSTRAP_TARGET/run-assistant-runtime.sh" ]; then
    "$BOOTSTRAP_TARGET/run-assistant-runtime.sh" stop >/dev/null 2>&1 || true
  fi
  rm -rf "$TEST_HOME" "$BOOTSTRAP_ROOT"
}

trap cleanup EXIT

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
            last_error = f"status {response.status}"
    except urllib.error.HTTPError as exc:
        if 200 <= exc.code < 400:
            raise SystemExit(0)
        last_error = f"status {exc.code}"
    except Exception as exc:
        last_error = str(exc)
    time.sleep(0.2)

print(last_error, file=sys.stderr)
raise SystemExit(1)
PY
}

assert_pid_running() {
  local pid_file="$1"
  python3 - "$pid_file" <<'PY'
from __future__ import annotations

import os
import pathlib
import sys

pid_path = pathlib.Path(sys.argv[1])
if not pid_path.exists():
    raise SystemExit(1)
raw_pid = pid_path.read_text(encoding="utf-8").strip()
if not raw_pid:
    raise SystemExit(1)
os.kill(int(raw_pid), 0)
PY
}

find_free_port() {
  python3 - <<'PY'
from __future__ import annotations

import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

# Use temp home to avoid clobbering real ~/.claude/skills
export HOME="$TEST_HOME"
echo "Test HOME: $HOME"

# Run Tier 1 install
bash "$ROOT_DIR/scripts/install.sh" 1

# Verify skills directory exists
if [ ! -d "$HOME/.claude/skills" ]; then
  echo "FAIL: ~/.claude/skills not created"
  rm -rf "$HOME"
  exit 1
fi

# Count installed skills
INSTALLED=$(ls -d "$HOME/.claude/skills"/*/ 2>/dev/null | wc -l | tr -d ' ')
echo "Installed skills: $INSTALLED"

if [ "$INSTALLED" -lt 12 ]; then
  echo "FAIL: Expected 12 skills, got $INSTALLED"
  ls "$HOME/.claude/skills/"
  rm -rf "$HOME"
  exit 1
fi

# Verify each skill has SKILL.md
MISSING=0
for skill_dir in "$HOME/.claude/skills"/*/; do
  if [ ! -f "$skill_dir/SKILL.md" ]; then
    echo "FAIL: Missing SKILL.md in $(basename "$skill_dir")"
    MISSING=$((MISSING + 1))
  fi
done

if [ "$MISSING" -gt 0 ]; then
  rm -rf "$HOME"
  exit 1
fi

echo "PASS: All 12 skills installed with SKILL.md"

# Verify assistant runtime bootstrap scaffold
BOOTSTRAP_TARGET="$BOOTSTRAP_ROOT/runtime"
API_PORT="$(find_free_port)"
WEB_PORT="$(find_free_port)"
bash "$ROOT_DIR/scripts/assistant/bootstrap_runtime.sh" --target "$BOOTSTRAP_TARGET" --api-port "$API_PORT" --web-port "$WEB_PORT"

for required_path in \
  "$BOOTSTRAP_TARGET/assistant-runtime.env" \
  "$BOOTSTRAP_TARGET/run-assistant-api.sh" \
  "$BOOTSTRAP_TARGET/run-assistant-web.sh" \
  "$BOOTSTRAP_TARGET/run-assistant-worker.sh" \
  "$BOOTSTRAP_TARGET/run-assistant-telegram.sh" \
  "$BOOTSTRAP_TARGET/run-assistant-runtime.sh" \
  "$BOOTSTRAP_TARGET/README.md" \
  "$BOOTSTRAP_TARGET/data" \
  "$BOOTSTRAP_TARGET/artifacts" \
  "$BOOTSTRAP_TARGET/logs" \
  "$BOOTSTRAP_TARGET/run"
do
  if [ ! -e "$required_path" ]; then
    echo "FAIL: Missing bootstrap artifact $required_path"
    exit 1
  fi
done

for executable_path in \
  "$BOOTSTRAP_TARGET/run-assistant-api.sh" \
  "$BOOTSTRAP_TARGET/run-assistant-web.sh" \
  "$BOOTSTRAP_TARGET/run-assistant-worker.sh" \
  "$BOOTSTRAP_TARGET/run-assistant-telegram.sh" \
  "$BOOTSTRAP_TARGET/run-assistant-runtime.sh"
do
  if [ ! -x "$executable_path" ]; then
    echo "FAIL: Expected executable bootstrap launcher $executable_path"
    exit 1
  fi
done

if ! grep -Fq 'ASSISTANT_API_PROVIDER_MODE="mock"' "$BOOTSTRAP_TARGET/assistant-runtime.env"; then
  echo "FAIL: bootstrap env did not default to mock provider mode"
  exit 1
fi

if ! grep -Fq "$ROOT_DIR/services/assistant-api" "$BOOTSTRAP_TARGET/assistant-runtime.env"; then
  echo "FAIL: bootstrap env does not point at services/assistant-api"
  exit 1
fi

if ! grep -Fq "$ROOT_DIR/apps/assistant-web" "$BOOTSTRAP_TARGET/assistant-runtime.env"; then
  echo "FAIL: bootstrap env does not point at apps/assistant-web"
  exit 1
fi

echo "PASS: Assistant runtime bootstrap scaffold created"

if ! grep -Fq 'ASSISTANT_RUNTIME_TELEGRAM_MODE="auto"' "$BOOTSTRAP_TARGET/assistant-runtime.env"; then
  echo "FAIL: bootstrap env did not default Telegram mode to auto"
  exit 1
fi

if ! grep -Fq 'ASSISTANT_RUNTIME_OPERATOR_MODE="self-host"' "$BOOTSTRAP_TARGET/assistant-runtime.env"; then
  echo "FAIL: bootstrap env did not lock operator mode to self-host"
  exit 1
fi

"$BOOTSTRAP_TARGET/run-assistant-runtime.sh" start
STACK_STARTED="1"

wait_for_http "http://127.0.0.1:$API_PORT/openapi.json" 20
wait_for_http "http://127.0.0.1:$WEB_PORT/" 20

for pid_file in \
  "$BOOTSTRAP_TARGET/run/api.pid" \
  "$BOOTSTRAP_TARGET/run/web.pid" \
  "$BOOTSTRAP_TARGET/run/worker.pid"
do
  if ! assert_pid_running "$pid_file"; then
    echo "FAIL: expected running process for $pid_file"
    exit 1
  fi
done

STATUS_OUTPUT="$("$BOOTSTRAP_TARGET/run-assistant-runtime.sh" status)"
echo "$STATUS_OUTPUT"
if ! grep -Fq 'api: running' <<<"$STATUS_OUTPUT"; then
  echo "FAIL: runtime status did not report api as running"
  exit 1
fi
if ! grep -Fq 'web: running' <<<"$STATUS_OUTPUT"; then
  echo "FAIL: runtime status did not report web as running"
  exit 1
fi
if ! grep -Fq 'worker: running' <<<"$STATUS_OUTPUT"; then
  echo "FAIL: runtime status did not report worker as running"
  exit 1
fi
if ! grep -Fq 'telegram: disabled' <<<"$STATUS_OUTPUT"; then
  echo "FAIL: runtime status did not explain Telegram disabled state"
  exit 1
fi
if ! grep -Fq 'operator-mode: self-host' <<<"$STATUS_OUTPUT"; then
  echo "FAIL: runtime status did not report self-host operator mode"
  exit 1
fi
if ! grep -Fq 'deployment-readiness: self-host-ready' <<<"$STATUS_OUTPUT"; then
  echo "FAIL: runtime status did not report self-host deployment readiness"
  exit 1
fi

"$BOOTSTRAP_TARGET/run-assistant-runtime.sh" stop
STACK_STARTED="0"

POST_STOP_STATUS="$("$BOOTSTRAP_TARGET/run-assistant-runtime.sh" status)"
if ! grep -Fq 'api: stopped' <<<"$POST_STOP_STATUS"; then
  echo "FAIL: runtime status did not report api as stopped after stop"
  exit 1
fi
if ! grep -Fq 'web: stopped' <<<"$POST_STOP_STATUS"; then
  echo "FAIL: runtime status did not report web as stopped after stop"
  exit 1
fi
if ! grep -Fq 'worker: stopped' <<<"$POST_STOP_STATUS"; then
  echo "FAIL: runtime status did not report worker as stopped after stop"
  exit 1
fi
if ! grep -Fq 'operator-mode: self-host' <<<"$POST_STOP_STATUS"; then
  echo "FAIL: stopped runtime status did not preserve self-host operator mode"
  exit 1
fi

echo "PASS: Assistant reference stack start/stop works"

# Verify managed quickstart operator bootstrap scaffold
MANAGED_BOOTSTRAP_TARGET="$BOOTSTRAP_ROOT/managed-runtime"
MANAGED_API_PORT="$(find_free_port)"
MANAGED_WEB_PORT="$(find_free_port)"
bash "$ROOT_DIR/scripts/assistant/bootstrap_managed_quickstart.sh" \
  --target "$MANAGED_BOOTSTRAP_TARGET" \
  --api-port "$MANAGED_API_PORT" \
  --web-port "$MANAGED_WEB_PORT" \
  --api-public-base-url "https://api.example.com" \
  --web-origin "https://app.example.com"

for required_path in \
  "$MANAGED_BOOTSTRAP_TARGET/assistant-runtime.env" \
  "$MANAGED_BOOTSTRAP_TARGET/assistant-runtime.managed.env.example" \
  "$MANAGED_BOOTSTRAP_TARGET/run-assistant-api.sh" \
  "$MANAGED_BOOTSTRAP_TARGET/run-assistant-web.sh" \
  "$MANAGED_BOOTSTRAP_TARGET/run-assistant-worker.sh" \
  "$MANAGED_BOOTSTRAP_TARGET/run-assistant-telegram.sh" \
  "$MANAGED_BOOTSTRAP_TARGET/run-assistant-runtime.sh" \
  "$MANAGED_BOOTSTRAP_TARGET/README.md" \
  "$MANAGED_BOOTSTRAP_TARGET/data" \
  "$MANAGED_BOOTSTRAP_TARGET/artifacts" \
  "$MANAGED_BOOTSTRAP_TARGET/logs" \
  "$MANAGED_BOOTSTRAP_TARGET/run"
do
  if [ ! -e "$required_path" ]; then
    echo "FAIL: Missing managed quickstart bootstrap artifact $required_path"
    exit 1
  fi
done

if ! grep -Fq 'ASSISTANT_RUNTIME_OPERATOR_MODE="managed-quickstart"' "$MANAGED_BOOTSTRAP_TARGET/assistant-runtime.env"; then
  echo "FAIL: managed quickstart env did not select managed-quickstart operator mode"
  exit 1
fi

if ! grep -Fq 'ASSISTANT_API_PROVIDER_MODE="oidc"' "$MANAGED_BOOTSTRAP_TARGET/assistant-runtime.env"; then
  echo "FAIL: managed quickstart env did not lock provider mode to oidc"
  exit 1
fi

if ! grep -Fq 'ASSISTANT_API_SECURE_COOKIES="true"' "$MANAGED_BOOTSTRAP_TARGET/assistant-runtime.env"; then
  echo "FAIL: managed quickstart env did not enable secure cookies"
  exit 1
fi

if ! grep -Fq 'ASSISTANT_API_RELEASE_CHANNEL="managed-quickstart"' "$MANAGED_BOOTSTRAP_TARGET/assistant-runtime.env"; then
  echo "FAIL: managed quickstart env did not set the release channel"
  exit 1
fi

if ! grep -Fq 'ASSISTANT_API_PUBLIC_BASE_URL="https://api.example.com"' "$MANAGED_BOOTSTRAP_TARGET/assistant-runtime.env"; then
  echo "FAIL: managed quickstart env did not capture the public API base URL"
  exit 1
fi

if ! grep -Fq 'ASSISTANT_API_WEB_ALLOWED_ORIGINS="https://app.example.com"' "$MANAGED_BOOTSTRAP_TARGET/assistant-runtime.env"; then
  echo "FAIL: managed quickstart env did not capture the managed web origin"
  exit 1
fi

MANAGED_STATUS="$("$MANAGED_BOOTSTRAP_TARGET/run-assistant-runtime.sh" status)"
echo "$MANAGED_STATUS"
if ! grep -Fq 'operator-mode: managed-quickstart' <<<"$MANAGED_STATUS"; then
  echo "FAIL: managed quickstart status did not report operator mode"
  exit 1
fi
if ! grep -Fq 'deployment-readiness: managed-blocked' <<<"$MANAGED_STATUS"; then
  echo "FAIL: managed quickstart status did not stay blocked before placeholders were replaced"
  exit 1
fi
if ! grep -Fq 'deployment-blocker: ASSISTANT_API_PUBLIC_BASE_URL still contains a placeholder value and must be replaced for managed quickstart.' <<<"$MANAGED_STATUS"; then
  echo "FAIL: managed quickstart status did not explain the placeholder blocker"
  exit 1
fi
if ! grep -Fq 'telegram: disabled reason=auto-disabled until ASSISTANT_API_TELEGRAM_BOT_TOKEN is set' <<<"$MANAGED_STATUS"; then
  echo "FAIL: managed quickstart status did not preserve Telegram auto-disabled messaging"
  exit 1
fi

echo "PASS: Managed quickstart operator bootstrap scaffold created"

exit 0
