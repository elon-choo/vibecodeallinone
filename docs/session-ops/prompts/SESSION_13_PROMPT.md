# SESSION_13_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S13`이며, 목적은 **assistant-web surface와 browser smoke를 새 backend contracts에 맞추는 것**이다.

## Session Size Gate

- 이번 세션은 `assistant-web + browser smoke`만 다룬다.
- install story 재작업이나 backend foundation 재설계는 이번 세션 범위가 아니다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/README.md`
6. `docs/session-ops/01_SESSION_BOARD.md`
7. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
8. `docs/session-ops/15_EXECUTION_WAVES.md`
9. `docs/session-ops/handovers/SESSION_12_HANDOVER.md`
10. `README.md`
11. `services/assistant-api/README.md`
12. `packages/contracts/README.md`
13. `packages/contracts/openapi/assistant-api.openapi.yaml`
14. `apps/assistant-web/README.md`
15. `apps/assistant-web/index.html`
16. `apps/assistant-web/app.js`
17. `apps/assistant-web/styles.css`
18. `scripts/assistant/run_browser_smoke.py`
19. `tests/test_assistant_api_runtime.py`

## 이번 세션의 핵심 미션

1. `assistant-web`가 새 backend state를 읽고 표시할 수 있게 최소 확장한다.
   - Telegram link state
   - checkpoint continuity metadata
   - auditable jobs
2. browser smoke를 이 새 state에 맞게 최소 갱신한다.
3. backend contract를 다시 바꾸지 않고 필요한 연결만 맞춘다.
4. `SESSION_14_PROMPT.md`로 넘긴다.

## 강한 제약

1. install story를 다시 열지 마라.
2. S12 backend contract shape를 함부로 바꾸지 마라.
3. Telegram 실제 bot/runtime 구현까지 이번 세션에 넣지 마라.
4. mock-only Telegram 경로는 browser smoke/test 전용으로만 써라.
