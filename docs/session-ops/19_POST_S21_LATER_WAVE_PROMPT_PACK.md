# Post-S21 Later-Wave Copy-Paste Prompt Pack

## 1. How To Use This Pack

These prompts are **prepared but inactive**.

Current chain state must stay:

- `NEXT_SESSION_PROMPT.md` -> `SESSION_CHAIN_PAUSE`

Use these prompts only when the user explicitly wants to resume the later wave.

Recommended later-wave sequence:

`S22 -> S23 -> S24 -> S25 -> S26 -> S27`

If a prompt below is used in a manual session:

1. read the exact files it lists first
2. keep scope to one objective only
3. do not unpause `NEXT_SESSION_PROMPT.md` automatically unless the user explicitly promotes this later wave into the official chain
4. if the user does promote it into the official chain:
   - update `docs/session-ops/01_SESSION_BOARD.md` first
   - create the numbered handover
   - create the next numbered prompt
   - sync root mirrors

## 2. Copy-Paste Prompts

### Draft Prompt A: `S22 Managed Quickstart Deployment Contract`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S22`이며, 목적은 **managed quickstart deployment contract를 self-host reference stack 위에 정의하는 것**이다.

## Activation Note

- 이 prompt는 `S21` closeout 이후 pause 상태에서 준비된 draft다.
- 사용자가 later wave를 공식 재개한다고 명시하지 않은 이상 `NEXT_SESSION_PROMPT.md`는 건드리지 마라.
- 공식 세션으로 승격된 경우에만 canonical handover / next prompt / root mirror를 갱신하라.

## Session Size Gate

- 이번 세션은 `managed quickstart deployment contract`만 다룬다.
- 실제 hosted rollout, live provider validation, KG memory broker, reminder follow-up policy는 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/13_PRODUCT_REPLAN_MASTER.md`
7. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
8. `docs/session-ops/15_EXECUTION_WAVES.md`
9. `docs/session-ops/18_POST_S21_LATER_WAVE_ORCHESTRATION_PLAN.md`
10. `docs/session-ops/handovers/SESSION_21_HANDOVER.md`
11. `README.md`
12. `scripts/assistant/bootstrap_runtime.sh`
13. `scripts/assistant/reference_stack.sh`
14. `scripts/assistant/run_operator_smoke.py`
15. `services/assistant-api/README.md`
16. `apps/assistant-web/README.md`

## 이번 세션의 핵심 미션

1. managed quickstart env/secret contract를 정의한다.
2. self-host와 managed quickstart operator mode의 경계를 문서와 runtime surface에 반영한다.
3. hosted-ready status/readiness surface가 필요하면 additive-only로 추가한다.
4. operator-facing docs/template를 추가한다.

## 강한 제약

1. second runtime/backend path를 만들지 마라.
2. self-host reference stack을 깨지 마라.
3. web onboarding UX를 크게 열지 마라.
4. KG memory broker를 이번 세션에서 설계하지 마라.

## 기대 산출물

1. managed quickstart env/secret contract
2. operator mode/readiness contract
3. targeted docs/templates
4. 공식 세션이면 `SESSION_22_HANDOVER.md`와 `SESSION_23` next prompt

## 종료 조건

1. managed quickstart에 필요한 env/secret/input surface가 명시된다.
2. self-host와 managed quickstart 경계가 문서와 runtime에서 명확해진다.
3. self-host path는 그대로 유지된다.
4. validation이 통과한다.

## 필수 validation

1. `.agent-orchestrator/config.json`의 validation 명령
2. 이번 세션이 추가한 operator/install targeted checks
```

### Draft Prompt B: `S23 Managed Quickstart Operator / Bootstrap Path`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S23`이며, 목적은 **managed quickstart operator/bootstrap path를 실제 artifact와 docs로 만드는 것**이다.

## Activation Note

- 이 prompt는 prepared draft다.
- 사용자가 later wave 재개를 명시하지 않았다면 `NEXT_SESSION_PROMPT.md`는 유지하라.

## Session Size Gate

- 이번 세션은 `managed quickstart operator/bootstrap path`만 다룬다.
- live OIDC validation, KG memory broker, web redesign은 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/18_POST_S21_LATER_WAVE_ORCHESTRATION_PLAN.md`
7. `docs/session-ops/handovers/SESSION_22_HANDOVER.md`
8. `README.md`
9. `scripts/assistant/bootstrap_runtime.sh`
10. `scripts/assistant/reference_stack.sh`
11. `scripts/assistant/run_install_smoke.py`
12. `tests/test_install_smoke.sh`
13. `services/assistant-api/README.md`
14. `apps/assistant-web/README.md`

## 이번 세션의 핵심 미션

1. managed quickstart bootstrap/operator path를 artifact 수준으로 만든다.
2. generated env/template/command surface를 정리한다.
3. install/reference-stack smoke를 이 path까지 반영한다.
4. operator docs/runbook을 정리한다.

## 강한 제약

1. runtime product surface를 다시 설계하지 마라.
2. live OIDC/Telegram validation은 이번 세션에서 완료하려고 무리하지 마라.
3. KG memory broker는 이번 세션에서 열지 마라.

## 기대 산출물

1. managed quickstart bootstrap/operator path
2. updated install/reference-stack smoke
3. refreshed operator docs
4. 공식 세션이면 `SESSION_23_HANDOVER.md`와 `SESSION_24` next prompt

## 종료 조건

1. operator가 later managed quickstart를 위한 artifact path를 실제로 만들 수 있다.
2. self-host reference stack path는 유지된다.
3. smoke와 validation이 통과한다.
```

### Draft Prompt C: `S24 Live Provider + Real Telegram Operator Validation`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S24`이며, 목적은 **real OIDC/provider + real Telegram operator validation foundation을 productized path로 정리하는 것**이다.

## Session Size Gate

- 이번 세션은 `live operator validation foundation`만 다룬다.
- managed quickstart UX, KG memory broker, reminder follow-up policy는 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/18_POST_S21_LATER_WAVE_ORCHESTRATION_PLAN.md`
7. `docs/session-ops/handovers/SESSION_22_HANDOVER.md`
8. `docs/session-ops/handovers/SESSION_23_HANDOVER.md`
9. `services/assistant-api/README.md`
10. `scripts/assistant/run_operator_smoke.py`
11. `scripts/assistant/run_telegram_mock_smoke.py` 또는 real Telegram runtime smoke entry
12. `scripts/assistant/smoke_support.py`
13. `.agent-orchestrator/config.json`
14. `artifacts/operator_smoke/assistant_api_operator_smoke.json`

## 이번 세션의 핵심 미션

1. real provider validation path를 productized한다.
2. real Telegram operator validation path를 정리한다.
3. env preflight와 blocker artifact를 더 명확하게 만든다.
4. real env가 있으면 실제 validation을, 없으면 explicit blocker result를 남긴다.

## 강한 제약

1. env가 없는데 fake success를 기록하지 마라.
2. broad product redesign으로 세션을 넓히지 마라.
3. KG memory broker를 이번 세션에서 열지 마라.

## 기대 산출물

1. real operator validation path
2. explicit blocker/report path
3. targeted tests/docs
4. 공식 세션이면 `SESSION_24_HANDOVER.md`와 `SESSION_25` next prompt

## 종료 조건

1. real env가 있을 때 live validation을 시도할 수 있다.
2. real env가 없을 때 blocker가 명확히 기록된다.
3. existing mock/self-host evidence path는 유지된다.
4. validation이 통과한다.
```

### Draft Prompt D: `S25 KG Memory Broker Foundation`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S25`이며, 목적은 **KG-backed workspace/project memory broker foundation을 `assistant-api` 안에 추가하는 것**이다.

## Session Size Gate

- 이번 세션은 `memory broker foundation`만 다룬다.
- web opt-in UI, managed quickstart UX, Telegram broad memory surface는 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/13_PRODUCT_REPLAN_MASTER.md`
7. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
8. `docs/session-ops/15_EXECUTION_WAVES.md`
9. `docs/session-ops/18_POST_S21_LATER_WAVE_ORCHESTRATION_PLAN.md`
10. `docs/session-ops/handovers/SESSION_21_HANDOVER.md`
11. `kg-mcp-server/API.md`
12. `packages/contracts/openapi/assistant-api.openapi.yaml`
13. `services/assistant-api/assistant_api/models.py`
14. `services/assistant-api/assistant_api/store.py`
15. `services/assistant-api/assistant_api/app.py`

## 이번 세션의 핵심 미션

1. opt-in workspace/project memory broker foundation을 추가한다.
2. workspace-scoped retrieval boundary와 consent/audit shape를 추가한다.
3. additive API/contract path를 추가한다.
4. backend tests를 추가한다.

## 강한 제약

1. KG를 always-on mandatory path로 만들지 마라.
2. Telegram에 raw KG retrieval을 노출하지 마라.
3. broad web UI는 이번 세션에서 열지 마라.
4. team/shared memory를 끌어오지 마라.

## 기대 산출물

1. broker module/foundation
2. additive contract/API path
3. broker-focused backend tests
4. 공식 세션이면 `SESSION_25_HANDOVER.md`와 `SESSION_26` next prompt

## 종료 조건

1. backend가 workspace/project memory opt-in state를 표현하고 broker할 수 있다.
2. current explicit/continuity memory behavior가 깨지지 않는다.
3. validation이 통과한다.
```

### Draft Prompt E: `S26 Broker Opt-In + Control-Plane Alignment`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S26`이며, 목적은 **memory broker opt-in/control state를 web control plane과 smoke에 반영하는 것**이다.

## Session Size Gate

- 이번 세션은 `web control plane + smoke alignment`만 다룬다.
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
4. docs를 최소 갱신한다.

## 강한 제약

1. backend shape를 크게 다시 바꾸지 마라.
2. Telegram이 full memory admin UI처럼 동작하게 만들지 마라.
3. managed quickstart infra를 이번 세션에서 다시 열지 마라.

## 기대 산출물

1. web control-plane alignment for broker opt-in
2. browser smoke alignment
3. 최소 docs refresh
4. 공식 세션이면 `SESSION_26_HANDOVER.md`와 `SESSION_27` next prompt

## 종료 조건

1. browser smoke가 broker opt-in/control path를 실제로 밟는다.
2. existing reminder/continuity/runtime shell behavior가 유지된다.
3. validation이 통과한다.
```

### Draft Prompt F: `S27 Later-Wave Closeout`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S27`이며, 목적은 **later-wave evidence, validation, doc sync, chain decision을 마감하는 것**이다.

## Session Size Gate

- 이번 세션은 `smoke/validation/closeout`만 다룬다.
- 기능 재설계나 broad bug hunt로 세션을 넓히지 마라.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/15_EXECUTION_WAVES.md`
7. `docs/session-ops/18_POST_S21_LATER_WAVE_ORCHESTRATION_PLAN.md`
8. `docs/session-ops/handovers/SESSION_22_HANDOVER.md`
9. `docs/session-ops/handovers/SESSION_23_HANDOVER.md`
10. `docs/session-ops/handovers/SESSION_24_HANDOVER.md`
11. `docs/session-ops/handovers/SESSION_25_HANDOVER.md`
12. `docs/session-ops/handovers/SESSION_26_HANDOVER.md`
13. `.agent-orchestrator/config.json`
14. later-wave smoke/validation entrypoints added in `S22`~`S26`

## 이번 세션의 핵심 미션

1. later-wave install/managed/operator/browser/broker evidence를 마감한다.
2. real env가 있으면 live validation evidence를 남기고, 없으면 explicit blocker artifact를 남긴다.
3. configured validation을 실행한다.
4. canonical docs와 root mirrors를 sync한다.
5. 다음 wave가 준비됐으면 새 prompt를 만들고, 아니면 stop marker를 남긴다.

## 강한 제약

1. feature redesign은 하지 마라.
2. docs와 evidence가 실제 결과와 어긋나지 않게 하라.
3. blocker를 숨기지 마라.

## 기대 산출물

1. full later-wave evidence artifact set
2. canonical closeout docs
3. root mirror sync
4. next prompt 또는 stop marker

## 종료 조건

1. all targeted smoke artifacts are current
2. `.agent-orchestrator/config.json` validation passes
3. canonical docs and root mirrors match the real result
4. chain decision is explicit
```

