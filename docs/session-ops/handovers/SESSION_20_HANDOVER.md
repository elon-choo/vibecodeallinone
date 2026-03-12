# SESSION_20_HANDOVER

## 1. Session Outcome

`S20` completed the one-command self-host reference stack slice of the resumed next wave.

This session stayed inside the locked install/ops/docs packaging scope and did not reopen backend contract redesign, web surface redesign, managed quickstart, or broad infra work.

It turned the thin bootstrap into an operator-ready reference stack by:

1. adding a generated stack controller with `start|stop|restart|status|logs`
2. bundling API, web, worker, and Telegram polling launchers into the same bootstrap workspace
3. defaulting Telegram to an `auto` operator mode so local startup still works before a bot token is configured
4. extending install smoke from scaffold-only checks to real stack start/stop validation
5. refreshing self-host docs to match the current reference-stack behavior

## 2. Files Updated

### Runtime / packaging

1. `scripts/assistant/reference_stack.sh`
2. `scripts/assistant/bootstrap_runtime.sh`
3. `scripts/install.sh`

### Smoke / validation

1. `tests/test_install_smoke.sh`
2. `scripts/assistant/run_install_smoke.py`

### Docs

1. `README.md`
2. `services/assistant-api/README.md`
3. `apps/assistant-web/README.md`

### Canonical session docs

1. `docs/session-ops/01_SESSION_BOARD.md`
2. `docs/session-ops/handovers/SESSION_20_HANDOVER.md`
3. `docs/session-ops/prompts/SESSION_21_PROMPT.md`

### Root mirrors

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `HANDOVER.md`
4. `NEXT_SESSION_PROMPT.md`

## 3. Main Decisions Locked

1. the bootstrapped workspace is now the self-host reference stack control point, not a two-process scaffold
2. `run-assistant-runtime.sh` is the operator entrypoint and now owns `start|stop|restart|status|logs`
3. Telegram stays in the same operator story as API/web/worker, but defaults to `ASSISTANT_RUNTIME_TELEGRAM_MODE=auto` so missing bot credentials do not block local startup
4. install/reference-stack smoke now proves real process start/stop for API, web, and worker instead of checking files only
5. self-host docs should describe the implemented reference stack and explicitly keep managed quickstart/cloud deployment deferred

## 4. Scope Boundary Kept

This session intentionally did **not** do the following:

1. no backend response/schema redesign
2. no `assistant-web` UI redesign
3. no managed quickstart implementation
4. no Kubernetes or broader cloud packaging
5. no new Telegram product-surface behavior beyond packaging the existing polling runtime

## 5. Remaining Gaps After S20

1. release-evidence closeout still remains for `S21`
2. canonical closeout docs and final chain decision still need to be written after the full smoke set is rerun together
3. managed quickstart, webhook ingress, and broader Telegram admin surfaces remain future work

## 6. Validation

- `bash tests/test_install_smoke.sh` -> pass
- `python3 scripts/assistant/run_install_smoke.py` -> pass
- `python3 scripts/assistant/run_telegram_mock_smoke.py` -> pass
- `ruff check services/assistant-api/assistant_api/*.py tests/test_assistant_api_runtime.py tests/test_assistant_api_worker.py tests/test_assistant_api_telegram.py` -> pass
- `node --check apps/assistant-web/app.js` -> pass
- `python3 -m pytest tests/test_ralphloop_artifact_io.py tests/test_ralphloop_trust_bundle.py tests/test_assistant_api_runtime.py tests/test_assistant_api_worker.py tests/test_assistant_api_telegram.py -q` -> pass
- `.agent-orchestrator/config.json` validation commands -> pass

Notes:

- install smoke now writes `artifacts/install_smoke/assistant_runtime_install_smoke.json` with three checks
- Telegram mock smoke still passes as a separate API/runtime evidence path
- pytest still emits the existing coverage warning (`No data was collected`) even though the targeted suite passed

## 7. Next Session Recommendation

The next official session should be `S21 closeout`.

`docs/session-ops/prompts/SESSION_21_PROMPT.md` has been created and `NEXT_SESSION_PROMPT.md` now mirrors it.

The chain should continue strictly as:

`S21`
