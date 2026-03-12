# Managed Quickstart Operator Runbook

## 1. Generate The Workspace

```bash
bash scripts/assistant/bootstrap_managed_quickstart.sh --target "$HOME/.claude-power-pack-managed"
```

Generated artifacts:

- `assistant-runtime.env`
- `assistant-runtime.managed.env.example`
- `run-assistant-api.sh`
- `run-assistant-web.sh`
- `run-assistant-worker.sh`
- `run-assistant-telegram.sh`
- `run-assistant-runtime.sh`
- local `data/`, `artifacts/`, `logs/`, and `run/` directories

## 2. Replace Placeholder Values

Edit `assistant-runtime.env` and replace placeholder values for:

- `ASSISTANT_API_PUBLIC_BASE_URL`
- `ASSISTANT_API_WEB_ALLOWED_ORIGINS`
- `ASSISTANT_API_PROVIDER_CLIENT_ID`
- `ASSISTANT_API_PROVIDER_AUTH_URL`
- `ASSISTANT_API_PROVIDER_TOKEN_URL`
- optional `ASSISTANT_API_PROVIDER_USERINFO_URL`
- Telegram fields when Telegram is enabled

Keep:

- `ASSISTANT_RUNTIME_OPERATOR_MODE=managed-quickstart`
- `ASSISTANT_API_PROVIDER_MODE=oidc`
- `ASSISTANT_API_SECURE_COOKIES=true`

## 3. Preflight The Contract

Run:

```bash
"$HOME/.claude-power-pack-managed/run-assistant-runtime.sh" status
```

Expected transition:

- before edits: `deployment-readiness: managed-blocked`
- after required values are real: `deployment-readiness: managed-ready`

The controller keeps using the same runtime path as self-host and reports:

- per-component process state
- Telegram mode/disabled reason
- operator mode
- deployment blockers and warnings

## 4. Start Local Operator Processes

After the status output is clean enough for operator testing:

```bash
"$HOME/.claude-power-pack-managed/run-assistant-runtime.sh" start
"$HOME/.claude-power-pack-managed/run-assistant-runtime.sh" logs
"$HOME/.claude-power-pack-managed/run-assistant-runtime.sh" stop
```

Notes:

- process health is verified on the local bind ports
- `ASSISTANT_API_PUBLIC_BASE_URL` remains the external HTTPS origin contract used by the product
- this step keeps the shared runtime/controller alive for the live validation commands below

## 5. Run Repeatable Operator Smoke

Before any live env-specific validation, capture the mock-mode operator report:

```bash
python3 scripts/assistant/run_operator_smoke.py
```

The mock section of this report now verifies:

- auth/session callback success
- Telegram mock link completion on the existing companion surface
- reminder follow-up policy visibility through `/v1/reminders` and `/v1/jobs`
- runtime `available_at` / `attempt_count` exposure for reminder follow-up
- memory export/delete/checkpoint behavior on the same runtime

Reminder follow-up policy stays on web/operator surfaces only. Telegram keeps the summary-safe/action-safe boundary and does not administer retry policy.

Artifact:

- `artifacts/operator_smoke/assistant_api_operator_smoke.json`

## 6. Run Live Provider Validation

If the public callback URL is different from the local bind URL, optionally point validation traffic at the local runtime:

```bash
export ASSISTANT_OPERATOR_VALIDATION_API_BASE_URL="http://127.0.0.1:8000"
```

Then run:

```bash
python3 scripts/assistant/run_operator_smoke.py --live-provider-wait-seconds 180
```

Expected outcomes:

- if required env is still missing: `live_provider_validation.status=blocked`
- if env is real but the browser step has not finished yet: `live_provider_validation.status=manual-step-required`
- if the operator completes the provider login and the callback reaches the configured public base URL before timeout: `live_provider_validation.status=pass`

## 7. Run Live Telegram Validation

After the Telegram polling transport is running with a real bot token:

```bash
python3 scripts/assistant/run_telegram_live_validation.py --wait-seconds 180
```

Expected outcomes:

- if bot env is missing: `live_telegram_validation.status=blocked`
- if the deep link has not been opened from Telegram yet: `live_telegram_validation.status=manual-step-required`
- if the real `/start <token>` path completes and writes resume metadata: `live_telegram_validation.status=pass`

Artifacts:

- `artifacts/operator_smoke/assistant_api_operator_smoke.json`
- `artifacts/telegram_smoke/assistant_api_telegram_live_validation.json`

## 8. Explicit Non-Goals

- no hosted vendor provisioning
- no alternate backend or alternate web app
