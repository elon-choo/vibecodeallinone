#!/bin/zsh

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
RUNTIME_DIR="$REPO_ROOT/.agent-orchestrator/runtime"
CAFFEINATE_PID_FILE="$RUNTIME_DIR/caffeinate.pid"

"$SCRIPT_DIR/stop_watchdog_loop.sh" >/dev/null 2>&1 || true

if [[ -f "$CAFFEINATE_PID_FILE" ]]; then
  PID="$(cat "$CAFFEINATE_PID_FILE" 2>/dev/null || true)"
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
  fi
  rm -f "$CAFFEINATE_PID_FILE"
fi

print -r -- "stopped"
