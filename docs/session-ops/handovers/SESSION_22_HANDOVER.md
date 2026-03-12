# SESSION_22_HANDOVER

## 1. Session Outcome

`S22` completed the managed quickstart deployment contract slice on top of the existing self-host reference stack.

This session stayed inside the locked contract/ops/docs scope and did not reopen hosted rollout, live provider validation, web onboarding redesign, KG memory broker work, or reminder policy work.

It landed the contract by:

1. adding `scripts/assistant/deployment_contract.py` as the single helper for operator mode and managed quickstart readiness on the shared runtime path
2. locking self-host bootstrap output to `ASSISTANT_RUNTIME_OPERATOR_MODE=self-host`
3. extending `reference_stack.sh` and `run_operator_smoke.py` to surface operator mode plus deployment readiness without introducing a second runtime/controller
4. adding `ops/managed/README.md` and `ops/managed/assistant-runtime.managed.env.example` as operator-facing contract/template artifacts
5. refreshing top-level runtime docs so self-host vs managed quickstart boundaries are explicit

## 2. Documents And Files Updated

### Runtime / operator surface

1. `scripts/assistant/bootstrap_runtime.sh`
2. `scripts/assistant/reference_stack.sh`
3. `scripts/assistant/deployment_contract.py`
4. `scripts/assistant/run_operator_smoke.py`
5. `scripts/assistant/run_install_smoke.py`
6. `tests/test_install_smoke.sh`
7. `tests/test_assistant_operator_contract.py`

### Operator docs / templates

1. `README.md`
2. `services/assistant-api/README.md`
3. `apps/assistant-web/README.md`
4. `ops/managed/README.md`
5. `ops/managed/assistant-runtime.managed.env.example`

### Canonical session docs

1. `docs/session-ops/01_SESSION_BOARD.md`
2. `docs/session-ops/handovers/SESSION_22_HANDOVER.md`
3. `docs/session-ops/prompts/SESSION_23_PROMPT.md`

### Root mirrors

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `HANDOVER.md`
4. `NEXT_SESSION_PROMPT.md`

## 3. Main Decisions Locked

1. managed quickstart remains the same runtime path as self-host:
   - `assistant-api`
   - `assistant-web`
   - worker
   - Telegram transport
2. `ASSISTANT_RUNTIME_OPERATOR_MODE` is now the explicit boundary:
   - `self-host`
   - `managed-quickstart`
3. managed quickstart readiness is additive-only and currently contract-driven:
   - public HTTPS base URL/origin
   - `oidc` provider mode
   - secure cookies
   - operator-held secrets
4. self-host bootstrap still defaults to local/mock-safe behavior and remains the only buildable path in this repo today

## 4. Scope Boundary Kept

This session intentionally did **not** do the following:

1. no second backend/runtime path
2. no managed hosting/bootstrap artifact generation yet
3. no live OIDC or real Telegram validation rollout
4. no KG memory broker design
5. no web onboarding redesign

## 5. Remaining Limits After S22

1. managed quickstart still needs a real operator/bootstrap artifact path in `S23`
2. live provider and real Telegram validation remain capability-gated future work for `S24`
3. KG-backed workspace/project memory broker remains deferred to `S25` and `S26`
4. reminder follow-up hardening remains deferred beyond this later wave

## 6. Validation

- `python3 -m pytest tests/test_assistant_operator_contract.py -q` -> pass
- `bash tests/test_install_smoke.sh` -> pass
- `python3 scripts/assistant/run_operator_smoke.py --output /tmp/session22_operator_smoke.json` -> pass
- `ruff check services/assistant-api/assistant_api/*.py tests/test_assistant_api_runtime.py tests/test_assistant_api_worker.py tests/test_assistant_api_telegram.py` -> pass
- `node --check apps/assistant-web/app.js` -> pass
- `python3 -m pytest tests/test_ralphloop_artifact_io.py tests/test_ralphloop_trust_bundle.py tests/test_assistant_api_runtime.py tests/test_assistant_api_worker.py tests/test_assistant_api_telegram.py -q` -> pass

Notes:

- targeted pytest and configured pytest still emit the existing coverage warning (`No data was collected`) even though all tests passed
- operator smoke now reports both:
  - live-provider preflight blockers when env is absent
  - operator mode / deployment readiness for the shared runtime path
- self-host install smoke now asserts `ASSISTANT_RUNTIME_OPERATOR_MODE=self-host` and `deployment-readiness: self-host-ready`

## 7. Next Session Recommendation

The next official session should be `S23 managed quickstart operator/bootstrap path`.

Use:

1. `docs/session-ops/prompts/SESSION_23_PROMPT.md`
2. `NEXT_SESSION_PROMPT.md`

That session should convert the new contract/template into real operator/bootstrap artifacts and smoke alignment while preserving the self-host fallback path.
