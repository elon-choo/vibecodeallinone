# SESSION_12_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S12`이며, 목적은 **contracts + assistant-api foundation만 확장하는 것**이다.

## Session Size Gate

- 이번 세션은 `contracts/backend`만 다룬다.
- web surface와 smoke 확장은 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/README.md`
6. `docs/session-ops/01_SESSION_BOARD.md`
7. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
8. `docs/session-ops/15_EXECUTION_WAVES.md`
9. `docs/session-ops/handovers/SESSION_11_HANDOVER.md`
10. `README.md`
11. `scripts/assistant/bootstrap_runtime.sh`
12. `services/assistant-api/README.md`
13. `packages/contracts/README.md`
14. `packages/contracts/openapi/assistant-api.openapi.yaml`
15. `services/assistant-api/assistant_api/models.py`
16. `services/assistant-api/assistant_api/store.py`
17. `services/assistant-api/assistant_api/app.py`
18. `tests/test_assistant_api_runtime.py`

## 이번 세션의 핵심 미션

1. public contract를 최소 확장한다.
   - Telegram link state
   - checkpoint continuity metadata
   - auditable jobs
2. `assistant-api` migration/model/store/app foundation을 확장한다.
3. backend test를 추가/갱신한다.
4. `SESSION_13_PROMPT.md`로 넘긴다.

## 강한 제약

1. install story를 다시 열지 마라.
2. S11 bootstrap entry는 유지하고 backend 호환성만 맞춰라.
3. web shell 대규모 UI 작업은 다음 세션으로 넘겨라.
4. mock-only Telegram 경로는 smoke/test 전용으로 감춰라.
