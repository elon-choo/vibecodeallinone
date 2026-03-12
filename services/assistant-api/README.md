# Assistant API Bootstrap

This directory is the future runtime boundary for:
- OpenAI-first auth handshake
- First-party session ownership
- Chat orchestration
- Memory CRUD and export/delete
- Session checkpoint sync and continuity metadata
- Telegram companion link state
- Auditable runtime jobs
- Trust summary lookup

Current state:
- FastAPI bootstrap runtime exists in `assistant_api/`
- separate runtime worker entrypoint exists in `assistant_api/worker.py` and `scripts/assistant/run_job_worker.py`
- separate Telegram polling transport exists in `assistant_api/telegram_transport.py` and `scripts/assistant/run_telegram_transport.py`
- SQLite bootstrap storage and migration draft live in `migrations/0001_bootstrap.sql`
- Source of truth still lives in `packages/contracts`
- Public trust summary shape still comes from `packages/evidence-contracts`
- Telegram link state and auditable job list are now exposed from the same runtime boundary

Initial route map:
- `POST /v1/auth/openai/start`
- `GET /v1/auth/openai/callback`
- `GET /v1/auth/session`
- `GET|POST /v1/surfaces/telegram/link`
- `GET|POST /v1/reminders`
- `DELETE /v1/reminders/{reminderId}`
- `GET|POST /v1/memory/items`
- `GET /v1/memory/broker/workspaces`
- `GET|PUT /v1/memory/broker/workspaces/{workspaceId}`
- `POST /v1/memory/broker/workspaces/{workspaceId}/query`
- `POST /v1/memory/exports`
- `PATCH|DELETE /v1/memory/items/{memoryId}`
- `GET|PUT /v1/checkpoints/current`
- `GET /v1/jobs`
- `GET /v1/trust/current`
- `GET /v1/trust/bundles/{bundleId}`

Bootstrap rules:
- Provider tokens stay server-side only.
- `assistant-api` resolves trust via `app_version -> bundle_id -> evidence_summary`.
- Raw Ralph Loop artifacts are never exposed through user-facing routes.

Implemented bootstrap pieces:
- session middleware that resolves the first-party `assistant_session` cookie
- `POST /v1/auth/openai/start` issuing a pending first-party session plus PKCE/state tracking
- `GET /v1/auth/openai/callback` completing the provider round trip and redirecting back to `assistant-web`
- local `mock` provider mode for end-to-end bootstrap without external credentials
- `GET|POST /v1/surfaces/telegram/link` for pending/linked Telegram companion state
- hidden mock-only Telegram completion route for backend tests and later smoke
- polling-first Telegram transport that can complete linking from a real `/start <token>` bot message
- Telegram-originated resume and quick-capture continuity updates on the linked web/PWA checkpoint
- memory CRUD with `memory_source` provenance write/read against SQLite
- memory export bundle generation plus executable delete receipts for purge follow-up
- checkpoint upsert/read with optimistic conflict detection (`base_version`, `force`) plus continuity metadata
- opt-in workspace/project memory broker state plus additive workspace-scoped query path
- auditable job projection for export/delete/reminder flows via `GET /v1/jobs`
- runtime job lease/claim lifecycle for a separate worker process
- public reminder create/list/cancel routes with worker-driven Telegram delivery audit
- additive reminder follow-up policy/state on the same contract, including retry scheduling, dead-letter visibility, and snooze/reschedule-ready store seams
- trust lookup that prefers `evidence_ref` and falls back to the latest published bundle
- `assistant-web` now consumes broker opt-in/control state plus minimal reminder follow-up control/state from the same runtime boundary while Telegram stays summary-safe only

Run locally:
- Bootstrapped reference stack workspace:
  - `bash scripts/assistant/bootstrap_runtime.sh --target "$HOME/.claude-power-pack-assistant"`
  - `"$HOME/.claude-power-pack-assistant/run-assistant-runtime.sh" start`
  - `"$HOME/.claude-power-pack-assistant/run-assistant-runtime.sh" status`
- Managed quickstart operator workspace:
  - `bash scripts/assistant/bootstrap_managed_quickstart.sh --target "$HOME/.claude-power-pack-managed"`
  - `"$HOME/.claude-power-pack-managed/run-assistant-runtime.sh" status`
  - replace placeholder env values, then `"$HOME/.claude-power-pack-managed/run-assistant-runtime.sh" start`
- `PYTHONPATH=services/assistant-api python3 -m assistant_api.main`
- `PYTHONPATH=services/assistant-api python3 scripts/assistant/run_job_worker.py --once`
- `PYTHONPATH=services/assistant-api python3 scripts/assistant/run_telegram_transport.py --once`

Useful env vars:
- `ASSISTANT_RUNTIME_OPERATOR_MODE`: `self-host` or `managed-quickstart` for operator/readiness reporting on the shared stack controller
- `ASSISTANT_RUNTIME_TELEGRAM_MODE`: `auto`, `enabled`, or `disabled` for the generated stack controller
- `ASSISTANT_API_PUBLIC_BASE_URL`: absolute base URL used to build the callback URL
- `ASSISTANT_API_WEB_ALLOWED_ORIGINS`: comma-separated web origins for credentialed CORS
- `ASSISTANT_API_PROVIDER_MODE`: `mock` or `oidc`
- `ASSISTANT_API_PROVIDER_CLIENT_ID`
- `ASSISTANT_API_PROVIDER_CLIENT_SECRET`
- `ASSISTANT_API_PROVIDER_AUTH_URL`
- `ASSISTANT_API_PROVIDER_TOKEN_URL`
- `ASSISTANT_API_PROVIDER_USERINFO_URL`
- `ASSISTANT_API_PROVIDER_SCOPES`
- `ASSISTANT_API_TELEGRAM_BOT_LINK_BASE_URL`: optional `https://t.me/...` prefix or template containing `{token}`
- `ASSISTANT_API_TELEGRAM_BOT_TOKEN`: bot token used by the Telegram polling transport
- `ASSISTANT_API_TELEGRAM_BOT_USERNAME`: optional username used to build `https://t.me/<bot>?start=<token>` deep links
- `ASSISTANT_API_TELEGRAM_API_BASE_URL`: override for Telegram Bot API base URL in self-host or test setups
- `ASSISTANT_API_TELEGRAM_LINK_TTL_SECONDS`: expiry for pending Telegram link state
- `ASSISTANT_API_TELEGRAM_POLL_TIMEOUT_SECONDS`: long-poll timeout for `getUpdates`
- `ASSISTANT_API_MEMORY_DELETE_RETENTION_SECONDS`: delay before queued delete work becomes purge-eligible
- `ASSISTANT_API_WORKER_POLL_INTERVAL_SECONDS`: idle wait between worker polling attempts
- `ASSISTANT_API_WORKER_JOB_LEASE_SECONDS`: lease duration for claimed runtime jobs

Managed quickstart boundary:
- the runtime path stays the same: `assistant-api` + `assistant-web` + worker + Telegram transport
- managed quickstart only changes operator mode and env/secret requirements; it does not introduce a second backend
- operator template and required env/secret contract live in [ops/managed/README.md](../../ops/managed/README.md)
- the operator bootstrap/runbook now lives in [ops/managed/RUNBOOK.md](../../ops/managed/RUNBOOK.md)

Telegram transport notes:
- self-host MVP is `polling-first`; a future webhook path should reuse the same update-processing seam
- current Telegram runtime scope includes link completion, resume handoff refresh, action-safe quick capture, and reminder delivery
- reminder follow-up now has a minimal control-plane path: web can set retry policy on reminder create and inspect follow-up policy/state plus runtime `available_at` / `attempt_count`, while Telegram remains delivery-only and action-safe
- broader Telegram command/admin surfaces remain later sessions
- raw workspace/project memory broker retrieval is never exposed to the Telegram surface
- broker opt-in/control remains a web/PWA control-plane action; Telegram only reflects the safe boundary
- Telegram bot token stays server-side only and is never exposed through browser-facing routes
- the generated reference stack keeps Telegram in the same `start|stop|status` operator path, but defaults to `auto` so startup still works before a bot token is configured

Live OIDC validation checklist:
- Set `ASSISTANT_API_PROVIDER_MODE=oidc`
- Point `ASSISTANT_API_PUBLIC_BASE_URL` at the externally reachable API origin
- Register `${ASSISTANT_API_PUBLIC_BASE_URL}/v1/auth/openai/callback` with the provider
- Set `ASSISTANT_API_WEB_ALLOWED_ORIGINS` to the exact `assistant-web` origin that will send credentialed requests
- Use HTTPS and `ASSISTANT_API_SECURE_COOKIES=true` outside localhost
- Provide `ASSISTANT_API_PROVIDER_CLIENT_ID`, optional `ASSISTANT_API_PROVIDER_CLIENT_SECRET`, and auth/token/userinfo URLs
- Optional: set `ASSISTANT_OPERATOR_VALIDATION_API_BASE_URL` when the operator wants to send validation requests to a local bind URL while keeping the public callback URL contract unchanged
- Optional: set `ASSISTANT_OPERATOR_VALIDATION_WEB_REDIRECT_URI` when the browser callback path is not the default `${first_web_origin}/callback`

Repeatable operator smoke:
- `python3 scripts/assistant/run_operator_smoke.py`
- The script records:
  - live OIDC and live Telegram env preflight blockers when real validation is not possible
  - capability-gated live provider attempt status (`blocked|manual-step-required|pass|fail`)
  - capability-gated live Telegram attempt status (`blocked|manual-step-required|pass|fail`)
  - operator mode / managed quickstart readiness on the shared runtime path
  - a mock-mode auth/session/Telegram link/reminder follow-up/memory/export/delete/checkpoint smoke report under `artifacts/operator_smoke/`
- To wait for a real browser/deep-link step instead of emitting an immediate manual-step-required result:
  - `python3 scripts/assistant/run_operator_smoke.py --live-provider-wait-seconds 180 --live-telegram-wait-seconds 180`
  - `python3 scripts/assistant/run_telegram_live_validation.py --wait-seconds 180`
