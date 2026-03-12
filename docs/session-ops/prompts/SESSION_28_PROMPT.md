# SESSION_28_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S28`이며, 목적은 **reminder follow-up policy를 additive-only contract/runtime slice로 harden하는 것**이다.

## Activation Note

- 이 prompt는 `S27` closeout 이후 원래 제품 목표와 deferred backlog를 다시 검토해 준비한 prepared next prompt다.
- 사용자가 공식 재개를 지시하기 전까지 `NEXT_SESSION_PROMPT.md`는 `SESSION_CHAIN_PAUSE`를 유지한다.
- 공식 세션으로 승격된 경우에만 canonical handover / next prompt / root mirror를 갱신하라.

## Why This Objective Now

- 원래 제품 목표에는 reminders / scheduled nudges / auditable jobs / cross-surface assistant convenience가 포함돼 있다.
- managed quickstart live pass evidence는 여전히 외부 managed OIDC/Telegram env 의존성이 크다.
- 반면 reminder follow-up hardening은 현재 저장소 안에서 바로 전진 가능하고, 사용자 가치에 직접 닿는 다음 좁은 objective다.

## Session Size Gate

- 이번 세션은 `reminder follow-up policy contract/runtime hardening`만 다룬다.
- live provider/Telegram validation, managed quickstart 확장, KG memory broker 재설계, broad reminder planner UI redesign은 다음 세션으로 넘긴다.
- recurring reminder 전체 productization을 한 번에 다 열지 말고, additive follow-up policy와 auditable execution seam부터 고정한다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
7. `docs/session-ops/15_EXECUTION_WAVES.md`
8. `docs/session-ops/20_POST_S27_REMINDER_POLICY_ORCHESTRATION_PLAN.md`
9. `docs/session-ops/21_POST_S27_REMINDER_POLICY_PROMPT_PACK.md`
10. `docs/session-ops/handovers/SESSION_18_HANDOVER.md`
11. `docs/session-ops/handovers/SESSION_19_HANDOVER.md`
12. `docs/session-ops/handovers/SESSION_27_HANDOVER.md`
13. `packages/contracts/openapi/assistant-api.openapi.yaml`
14. `packages/contracts/schemas/reminders/reminder-create-request.schema.json`
15. `packages/contracts/schemas/reminders/reminder-record.schema.json`
16. `packages/contracts/schemas/reminders/reminder-list-response.schema.json`
17. `services/assistant-api/assistant_api/models.py`
18. `services/assistant-api/assistant_api/store.py`
19. `services/assistant-api/assistant_api/app.py`
20. `services/assistant-api/assistant_api/worker.py`
21. `services/assistant-api/assistant_api/telegram_transport.py`
22. `services/assistant-api/README.md`
23. `apps/assistant-web/README.md`

## 이번 세션의 핵심 미션

1. reminder follow-up policy를 additive contract/state로 정의한다.
2. snooze/reschedule/retry/dead-letter-ready execution seam을 기존 reminder lifecycle 위에 얇게 올린다.
3. current schedule/cancel flow를 깨지 않고 audit/runtime visibility를 유지한다.
4. targeted backend tests와 최소 docs를 추가한다.

## 강한 제약

1. managed quickstart/live validation을 이번 세션에서 다시 열지 마라.
2. KG memory broker나 workspace memory scope를 이번 세션에 끌어오지 마라.
3. Telegram을 full reminder admin surface로 만들지 마라.
4. reminder planner 전체 UX redesign으로 세션을 넓히지 마라.
5. 실패/재시도/보류 상태를 숨기지 말고 auditable path로 남겨라.

## 기대 산출물

1. additive reminder follow-up contract/state shape
2. backend/runtime/worker changes
3. reminder follow-up focused tests
4. 공식 세션이면 `SESSION_28_HANDOVER.md`와 `SESSION_29` next prompt

## 종료 조건

1. 기존 one-shot reminder schedule/cancel path가 그대로 유지된다.
2. follow-up state가 explicit하고 auditable하다.
3. Telegram boundary는 action-safe를 유지한다.
4. validation이 통과한다.

## 필수 validation

1. `.agent-orchestrator/config.json`의 validation 명령
2. targeted reminder follow-up lifecycle pytest
3. web file을 건드렸다면 `node --check apps/assistant-web/app.js`
