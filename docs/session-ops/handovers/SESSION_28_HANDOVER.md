# SESSION_28_HANDOVER

## 1. Session Outcome

`S28` completed the reminder follow-up policy contract/runtime slice of the active reminder-policy mini-wave.

This session stayed inside the locked backend/contracts/docs scope and did not reopen web control-plane redesign, managed quickstart/live validation work, KG memory broker changes, or broad reminder planner productization.

It hardened reminder follow-up by:

1. adding additive `follow_up_policy` and `follow_up_state` contract/model fields on the existing reminder routes
2. exposing explicit reminder execution state through the reminder record plus runtime job `available_at` / `attempt_count`
3. adding store seams for snooze/reschedule-ready state and retry/dead-letter-ready transitions on top of the current reminder lifecycle
4. updating the worker so retryable failures requeue the same auditable reminder job while terminal failures land in explicit dead-letter state
5. extending backend tests and API docs without breaking the existing one-shot schedule/cancel path

## 2. Files Updated

### Contracts / runtime

1. `packages/contracts/openapi/assistant-api.openapi.yaml`
2. `packages/contracts/schemas/jobs/runtime-job-record.schema.json`
3. `packages/contracts/schemas/reminders/reminder-create-request.schema.json`
4. `packages/contracts/schemas/reminders/reminder-follow-up-policy.schema.json`
5. `packages/contracts/schemas/reminders/reminder-follow-up-state.schema.json`
6. `packages/contracts/schemas/reminders/reminder-record.schema.json`
7. `services/assistant-api/assistant_api/models.py`
8. `services/assistant-api/assistant_api/store.py`
9. `services/assistant-api/assistant_api/app.py`
10. `services/assistant-api/assistant_api/worker.py`
11. `services/assistant-api/migrations/0001_bootstrap.sql`

### Validation / docs

1. `services/assistant-api/README.md`
2. `tests/test_assistant_api_runtime.py`
3. `tests/test_assistant_api_worker.py`

### Canonical session docs

1. `docs/session-ops/01_SESSION_BOARD.md`
2. `docs/session-ops/handovers/SESSION_28_HANDOVER.md`
3. `docs/session-ops/prompts/SESSION_29_PROMPT.md`

### Root mirrors

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `HANDOVER.md`
4. `NEXT_SESSION_PROMPT.md`

## 3. Main Decisions Locked

1. `POST /v1/reminders` remains additive-only and now accepts an optional `follow_up_policy`; existing create/list/cancel routes and one-shot defaults still work without change.
2. `follow_up_policy.max_attempts` is total-attempt based, including the first delivery attempt; default one-shot reminders keep `on_failure=none`, `max_attempts=1`.
3. Reminder responses now expose explicit `follow_up_state`; runtime jobs now expose `available_at` and `attempt_count` so retry/hold state is visible in the auditable job surface.
4. Retryable failures reuse the same `reminder_id` / `job_id` and requeue the existing runtime job instead of creating hidden side jobs.
5. Snooze/reschedule land in `S28` as backend/store seams only; Telegram remains delivery-only/action-safe and web control-plane exposure is deferred to `S29`.

## 4. Scope Boundary Kept

This session intentionally did **not** do the following:

1. no `assistant-web` reminder UX or planner redesign
2. no browser/operator smoke changes yet
3. no managed quickstart/live provider or live Telegram validation work
4. no KG memory broker or workspace memory redesign
5. no recurring reminder productization

## 5. Remaining Gaps After S28

1. `S29` still needs to expose the new follow-up policy/state minimally through the web control plane, operator docs, and smoke coverage.
2. `S30` still needs to refresh reminder-policy evidence/validation and close the mini-wave honestly.
3. recurring reminders and broader admin workflows remain future work outside this mini-wave.

## 6. Validation

- `python3 -m pytest tests/test_assistant_api_runtime.py -q -k reminder` -> pass
- `python3 -m pytest tests/test_assistant_api_worker.py -q -k "reminder or dead_letter or snooze or reschedule"` -> pass
- `ruff check services/assistant-api/assistant_api/*.py tests/test_assistant_api_runtime.py tests/test_assistant_api_worker.py tests/test_assistant_api_telegram.py` -> pass
- `python3 -m pytest tests/test_assistant_api_runtime.py tests/test_assistant_api_worker.py tests/test_assistant_api_telegram.py -q` -> pass
- `.agent-orchestrator/config.json` validation commands -> pass
  - `ruff check services/assistant-api/assistant_api/*.py tests/test_assistant_api_runtime.py tests/test_assistant_api_worker.py tests/test_assistant_api_telegram.py`
  - `node --check apps/assistant-web/app.js`
  - `python3 -m pytest tests/test_ralphloop_artifact_io.py tests/test_ralphloop_trust_bundle.py tests/test_assistant_api_runtime.py tests/test_assistant_api_worker.py tests/test_assistant_api_telegram.py -q`

Notes:

- pytest still emits the existing coverage warning (`No data was collected`) even when the targeted/configured suites pass

## 7. Next Session Recommendation

The next official session should be `S29 follow-up control-plane/operator alignment`.

`docs/session-ops/prompts/SESSION_29_PROMPT.md` has been created and `NEXT_SESSION_PROMPT.md` now mirrors it.

The chain should continue strictly as:

`S29 -> S30`
