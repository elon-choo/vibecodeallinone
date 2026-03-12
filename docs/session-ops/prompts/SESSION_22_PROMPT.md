# SESSION_22_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S22`이며, 목적은 **managed quickstart deployment contract를 self-host reference stack 위에 정의하는 것**이다.

## Activation Note

- 이 prompt는 `S21` closeout 이후 pause 상태에서 준비된 Draft Prompt A를 공식 `SESSION_22` prompt로 승격한 버전이다.
- 이번 세션은 canonical handover / next prompt / root mirror를 갱신하는 official chain session이다.

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
4. `SESSION_22_HANDOVER.md`와 `SESSION_23` next prompt

## 종료 조건

1. managed quickstart에 필요한 env/secret/input surface가 명시된다.
2. self-host와 managed quickstart 경계가 문서와 runtime에서 명확해진다.
3. self-host path는 그대로 유지된다.
4. validation이 통과한다.

## 필수 validation

1. `.agent-orchestrator/config.json`의 validation 명령
2. 이번 세션이 추가한 operator/install targeted checks
