# SESSION_23_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S23`이며, 목적은 **managed quickstart operator/bootstrap path를 실제 artifact와 docs로 만드는 것**이다.

## Activation Note

- 이 prompt는 `S22`에서 managed quickstart deployment contract가 정의된 뒤 공식 `SESSION_23` prompt로 승격된 버전이다.
- 이번 세션은 canonical handover / next prompt / root mirror를 갱신하는 official chain session이다.

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
9. `ops/managed/README.md`
10. `ops/managed/assistant-runtime.managed.env.example`
11. `scripts/assistant/deployment_contract.py`
12. `scripts/assistant/bootstrap_runtime.sh`
13. `scripts/assistant/reference_stack.sh`
14. `scripts/assistant/run_install_smoke.py`
15. `tests/test_install_smoke.sh`
16. `services/assistant-api/README.md`
17. `apps/assistant-web/README.md`

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
4. `SESSION_23_HANDOVER.md`와 `SESSION_24` next prompt

## 종료 조건

1. operator가 later managed quickstart를 위한 artifact path를 실제로 만들 수 있다.
2. self-host reference stack path는 유지된다.
3. smoke와 validation이 통과한다.

## 필수 validation

1. `python3 scripts/assistant/run_install_smoke.py`
2. `bash tests/test_install_smoke.sh`
3. `.agent-orchestrator/config.json`의 validation 명령
