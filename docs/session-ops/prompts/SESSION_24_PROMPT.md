# SESSION_24_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S24`이며, 목적은 **real OIDC/provider + real Telegram operator validation foundation을 productized path로 정리하는 것**이다.

## Activation Note

- 이 prompt는 `S23`에서 managed quickstart operator/bootstrap path가 실제 artifact와 smoke로 landing된 뒤 공식 `SESSION_24` prompt로 승격된 버전이다.
- 이번 세션은 canonical handover / next prompt / root mirror를 갱신하는 official chain session이다.

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
10. `ops/managed/README.md`
11. `ops/managed/RUNBOOK.md`
12. `scripts/assistant/run_operator_smoke.py`
13. `scripts/assistant/run_telegram_mock_smoke.py` 또는 real Telegram runtime smoke entry
14. `scripts/assistant/smoke_support.py`
15. `.agent-orchestrator/config.json`
16. `artifacts/operator_smoke/assistant_api_operator_smoke.json`
17. `artifacts/install_smoke/assistant_runtime_install_smoke.json`

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
4. `SESSION_24_HANDOVER.md`와 `SESSION_25` next prompt

## 종료 조건

1. real env가 있을 때 live validation을 시도할 수 있다.
2. real env가 없을 때 blocker가 명확히 기록된다.
3. existing mock/self-host evidence path는 유지된다.
4. validation이 통과한다.

## 필수 validation

1. `.agent-orchestrator/config.json`의 validation 명령
2. 이번 세션에서 추가/갱신한 operator/live-validation targeted checks
