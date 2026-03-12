# Post-S27 Reminder Policy Copy-Paste Prompt Pack

## 1. How To Use This Pack

These prompts are **prepared but inactive**.

Current chain state must stay:

- `NEXT_SESSION_PROMPT.md` -> `SESSION_CHAIN_PAUSE`

Use these prompts only when the user explicitly wants to resume the post-`S27` reminder-policy wave.

Recommended sequence:

`S28 -> S29 -> S30`

If a prompt below is used in a manual session:

1. read the exact files it lists first
2. keep scope to one objective only
3. do not unpause `NEXT_SESSION_PROMPT.md` automatically unless the user explicitly promotes this wave into the official chain
4. if the user does promote it into the official chain:
   - update `docs/session-ops/01_SESSION_BOARD.md` first
   - mirror the official prompt into `NEXT_SESSION_PROMPT.md`
   - create the numbered handover
   - create the next numbered prompt
   - sync root mirrors

## 2. Copy-Paste Prompts

### Draft Prompt A: `S28 Reminder Follow-Up Policy Contract`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S28`이며, 목적은 **reminder follow-up policy를 additive-only contract/runtime slice로 harden하는 것**이다.

## Activation Note

- 이 prompt는 `S27` closeout 이후 준비된 prepared draft다.
- 사용자가 공식 재개를 지시하지 않은 이상 `NEXT_SESSION_PROMPT.md`는 건드리지 마라.
- 공식 세션으로 승격된 경우에만 canonical handover / next prompt / root mirror를 갱신하라.

## Session Size Gate

- 이번 세션은 `reminder follow-up policy contract/runtime hardening`만 다룬다.
- live provider/Telegram validation, managed quickstart 확장, KG memory broker 재설계, broad reminder planner UI redesign은 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
7. `docs/session-ops/15_EXECUTION_WAVES.md`
8. `docs/session-ops/20_POST_S27_REMINDER_POLICY_ORCHESTRATION_PLAN.md`
9. `docs/session-ops/handovers/SESSION_18_HANDOVER.md`
10. `docs/session-ops/handovers/SESSION_19_HANDOVER.md`
11. `docs/session-ops/handovers/SESSION_27_HANDOVER.md`
12. `packages/contracts/openapi/assistant-api.openapi.yaml`
13. `packages/contracts/schemas/reminders/*.json`
14. `services/assistant-api/assistant_api/models.py`
15. `services/assistant-api/assistant_api/store.py`
16. `services/assistant-api/assistant_api/app.py`
17. `services/assistant-api/assistant_api/worker.py`
18. `services/assistant-api/assistant_api/telegram_transport.py`
19. `services/assistant-api/README.md`
20. `apps/assistant-web/README.md`

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
```

### Draft Prompt B: `S29 Follow-Up Control-Plane / Operator Alignment`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S29`이며, 목적은 **reminder follow-up policy state를 web control plane, operator docs, smoke에 최소 반영하는 것**이다.

## Activation Note

- 이 prompt는 prepared draft다.
- 사용자가 post-`S27` reminder-policy wave 재개를 명시하지 않았다면 `NEXT_SESSION_PROMPT.md`는 유지하라.

## Session Size Gate

- 이번 세션은 `follow-up control-plane/operator alignment`만 다룬다.
- broad planner redesign, managed quickstart live pass, KG memory redesign은 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/20_POST_S27_REMINDER_POLICY_ORCHESTRATION_PLAN.md`
7. `docs/session-ops/handovers/SESSION_28_HANDOVER.md`
8. `apps/assistant-web/index.html`
9. `apps/assistant-web/app.js`
10. `apps/assistant-web/styles.css`
11. `apps/assistant-web/README.md`
12. `scripts/assistant/run_browser_smoke.py`
13. `scripts/assistant/run_operator_smoke.py`
14. `services/assistant-api/README.md`

## 이번 세션의 핵심 미션

1. follow-up state/actions를 web control plane에 최소 반영한다.
2. operator docs/runbook을 정리한다.
3. browser/operator smoke가 그 경로를 실제로 밟게 만든다.
4. Telegram boundary는 summary-safe를 유지한다.

## 강한 제약

1. backend contract shape를 크게 다시 바꾸지 마라.
2. reminder planner 전체 UX redesign을 이번 세션에서 열지 마라.
3. managed quickstart live validation을 이번 세션에서 다시 열지 마라.

## 기대 산출물

1. follow-up control-plane/operator path
2. updated browser/operator smoke
3. refreshed docs
4. 공식 세션이면 `SESSION_29_HANDOVER.md`와 `SESSION_30` next prompt

## 종료 조건

1. browser/operator smoke가 follow-up state/path를 관찰한다.
2. existing schedule/cancel flow가 그대로 유지된다.
3. validation이 통과한다.
```

### Draft Prompt C: `S30 Reminder Policy Closeout`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S30`이며, 목적은 **reminder-policy wave evidence, validation, doc sync, chain decision을 마감하는 것**이다.

## Session Size Gate

- 이번 세션은 `smoke/validation/closeout`만 다룬다.
- 기능 재설계나 broad bug hunt로 세션을 넓히지 마라.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/20_POST_S27_REMINDER_POLICY_ORCHESTRATION_PLAN.md`
7. `docs/session-ops/handovers/SESSION_28_HANDOVER.md`
8. `docs/session-ops/handovers/SESSION_29_HANDOVER.md`
9. `.agent-orchestrator/config.json`
10. reminder-policy smoke/validation entrypoints added in `S28` and `S29`

## 이번 세션의 핵심 미션

1. reminder-policy evidence와 validation을 마감한다.
2. canonical docs와 root mirrors를 sync한다.
3. configured validation을 실행한다.
4. 다음 wave가 준비됐으면 새 prompt를 만들고, 아니면 stop marker를 남긴다.

## 강한 제약

1. feature redesign은 하지 마라.
2. docs와 evidence가 실제 결과와 어긋나지 않게 하라.
3. blocker를 숨기지 마라.

## 기대 산출물

1. reminder-policy evidence artifact set
2. canonical closeout docs
3. root mirror sync
4. next prompt 또는 stop marker

## 종료 조건

1. all targeted artifacts are current
2. `.agent-orchestrator/config.json` validation passes
3. canonical docs and root mirrors match the real result
4. chain decision is explicit
```
