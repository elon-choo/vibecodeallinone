# Assistant Web Shell

Static, mobile-first shell for:

- OpenAI-first auth start
- Telegram companion link state
- Telegram reminder scheduling, cancel visibility, and follow-up policy control
- first-party session read
- explicit memory CRUD with provenance display
- web-only workspace memory broker opt-in and probe state
- memory export/download and delete queue feedback
- checkpoint resume sync with continuity metadata and local-vs-server conflict recovery
- auditable runtime job visibility
- trust summary visibility

## Run locally

If you already bootstrapped the self-host reference stack, use:

- `"$HOME/.claude-power-pack-assistant/run-assistant-runtime.sh" start`
- `"$HOME/.claude-power-pack-assistant/run-assistant-runtime.sh" status`

If you are preparing the managed quickstart operator path, use:

- `bash scripts/assistant/bootstrap_managed_quickstart.sh --target "$HOME/.claude-power-pack-managed"`
- `"$HOME/.claude-power-pack-managed/run-assistant-runtime.sh" status`

Manual surface-only flow:

1. Start `assistant-api`:
   - `PYTHONPATH=services/assistant-api python3 -m assistant_api.main`
2. Serve this folder:
   - `cd apps/assistant-web`
   - `python3 -m http.server 4173`
3. Open `http://127.0.0.1:4173`

## Runtime notes

- The shell talks directly to `assistant-api` with `credentials: include`.
- API base defaults to `http://127.0.0.1:8000` and can be changed in the top control field.
- In the bootstrapped reference stack, this shell is served by the same `run-assistant-runtime.sh start` command that also manages API, worker, and optional Telegram polling.
- Managed quickstart reuses this same shell; only the public origin/env contract changes, not the web app path.
- The managed quickstart operator workspace stays on the same controller surface and starts as `managed-blocked` until placeholder env values are replaced.
- Cached snapshots for session, trust, memory, checkpoint draft, and last export live in IndexedDB under `assistant-web-shell`.
- Reminder times are entered in the browser's local timezone and sent to `assistant-api` as ISO timestamps.
- Reminder follow-up policy is configured from the web control plane only. Retry-ready, retry-scheduled, snoozed, rescheduled, dead-letter state, plus runtime `available_at` / `attempt_count`, stay visible in the reminder card and runtime ledger while Telegram keeps the summary-safe/action-safe boundary.
- Local bootstrap works with `ASSISTANT_API_PROVIDER_MODE=mock`.
- For a real OIDC/OpenAI-compatible flow, set the provider auth/token/userinfo env vars on `assistant-api`.
- The shell keeps a local draft checkpoint separate from the latest server checkpoint and offers `Use Server Copy` or `Keep Local Draft` when a conflict is detected.

Repeatable browser smoke:
- `python3 scripts/assistant/run_browser_smoke.py`
- The smoke starts a temporary `assistant-api` fixture in mock mode, serves this static shell, and verifies:
  - stale trust fallback copy
  - auth round trip
  - Telegram link state render
  - reminder follow-up policy render
  - reminder schedule/cancel render
  - workspace broker opt-in/control render
  - checkpoint continuity metadata render
  - memory save + provenance render
  - memory export download
  - memory delete pending-purge receipt
  - auditable job visibility
