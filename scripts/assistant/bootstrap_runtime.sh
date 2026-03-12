#!/bin/bash
# Bootstrap a self-host workspace for the assistant reference stack.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

TARGET_DIR="${ROOT_DIR}/.assistant-runtime"
API_PORT="8000"
WEB_PORT="4173"
PROVIDER_MODE="mock"
FORCE="0"

usage() {
  cat <<'EOF'
Assistant Runtime Bootstrap

Usage:
  bash scripts/assistant/bootstrap_runtime.sh [--target DIR] [--api-port PORT] [--web-port PORT] [--provider-mode mock|oidc] [--force]

What it does:
  - creates a local state directory for the assistant reference stack
  - writes assistant-api env defaults for this repo
  - generates launchers for assistant-api, assistant-web, worker, Telegram polling, and stack control

What it does not do:
  - provision managed hosting
  - provision a Telegram bot token for you
  - provision cloud deployment or hosted quickstart infrastructure
  - generate the managed quickstart operator artifact path (use scripts/assistant/bootstrap_managed_quickstart.sh for that)

Examples:
  bash scripts/assistant/bootstrap_runtime.sh --target "$HOME/.claude-power-pack-assistant"
  bash scripts/assistant/bootstrap_runtime.sh --target ./tmp/runtime --api-port 8010 --web-port 4174 --force
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET_DIR="${2:?missing value for --target}"
      shift 2
      ;;
    --api-port)
      API_PORT="${2:?missing value for --api-port}"
      shift 2
      ;;
    --web-port)
      WEB_PORT="${2:?missing value for --web-port}"
      shift 2
      ;;
    --provider-mode)
      PROVIDER_MODE="${2:?missing value for --provider-mode}"
      shift 2
      ;;
    --force)
      FORCE="1"
      shift
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

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required for the assistant runtime bootstrap." >&2
  exit 1
fi

if [[ "$PROVIDER_MODE" != "mock" && "$PROVIDER_MODE" != "oidc" ]]; then
  echo "provider mode must be 'mock' or 'oidc'." >&2
  exit 1
fi

case "$API_PORT" in
  ''|*[!0-9]*)
    echo "api port must be numeric." >&2
    exit 1
    ;;
esac

case "$WEB_PORT" in
  ''|*[!0-9]*)
    echo "web port must be numeric." >&2
    exit 1
    ;;
esac

TARGET_DIR="$(mkdir -p "$(dirname "$TARGET_DIR")" && cd "$(dirname "$TARGET_DIR")" && pwd)/$(basename "$TARGET_DIR")"

if [[ -d "$TARGET_DIR" && -n "$(ls -A "$TARGET_DIR" 2>/dev/null)" && "$FORCE" != "1" ]]; then
  echo "Target directory already exists and is not empty: $TARGET_DIR" >&2
  echo "Re-run with --force to overwrite bootstrap files." >&2
  exit 1
fi

mkdir -p "$TARGET_DIR/data" "$TARGET_DIR/artifacts" "$TARGET_DIR/logs" "$TARGET_DIR/run"

ENV_FILE="$TARGET_DIR/assistant-runtime.env"
API_RUNNER="$TARGET_DIR/run-assistant-api.sh"
WEB_RUNNER="$TARGET_DIR/run-assistant-web.sh"
WORKER_RUNNER="$TARGET_DIR/run-assistant-worker.sh"
TELEGRAM_RUNNER="$TARGET_DIR/run-assistant-telegram.sh"
RUNTIME_RUNNER="$TARGET_DIR/run-assistant-runtime.sh"
README_FILE="$TARGET_DIR/README.md"

cat > "$ENV_FILE" <<EOF
export ASSISTANT_RUNTIME_REPO_ROOT="$ROOT_DIR"
export ASSISTANT_RUNTIME_STATE_DIR="$TARGET_DIR"
export ASSISTANT_RUNTIME_API_PORT="$API_PORT"
export ASSISTANT_RUNTIME_WEB_PORT="$WEB_PORT"
export ASSISTANT_RUNTIME_WEB_ROOT="$ROOT_DIR/apps/assistant-web"
export ASSISTANT_RUNTIME_LOG_LEVEL="INFO"
export ASSISTANT_RUNTIME_OPERATOR_MODE="self-host"
export ASSISTANT_RUNTIME_TELEGRAM_MODE="auto"
export PYTHONUNBUFFERED="1"

export ASSISTANT_API_REPO_ROOT="$ROOT_DIR"
export ASSISTANT_API_SERVICE_ROOT="$ROOT_DIR/services/assistant-api"
export ASSISTANT_API_ARTIFACTS_DIR="$TARGET_DIR/artifacts"
export ASSISTANT_API_DB_PATH="$TARGET_DIR/data/assistant_api.sqlite3"
export ASSISTANT_API_MIGRATION_PATH="$ROOT_DIR/services/assistant-api/migrations/0001_bootstrap.sql"
export ASSISTANT_API_PUBLIC_BASE_URL="http://127.0.0.1:$API_PORT"
export ASSISTANT_API_WEB_ALLOWED_ORIGINS="http://127.0.0.1:$WEB_PORT"
export ASSISTANT_API_PROVIDER_MODE="$PROVIDER_MODE"
export ASSISTANT_API_RELEASE_CHANNEL="self-host-bootstrap"
export ASSISTANT_API_SECURE_COOKIES="false"
export ASSISTANT_API_TELEGRAM_BOT_TOKEN=""
export ASSISTANT_API_TELEGRAM_BOT_USERNAME=""
export ASSISTANT_API_TELEGRAM_BOT_LINK_BASE_URL=""
export ASSISTANT_API_TELEGRAM_API_BASE_URL="https://api.telegram.org"
export ASSISTANT_API_TELEGRAM_POLL_TIMEOUT_SECONDS="5"
EOF

cat > "$API_RUNNER" <<'EOF'
#!/bin/bash
set -euo pipefail

RUNTIME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$RUNTIME_DIR/assistant-runtime.env"

export PYTHONPATH="$ASSISTANT_API_SERVICE_ROOT"
exec python3 -m uvicorn assistant_api.main:app --host 127.0.0.1 --port "$ASSISTANT_RUNTIME_API_PORT"
EOF

cat > "$WEB_RUNNER" <<'EOF'
#!/bin/bash
set -euo pipefail

RUNTIME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$RUNTIME_DIR/assistant-runtime.env"

exec python3 -m http.server "$ASSISTANT_RUNTIME_WEB_PORT" --bind 127.0.0.1 --directory "$ASSISTANT_RUNTIME_WEB_ROOT"
EOF

cat > "$WORKER_RUNNER" <<'EOF'
#!/bin/bash
set -euo pipefail

RUNTIME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$RUNTIME_DIR/assistant-runtime.env"

export PYTHONPATH="$ASSISTANT_API_SERVICE_ROOT"
exec python3 "$ASSISTANT_RUNTIME_REPO_ROOT/scripts/assistant/run_job_worker.py" --log-level "$ASSISTANT_RUNTIME_LOG_LEVEL"
EOF

cat > "$TELEGRAM_RUNNER" <<'EOF'
#!/bin/bash
set -euo pipefail

RUNTIME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$RUNTIME_DIR/assistant-runtime.env"

export PYTHONPATH="$ASSISTANT_API_SERVICE_ROOT"
exec python3 "$ASSISTANT_RUNTIME_REPO_ROOT/scripts/assistant/run_telegram_transport.py" --log-level "$ASSISTANT_RUNTIME_LOG_LEVEL" --idle-sleep-seconds 1
EOF

cat > "$RUNTIME_RUNNER" <<'EOF'
#!/bin/bash
set -euo pipefail

RUNTIME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$RUNTIME_DIR/assistant-runtime.env"
if [[ $# -eq 0 ]]; then
  set -- start
fi

exec "$ASSISTANT_RUNTIME_REPO_ROOT/scripts/assistant/reference_stack.sh" --runtime-dir "$RUNTIME_DIR" "$@"
EOF

cat > "$README_FILE" <<EOF
# Assistant Runtime Bootstrap

This workspace was generated from:

- repo: $ROOT_DIR
- state dir: $TARGET_DIR

Generated files:

- \`assistant-runtime.env\`
- \`run-assistant-api.sh\`
- \`run-assistant-web.sh\`
- \`run-assistant-worker.sh\`
- \`run-assistant-telegram.sh\`
- \`run-assistant-runtime.sh\`

Default local URLs:

- assistant-api: http://127.0.0.1:$API_PORT
- assistant-web: http://127.0.0.1:$WEB_PORT

Current bootstrap scope:

- self-host reference stack controller
- operator mode locked to \`self-host\`
- mock auth by default
- local SQLite/artifacts/logs/run directories
- Telegram runtime in the same control path, disabled until a bot token is configured

Next steps:

1. Review \`assistant-runtime.env\`.
2. If your Python environment is missing runtime packages, install \`fastapi\`, \`uvicorn\`, and \`pydantic\`.
3. Start the local stack with \`./run-assistant-runtime.sh start\`.
4. Inspect status with \`./run-assistant-runtime.sh status\`.
5. Stop the stack with \`./run-assistant-runtime.sh stop\`.
6. For real auth, switch \`ASSISTANT_API_PROVIDER_MODE\` to \`oidc\` and fill in the provider env vars.
7. To enable Telegram polling in the same operator path, set:
   - \`ASSISTANT_RUNTIME_TELEGRAM_MODE=enabled\`
   - \`ASSISTANT_API_TELEGRAM_BOT_TOKEN=...\`
   - optional \`ASSISTANT_API_TELEGRAM_BOT_USERNAME=...\`
8. For the managed quickstart contract, keep this same runtime path but use \`scripts/assistant/bootstrap_managed_quickstart.sh\` instead of changing this bootstrap away from \`ASSISTANT_RUNTIME_OPERATOR_MODE=self-host\`.

Not included yet:

- webhook-based Telegram ingress
- broader Telegram admin/moderation surfaces
- cloud deployment automation
EOF

chmod +x "$API_RUNNER" "$WEB_RUNNER" "$WORKER_RUNNER" "$TELEGRAM_RUNNER" "$RUNTIME_RUNNER"

echo "Assistant runtime bootstrap created:"
echo "  target: $TARGET_DIR"
echo "  env:    $ENV_FILE"
echo "  run:    $RUNTIME_RUNNER"
echo ""
echo "Next steps:"
echo "  1. Review $ENV_FILE"
echo "  2. Install fastapi, uvicorn, and pydantic if your Python env does not already have them"
echo "  3. Start the stack: $RUNTIME_RUNNER start"
echo "  4. Check status: $RUNTIME_RUNNER status"
echo "  5. Stop the stack: $RUNTIME_RUNNER stop"
