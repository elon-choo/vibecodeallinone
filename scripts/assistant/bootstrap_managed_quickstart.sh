#!/bin/bash
# Bootstrap a managed-quickstart operator workspace on the shared assistant runtime path.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

TARGET_DIR="${ROOT_DIR}/.assistant-managed-runtime"
API_PORT="8000"
WEB_PORT="4173"
API_PUBLIC_BASE_URL="https://api.example.com"
WEB_ORIGIN="https://app.example.com"
TELEGRAM_MODE="auto"
FORCE="0"

usage() {
  cat <<'EOF'
Assistant Managed Quickstart Bootstrap

Usage:
  bash scripts/assistant/bootstrap_managed_quickstart.sh [--target DIR] [--api-port PORT] [--web-port PORT] [--api-public-base-url URL] [--web-origin URL] [--telegram-mode auto|enabled|disabled] [--force]

What it does:
  - creates an operator workspace on top of the same assistant reference stack controller
  - writes a managed-quickstart env file with placeholder values that must be replaced before live rollout
  - keeps the generated API/web/worker/Telegram launchers and stack controller in one place

What it does not do:
  - provision hosted infrastructure or reverse proxies
  - validate live OIDC credentials or Telegram reachability
  - create a second backend or a forked web app

Examples:
  bash scripts/assistant/bootstrap_managed_quickstart.sh --target "$HOME/.claude-power-pack-managed"
  bash scripts/assistant/bootstrap_managed_quickstart.sh --target ./tmp/managed --api-public-base-url https://api.example.com --web-origin https://app.example.com --force
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
    --api-public-base-url)
      API_PUBLIC_BASE_URL="${2:?missing value for --api-public-base-url}"
      shift 2
      ;;
    --web-origin)
      WEB_ORIGIN="${2:?missing value for --web-origin}"
      shift 2
      ;;
    --telegram-mode)
      TELEGRAM_MODE="${2:?missing value for --telegram-mode}"
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
  echo "python3 is required for the managed quickstart bootstrap." >&2
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

case "$TELEGRAM_MODE" in
  auto|enabled|disabled)
    ;;
  *)
    echo "telegram mode must be auto, enabled, or disabled." >&2
    exit 1
    ;;
esac

python3 - "$API_PUBLIC_BASE_URL" "$WEB_ORIGIN" <<'PY'
from __future__ import annotations

import sys
from urllib.parse import urlsplit


def assert_public_https(name: str, value: str) -> None:
    parts = urlsplit(value)
    hostname = (parts.hostname or "").lower()
    if parts.scheme != "https" or hostname in {"", "localhost", "127.0.0.1"}:
        raise SystemExit(f"{name} must be a public https URL.")


assert_public_https("api public base URL", sys.argv[1])
assert_public_https("web origin", sys.argv[2])
PY

BOOTSTRAP_ARGS=(
  --target "$TARGET_DIR"
  --api-port "$API_PORT"
  --web-port "$WEB_PORT"
  --provider-mode oidc
)
if [[ "$FORCE" == "1" ]]; then
  BOOTSTRAP_ARGS+=(--force)
fi

bash "$ROOT_DIR/scripts/assistant/bootstrap_runtime.sh" "${BOOTSTRAP_ARGS[@]}" >/dev/null

TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
ENV_FILE="$TARGET_DIR/assistant-runtime.env"
README_FILE="$TARGET_DIR/README.md"
MANAGED_TEMPLATE_COPY="$TARGET_DIR/assistant-runtime.managed.env.example"

cat > "$ENV_FILE" <<EOF
# Managed quickstart uses the same runtime/controller as self-host.
# Replace placeholder values before expecting deployment-readiness: managed-ready.

export ASSISTANT_RUNTIME_REPO_ROOT="$ROOT_DIR"
export ASSISTANT_RUNTIME_STATE_DIR="$TARGET_DIR"
export ASSISTANT_RUNTIME_API_PORT="$API_PORT"
export ASSISTANT_RUNTIME_WEB_PORT="$WEB_PORT"
export ASSISTANT_RUNTIME_WEB_ROOT="$ROOT_DIR/apps/assistant-web"
export ASSISTANT_RUNTIME_LOG_LEVEL="INFO"
export ASSISTANT_RUNTIME_OPERATOR_MODE="managed-quickstart"
export ASSISTANT_RUNTIME_TELEGRAM_MODE="$TELEGRAM_MODE"
export PYTHONUNBUFFERED="1"

export ASSISTANT_API_REPO_ROOT="$ROOT_DIR"
export ASSISTANT_API_SERVICE_ROOT="$ROOT_DIR/services/assistant-api"
export ASSISTANT_API_ARTIFACTS_DIR="$TARGET_DIR/artifacts"
export ASSISTANT_API_DB_PATH="$TARGET_DIR/data/assistant_api.sqlite3"
export ASSISTANT_API_MIGRATION_PATH="$ROOT_DIR/services/assistant-api/migrations/0001_bootstrap.sql"

export ASSISTANT_API_PUBLIC_BASE_URL="$API_PUBLIC_BASE_URL"
export ASSISTANT_API_WEB_ALLOWED_ORIGINS="$WEB_ORIGIN"
export ASSISTANT_API_PROVIDER_MODE="oidc"
export ASSISTANT_API_RELEASE_CHANNEL="managed-quickstart"
export ASSISTANT_API_SECURE_COOKIES="true"

export ASSISTANT_API_PROVIDER_CLIENT_ID="replace-me"
export ASSISTANT_API_PROVIDER_CLIENT_SECRET="replace-me-when-required"
export ASSISTANT_API_PROVIDER_AUTH_URL="https://auth.example.com/oauth/authorize"
export ASSISTANT_API_PROVIDER_TOKEN_URL="https://auth.example.com/oauth/token"
export ASSISTANT_API_PROVIDER_USERINFO_URL="https://auth.example.com/oauth/userinfo"
export ASSISTANT_API_PROVIDER_SCOPES="openid,profile,email,offline_access"

export ASSISTANT_API_TELEGRAM_BOT_TOKEN=""
export ASSISTANT_API_TELEGRAM_BOT_USERNAME=""
export ASSISTANT_API_TELEGRAM_BOT_LINK_BASE_URL=""
export ASSISTANT_API_TELEGRAM_API_BASE_URL="https://api.telegram.org"
export ASSISTANT_API_TELEGRAM_POLL_TIMEOUT_SECONDS="30"

export ASSISTANT_API_MEMORY_DELETE_RETENTION_SECONDS="604800"
export ASSISTANT_API_WORKER_POLL_INTERVAL_SECONDS="2"
export ASSISTANT_API_WORKER_JOB_LEASE_SECONDS="30"
export ASSISTANT_API_SESSION_TTL_SECONDS="2592000"
EOF

cp "$ROOT_DIR/ops/managed/assistant-runtime.managed.env.example" "$MANAGED_TEMPLATE_COPY"

cat > "$README_FILE" <<EOF
# Managed Quickstart Operator Bootstrap

This workspace was generated from:

- repo: $ROOT_DIR
- state dir: $TARGET_DIR

Generated files:

- \`assistant-runtime.env\`
- \`assistant-runtime.managed.env.example\`
- \`run-assistant-api.sh\`
- \`run-assistant-web.sh\`
- \`run-assistant-worker.sh\`
- \`run-assistant-telegram.sh\`
- \`run-assistant-runtime.sh\`

Managed quickstart notes:

- this workspace stays on the same runtime path as self-host
- \`run-assistant-runtime.sh status\` reports managed contract blockers until placeholders are replaced
- \`run-assistant-runtime.sh start\` still controls the local API/web/worker/Telegram processes for operator verification
- the stack controller verifies local process health on \`127.0.0.1\`, while \`ASSISTANT_API_PUBLIC_BASE_URL\` remains the external origin contract used by the product

Next steps:

1. Review \`assistant-runtime.env\` and replace placeholder OIDC/public-origin values.
2. Keep Telegram in \`auto\` until a bot token exists, or set \`ASSISTANT_RUNTIME_TELEGRAM_MODE=disabled\` if Telegram is out of scope.
3. Run \`./run-assistant-runtime.sh status\` until \`deployment-readiness: managed-ready\`.
4. Start the local operator stack with \`./run-assistant-runtime.sh start\`.
5. Optionally export \`ASSISTANT_OPERATOR_VALIDATION_API_BASE_URL="http://127.0.0.1:$API_PORT"\` and run live validation:
   - \`python3 "$ROOT_DIR/scripts/assistant/run_operator_smoke.py" --live-provider-wait-seconds 180 --live-telegram-wait-seconds 180\`
   - \`python3 "$ROOT_DIR/scripts/assistant/run_telegram_live_validation.py" --wait-seconds 180\`
6. Inspect logs with \`./run-assistant-runtime.sh logs\`.
7. Stop the stack with \`./run-assistant-runtime.sh stop\`.

Not included yet:

- hosted vendor provisioning
- web onboarding redesign
EOF

echo "Managed quickstart operator bootstrap created:"
echo "  target: $TARGET_DIR"
echo "  env:    $ENV_FILE"
echo "  run:    $TARGET_DIR/run-assistant-runtime.sh"
echo ""
echo "Next steps:"
echo "  1. Replace placeholder values in $ENV_FILE"
echo "  2. Check readiness: $TARGET_DIR/run-assistant-runtime.sh status"
echo "  3. Start the stack once the contract is ready: $TARGET_DIR/run-assistant-runtime.sh start"
echo "  4. Stop the stack when finished: $TARGET_DIR/run-assistant-runtime.sh stop"
