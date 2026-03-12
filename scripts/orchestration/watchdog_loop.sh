#!/bin/zsh

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
RUNTIME_DIR="$REPO_ROOT/.agent-orchestrator/runtime"
LOG_FILE="$RUNTIME_DIR/watchdog-loop.log"
PID_FILE="$RUNTIME_DIR/watchdog-loop.pid"
INTERVAL="${AGENT_ORCHESTRATOR_WATCH_INTERVAL_SECONDS:-120}"

mkdir -p "$RUNTIME_DIR"

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
  print -r -- "[$(timestamp)] $*" >> "$LOG_FILE"
}

print -r -- "$$" > "$PID_FILE"
trap 'rm -f "$PID_FILE"' EXIT

log "watchdog loop started with interval=${INTERVAL}s"

while true; do
  if "$SCRIPT_DIR/ensure_agent_orchestrator.sh" >> "$LOG_FILE" 2>&1; then
    log "ensure pass complete"
  else
    log "ensure pass reported failure"
  fi
  sleep "$INTERVAL"
done
