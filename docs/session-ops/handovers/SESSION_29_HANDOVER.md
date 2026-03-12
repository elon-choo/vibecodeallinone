# SESSION_29_HANDOVER

## 1. Session Outcome

`S29` completed the follow-up control-plane/operator alignment slice of the active reminder-policy mini-wave.

This session consumed the additive `S28` reminder follow-up contract without reopening backend shape redesign, managed quickstart/live validation work, KG memory broker changes, or broad reminder planner UX work.

It aligned the follow-up path by:

1. extending `assistant-web` reminder scheduling so the web control plane can opt into retry-based `follow_up_policy` while keeping the default one-shot path unchanged
2. rendering reminder follow-up policy/state, retry-ready summary, and runtime `available_at` / `attempt_count` visibility in the reminder shell and job ledger
3. updating browser smoke and operator smoke so both repeatable flows now observe the follow-up path explicitly
4. refreshing web/API/operator docs so the reminder follow-up boundary is consistent and Telegram remains summary-safe/action-safe

## 2. Files Updated

### Web / smoke / docs

1. `apps/assistant-web/index.html`
2. `apps/assistant-web/app.js`
3. `apps/assistant-web/styles.css`
4. `apps/assistant-web/README.md`
5. `scripts/assistant/run_browser_smoke.py`
6. `scripts/assistant/run_operator_smoke.py`
7. `services/assistant-api/README.md`
8. `ops/managed/README.md`
9. `ops/managed/RUNBOOK.md`

### Canonical session docs

1. `docs/session-ops/01_SESSION_BOARD.md`
2. `docs/session-ops/handovers/SESSION_29_HANDOVER.md`
3. `docs/session-ops/prompts/SESSION_30_PROMPT.md`

### Root mirrors

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `HANDOVER.md`
4. `NEXT_SESSION_PROMPT.md`

## 3. Main Decisions Locked

1. Web follow-up control stays additive-only: `Schedule Reminder` now optionally sends `follow_up_policy` on create, but the default schedule/cancel path still remains one-shot and unchanged.
2. Follow-up visibility now lives on the same reminder/job surfaces: reminder cards show policy/state and the runtime ledger shows `available_at`, `attempt_count`, and flattened follow-up detail keys.
3. Telegram remains delivery-only/action-safe: it can summarize reminder/follow-up state but cannot administer retry policy, snooze/reschedule, or raw broker scope.
4. Browser/operator smoke now treat follow-up observation as a first-class check:
   - browser smoke verifies retry-configured reminder render on the web shell
   - operator smoke verifies retry-configured reminder visibility through `/v1/reminders` and `/v1/jobs`
5. Snooze/reschedule remain backend/store seams only in this wave; no new public reminder admin routes were added in `S29`.

## 4. Scope Boundary Kept

This session intentionally did **not** do the following:

1. no backend contract reshaping beyond consuming the landed `S28` fields
2. no managed quickstart/live provider/live Telegram pass work
3. no KG memory broker redesign
4. no broad reminder planner/admin UX redesign
5. no Telegram-side reminder follow-up admin surface

## 5. Remaining Gaps After S29

1. `S30` still needs to refresh reminder-policy evidence/validation/doc sync and close the mini-wave honestly.
2. recurring reminders, public snooze/reschedule routes, and broader planner/admin UX remain later work outside this mini-wave.
3. live provider/live Telegram pass evidence still depends on external managed env and remains outside this reminder-policy closeout scope.

## 6. Validation

- `node --check apps/assistant-web/app.js` -> pass
- `python3 -m py_compile scripts/assistant/run_browser_smoke.py scripts/assistant/run_operator_smoke.py` -> pass
- `python3 scripts/assistant/run_operator_smoke.py` -> pass
  - mock smoke status `pass`
  - explicit follow-up check: `reminder_follow_up_policy`
- `python3 scripts/assistant/run_browser_smoke.py` -> pass
  - explicit follow-up check: `reminder_follow_up_policy_surface`
- `.agent-orchestrator/config.json` validation commands -> pass
  - `ruff check services/assistant-api/assistant_api/*.py tests/test_assistant_api_runtime.py tests/test_assistant_api_worker.py tests/test_assistant_api_telegram.py`
  - `node --check apps/assistant-web/app.js`
  - `python3 -m pytest tests/test_ralphloop_artifact_io.py tests/test_ralphloop_trust_bundle.py tests/test_assistant_api_runtime.py tests/test_assistant_api_worker.py tests/test_assistant_api_telegram.py -q`

Notes:

- pytest still emits the existing coverage warning (`No data was collected`) even when the configured suite passes

## 7. Next Session Recommendation

The next official session should be `S30 reminder-policy closeout`.

`docs/session-ops/prompts/SESSION_30_PROMPT.md` has been created and `NEXT_SESSION_PROMPT.md` now mirrors it.

The chain should continue strictly as:

`S30`
