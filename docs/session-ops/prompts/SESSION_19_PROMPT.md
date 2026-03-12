# SESSION_19_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S19`이며, 목적은 **assistant-web를 reminder/runtime 상태에 맞추고 browser smoke를 갱신하는 것**이다.

## Official Chain Note

- 이 prompt는 `S18`이 reminder backend + delivery로 종료된 뒤 이어지는 canonical next-session prompt다.
- canonical next-wave context는 `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`에 잠겨 있다.
- 이번 세션 종료 시 `S20`가 여전히 다음 세션이면 `docs/session-ops/prompts/SESSION_20_PROMPT.md`를 만들고 `NEXT_SESSION_PROMPT.md`에 mirror하라.

## Session Size Gate

- 이번 세션은 `web control plane + browser smoke`만 다룬다.
- backend contract 재설계, install packaging, managed quickstart는 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`
7. `docs/session-ops/handovers/SESSION_18_HANDOVER.md`
8. `apps/assistant-web/README.md`
9. `apps/assistant-web/index.html`
10. `apps/assistant-web/app.js`
11. `apps/assistant-web/styles.css`
12. `scripts/assistant/run_browser_smoke.py`
13. `services/assistant-api/README.md`
14. `packages/contracts/openapi/assistant-api.openapi.yaml`
15. `tests/test_assistant_api_runtime.py`

## 이번 세션의 핵심 미션

1. reminder/runtime 상태를 web control plane에 최소 노출한다.
2. Telegram link/continuity/reminder 상태를 backend contract churn 없이 정리한다.
3. browser smoke를 새 runtime state에 맞게 갱신한다.
4. docs를 최소 갱신한다.

## 강한 제약

1. backend shape를 크게 바꾸지 마라.
2. install/bootstrap story를 다시 열지 마라.
3. packaging/managed quickstart를 이번 세션에서 열지 마라.
4. UI를 넓게 재디자인하지 마라.

## 기대 산출물

1. web control-plane alignment
2. browser smoke alignment
3. 최소 docs refresh
4. `SESSION_19_HANDOVER.md`
5. 다음 세션이 계속되면 `SESSION_20_PROMPT.md`와 `NEXT_SESSION_PROMPT.md` mirror

## 종료 조건

1. browser smoke가 new reminder/runtime/Telegram state를 실제로 밟는다.
2. auth/memory/trust 기존 흐름이 유지된다.
3. validation이 통과한다.

## 필수 validation

1. `node --check apps/assistant-web/app.js`
2. `python3 scripts/assistant/run_browser_smoke.py`
3. `.agent-orchestrator/config.json`의 validation 명령
