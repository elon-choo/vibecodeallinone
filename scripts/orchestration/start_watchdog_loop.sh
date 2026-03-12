#!/bin/zsh

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
RUNTIME_DIR="$REPO_ROOT/.agent-orchestrator/runtime"
PID_FILE="$RUNTIME_DIR/watchdog-loop.pid"
STARTER_PID_FILE="$RUNTIME_DIR/watchdog-starter.pid"
LOG_FILE="$RUNTIME_DIR/watchdog-launch.log"

mkdir -p "$RUNTIME_DIR"

if [[ -f "$PID_FILE" ]]; then
  EXISTING_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
    print -r -- "$EXISTING_PID"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

NEW_PID="$(
  SCRIPT_DIR="$SCRIPT_DIR" LOG_FILE="$LOG_FILE" python3 - <<'PY'
import os
import subprocess
from pathlib import Path

script_dir = Path(os.environ["SCRIPT_DIR"])
log_path = Path(os.environ["LOG_FILE"])
log_path.parent.mkdir(parents=True, exist_ok=True)

with log_path.open("ab") as log_file:
    process = subprocess.Popen(
        [str(script_dir / "watchdog_loop.sh")],
        stdin=subprocess.DEVNULL,
        stdout=log_file,
        stderr=log_file,
        start_new_session=True,
    )

print(process.pid)
PY
)"
print -r -- "$NEW_PID" > "$STARTER_PID_FILE"
print -r -- "$NEW_PID"
