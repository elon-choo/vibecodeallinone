# SESSION_29_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S29`이며, 목적은 **reminder follow-up policy state를 web control plane, operator docs, smoke에 최소 반영하는 것**이다.

## Activation Note

- `S28`은 공식 완료 상태이며, 이 문서는 현재 active official next prompt다.
- 이번 세션이 끝나기 전까지 scope를 `follow-up control-plane/operator alignment`로 유지하라.
- canonical handover / next prompt / root mirror는 `S29` closeout 시점에만 갱신하라.

## Why This Objective Now

- `S28`에서 reminder follow-up contract/state와 backend runtime seam이 additive-only로 고정됐다.
- 다음 좁은 step은 그 shape를 다시 바꾸지 않고 web control plane / operator surface / smoke에서 최소 소비 경로를 여는 것이다.
- broad planner redesign이나 managed/live work를 다시 열 필요 없이 현재 저장소 안에서 바로 전진할 수 있다.

## Session Size Gate

- 이번 세션은 `follow-up control-plane/operator alignment`만 다룬다.
- broad planner redesign, managed quickstart live pass, KG memory redesign, recurring reminder productization은 다음 세션 이후로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/20_POST_S27_REMINDER_POLICY_ORCHESTRATION_PLAN.md`
7. `docs/session-ops/21_POST_S27_REMINDER_POLICY_PROMPT_PACK.md`
8. `docs/session-ops/handovers/SESSION_28_HANDOVER.md`
9. `apps/assistant-web/index.html`
10. `apps/assistant-web/app.js`
11. `apps/assistant-web/styles.css`
12. `apps/assistant-web/README.md`
13. `scripts/assistant/run_browser_smoke.py`
14. `scripts/assistant/run_operator_smoke.py`
15. `services/assistant-api/README.md`
16. `packages/contracts/openapi/assistant-api.openapi.yaml`
17. `packages/contracts/schemas/reminders/reminder-record.schema.json`

## 이번 세션의 핵심 미션

1. `S28` follow-up state/actions를 web control plane에 최소 반영한다.
2. operator docs/runbook을 reminder follow-up path 기준으로 정리한다.
3. browser/operator smoke가 그 경로를 실제로 관찰하게 만든다.
4. Telegram boundary는 summary-safe / action-safe를 유지한다.

## 강한 제약

1. backend contract shape를 크게 다시 바꾸지 마라.
2. reminder planner 전체 UX redesign을 이번 세션에서 열지 마라.
3. managed quickstart live validation을 이번 세션에서 다시 열지 마라.
4. KG memory broker나 workspace memory scope redesign을 섞지 마라.

## 기대 산출물

1. follow-up control-plane/operator path
2. updated browser/operator smoke
3. refreshed docs
4. 공식 세션이면 `SESSION_29_HANDOVER.md`와 `SESSION_30` next prompt

## 종료 조건

1. browser/operator smoke가 follow-up state/path를 관찰한다.
2. existing schedule/cancel flow가 그대로 유지된다.
3. Telegram boundary는 action-safe를 유지한다.
4. validation이 통과한다.

## 필수 validation

1. `node --check apps/assistant-web/app.js`
2. `python3 scripts/assistant/run_browser_smoke.py`
3. `.agent-orchestrator/config.json`의 validation 명령
