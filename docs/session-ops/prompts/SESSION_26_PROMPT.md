# SESSION_26_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S26`이며, 목적은 **memory broker opt-in/control state를 web control plane과 smoke에 반영하는 것**이다.

## Activation Note

- 이 prompt는 `S25`에서 opt-in KG memory broker backend/contracts foundation이 additive-only path로 landing된 뒤 공식 `SESSION_26` prompt로 승격된 버전이다.
- 이번 세션은 canonical handover / next prompt / root mirror를 갱신하는 official chain session이다.

## Session Size Gate

- 이번 세션은 `web control plane + browser smoke alignment`만 다룬다.
- managed quickstart infra, Telegram admin surface, reminder follow-up policy는 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/18_POST_S21_LATER_WAVE_ORCHESTRATION_PLAN.md`
7. `docs/session-ops/handovers/SESSION_25_HANDOVER.md`
8. `apps/assistant-web/README.md`
9. `apps/assistant-web/index.html`
10. `apps/assistant-web/app.js`
11. `apps/assistant-web/styles.css`
12. `scripts/assistant/run_browser_smoke.py`
13. `services/assistant-api/README.md`
14. `packages/contracts/openapi/assistant-api.openapi.yaml`

## 이번 세션의 핵심 미션

1. memory broker opt-in/control state를 web control plane에 최소 노출한다.
2. browser smoke가 그 state를 실제로 밟게 만든다.
3. Telegram surface는 summary-safe boundary를 유지한다.
4. docs/handover를 최소 갱신한다.

## 강한 제약

1. `S25`에서 landing한 backend shape를 크게 다시 바꾸지 마라.
2. Telegram이 full memory admin UI처럼 동작하게 만들지 마라.
3. managed quickstart/live validation scope를 이번 세션에서 다시 열지 마라.
4. reminder follow-up policy를 이번 세션에 끌어오지 마라.

## 기대 산출물

1. web control-plane alignment for broker opt-in/control
2. browser smoke alignment
3. 최소 docs refresh
4. `SESSION_26_HANDOVER.md`와 `SESSION_27` next prompt

## 종료 조건

1. browser smoke가 broker opt-in/control path를 실제로 밟는다.
2. existing reminder/continuity/runtime shell behavior가 유지된다.
3. Telegram summary-safe boundary가 유지된다.
4. validation이 통과한다.

## 필수 validation

1. `.agent-orchestrator/config.json`의 validation 명령
2. 이번 세션에서 추가/갱신한 browser smoke + broker opt-in checks
