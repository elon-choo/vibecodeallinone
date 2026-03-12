# Managed Quickstart Contract

This directory defines the `managed quickstart` deployment contract that sits on top of the same assistant runtime used by the self-host reference stack.

## Boundary

- `self-host` and `managed-quickstart` use the same runtime pieces:
  - `assistant-api`
  - `assistant-web`
  - worker
  - Telegram transport
- `managed quickstart` is an operator mode and env/secret contract, not a second backend or a forked web app.
- the buildable path in this repo is still the self-host reference stack
- hosted rollout automation remains a later session concern

## Operator Bootstrap Artifact

Generate a managed quickstart operator workspace with:

```bash
bash scripts/assistant/bootstrap_managed_quickstart.sh --target "$HOME/.claude-power-pack-managed"
```

That workspace contains:

- `assistant-runtime.env`
- `assistant-runtime.managed.env.example`
- `run-assistant-api.sh`
- `run-assistant-web.sh`
- `run-assistant-worker.sh`
- `run-assistant-telegram.sh`
- `run-assistant-runtime.sh`
- local `data/`, `artifacts/`, `logs/`, and `run/` directories

The generated env intentionally starts in `managed-blocked` until placeholder values are replaced. Use:

```bash
"$HOME/.claude-power-pack-managed/run-assistant-runtime.sh" status
```

The detailed operator sequence lives in [RUNBOOK.md](RUNBOOK.md).

## Required Operator Mode

Set:

```bash
export ASSISTANT_RUNTIME_OPERATOR_MODE="managed-quickstart"
```

This switches the runtime/readiness surface from `self-host-ready` checks to `managed-ready` or `managed-blocked` checks while keeping the same `reference_stack.sh` controller.

## Required Managed Quickstart Config

These values are required before the managed quickstart contract is considered ready:

- `ASSISTANT_API_PUBLIC_BASE_URL`
  - must be a public `https://` API origin
- `ASSISTANT_API_WEB_ALLOWED_ORIGINS`
  - must contain only public `https://` web origins
- `ASSISTANT_API_PROVIDER_MODE=oidc`
- `ASSISTANT_API_PROVIDER_CLIENT_ID`
- `ASSISTANT_API_PROVIDER_AUTH_URL`
- `ASSISTANT_API_PROVIDER_TOKEN_URL`
- `ASSISTANT_API_SECURE_COOKIES=true`

## Secret Contract

Secrets stay server-side only. They are never exposed through browser routes or Telegram surfaces.

- `ASSISTANT_API_PROVIDER_CLIENT_SECRET`
  - required when the chosen OIDC provider uses a confidential client
- `ASSISTANT_API_TELEGRAM_BOT_TOKEN`
  - required only when Telegram is enabled for the managed deployment

## Recommended Inputs

- `ASSISTANT_API_RELEASE_CHANNEL=managed-quickstart`
- `ASSISTANT_API_PROVIDER_USERINFO_URL`
- `ASSISTANT_API_TELEGRAM_BOT_USERNAME`
- `ASSISTANT_API_TELEGRAM_BOT_LINK_BASE_URL`

## Telegram Rule

- `ASSISTANT_RUNTIME_TELEGRAM_MODE=auto`
  - allowed; Telegram remains disabled until a bot token is configured
- `ASSISTANT_RUNTIME_TELEGRAM_MODE=enabled`
  - requires `ASSISTANT_API_TELEGRAM_BOT_TOKEN`
- `ASSISTANT_RUNTIME_TELEGRAM_MODE=disabled`
  - keeps Telegram out of the operator path entirely

## Files

- [assistant-runtime.managed.env.example](assistant-runtime.managed.env.example)
  - operator-facing template for the managed quickstart env file
- [RUNBOOK.md](RUNBOOK.md)
  - step-by-step operator bootstrap/runbook for the managed quickstart workspace

## Runtime Surface

The existing stack controller exposes the boundary:

- `operator-mode: self-host|managed-quickstart`
- `deployment-readiness: self-host-ready|managed-ready|managed-blocked`
- `deployment-blocker: ...`
- `deployment-warning: ...`

Run:

```bash
python3 scripts/assistant/deployment_contract.py --format json
python3 scripts/assistant/run_operator_smoke.py
```

For live operator validation after the contract reaches `managed-ready`:

```bash
export ASSISTANT_OPERATOR_VALIDATION_API_BASE_URL="http://127.0.0.1:8000" # optional local request target
python3 scripts/assistant/run_operator_smoke.py --live-provider-wait-seconds 180 --live-telegram-wait-seconds 180
python3 scripts/assistant/run_telegram_live_validation.py --wait-seconds 180
```

Notes:

- `ASSISTANT_OPERATOR_VALIDATION_API_BASE_URL` is optional and only changes where the validation requests are sent
- the public callback contract still comes from `ASSISTANT_API_PUBLIC_BASE_URL`
- the repeatable mock operator smoke now includes Telegram link + reminder follow-up visibility checks via `/v1/reminders` and `/v1/jobs`; retry policy stays on web/operator surfaces and is never administered from Telegram
- the live validation artifacts stay explicit when env or manual operator steps are missing:
  - `artifacts/operator_smoke/assistant_api_operator_smoke.json`
  - `artifacts/telegram_smoke/assistant_api_telegram_live_validation.json`

Or, inside a bootstrapped workspace:

```bash
./run-assistant-runtime.sh status
```

## Explicitly Not In Scope Here

- hosted vendor lock-in
- infra provisioning
