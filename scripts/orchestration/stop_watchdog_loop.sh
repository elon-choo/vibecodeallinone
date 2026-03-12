#!/bin/zsh

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
RUNTIME_DIR="$REPO_ROOT/.agent-orchestrator/runtime"
PID_FILE="$RUNTIME_DIR/watchdog-loop.pid"
STARTER_PID_FILE="$RUNTIME_DIR/watchdog-starter.pid"

STOPPED=0

for FILE in "$PID_FILE" "$STARTER_PID_FILE"; do
  if [[ -f "$FILE" ]]; then
    PID="$(cat "$FILE" 2>/dev/null || true)"
    if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
      kill "$PID" 2>/dev/null || true
      STOPPED=1
    fi
    rm -f "$FILE"
  fi
done

if [[ "$STOPPED" -eq 1 ]]; then
  print -r -- "stopped"
else
  print -r -- "not-running"
fi
