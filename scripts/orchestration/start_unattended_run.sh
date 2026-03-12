#!/bin/zsh

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
RUNTIME_DIR="$REPO_ROOT/.agent-orchestrator/runtime"
CAFFEINATE_PID_FILE="$RUNTIME_DIR/caffeinate.pid"
CAFFEINATE_LOG="$RUNTIME_DIR/caffeinate.log"
SECONDS_TOTAL="${AGENT_ORCHESTRATOR_AWAKE_SECONDS:-36000}"

export AGENT_ORCHESTRATOR_MAX_SESSIONS="${AGENT_ORCHESTRATOR_MAX_SESSIONS:-20}"
export AGENT_ORCHESTRATOR_WATCH_INTERVAL_SECONDS="${AGENT_ORCHESTRATOR_WATCH_INTERVAL_SECONDS:-120}"
export AGENT_ORCHESTRATOR_STALL_SECONDS="${AGENT_ORCHESTRATOR_STALL_SECONDS:-240}"

mkdir -p "$RUNTIME_DIR"

WATCHDOG_PID="$("$SCRIPT_DIR/start_watchdog_loop.sh")"

if [[ -f "$CAFFEINATE_PID_FILE" ]]; then
  EXISTING_PID="$(cat "$CAFFEINATE_PID_FILE" 2>/dev/null || true)"
  if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
    print -r -- "watchdog=$WATCHDOG_PID caffeinate=$EXISTING_PID"
    exit 0
  fi
  rm -f "$CAFFEINATE_PID_FILE"
fi

CAFFEINATE_PID="$(
  python3 - "$SECONDS_TOTAL" "$CAFFEINATE_LOG" <<'PY'
import subprocess
import sys
from pathlib import Path

seconds_total = sys.argv[1]
log_path = Path(sys.argv[2])
log_path.parent.mkdir(parents=True, exist_ok=True)

with log_path.open("ab") as log_file:
    process = subprocess.Popen(
        ["caffeinate", "-dimsu", "-t", seconds_total],
        stdin=subprocess.DEVNULL,
        stdout=log_file,
        stderr=log_file,
        start_new_session=True,
    )
print(process.pid)
PY
)"

print -r -- "$CAFFEINATE_PID" > "$CAFFEINATE_PID_FILE"
print -r -- "watchdog=$WATCHDOG_PID caffeinate=$CAFFEINATE_PID"
