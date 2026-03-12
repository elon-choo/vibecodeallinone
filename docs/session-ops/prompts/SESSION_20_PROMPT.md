# SESSION_20_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S20`이며, 목적은 **thin bootstrap을 one-command self-host reference stack으로 승격하는 것**이다.

## Official Chain Note

- 이 prompt는 `S19`가 web control plane + browser smoke로 종료된 뒤 이어지는 canonical next-session prompt다.
- canonical next-wave context는 `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`에 잠겨 있다.
- 이번 세션 종료 시 `S21`가 여전히 다음 세션이면 `docs/session-ops/prompts/SESSION_21_PROMPT.md`를 만들고 `NEXT_SESSION_PROMPT.md`에 mirror하라.

## Session Size Gate

- 이번 세션은 `install/ops/docs/reference-stack packaging`만 다룬다.
- backend feature redesign이나 web surface redesign은 다시 열지 마라.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`
7. `docs/session-ops/handovers/SESSION_19_HANDOVER.md`
8. `README.md`
9. `scripts/assistant/bootstrap_runtime.sh`
10. `scripts/assistant/run_install_smoke.py`
11. `scripts/assistant/run_telegram_mock_smoke.py`
12. `tests/test_install_smoke.sh`
13. `services/assistant-api/README.md`
14. `apps/assistant-web/README.md`

## 이번 세션의 핵심 미션

1. one-command self-host reference stack start/stop path를 만든다.
2. API + worker + web + Telegram runtime pieces를 같은 operator story로 묶는다.
3. install/reference-stack smoke를 갱신한다.
4. self-host docs를 현재 구현 수준에 맞게 정리한다.

## 강한 제약

1. hosted/managed quickstart는 만들지 마라.
2. product surface redesign은 하지 마라.
3. broad infra stack(Kubernetes 등)은 넣지 마라.

## 기대 산출물

1. one-command reference stack launcher
2. reference-stack smoke path
3. refreshed self-host docs
4. `SESSION_20_HANDOVER.md`
5. 다음 세션이 계속되면 `SESSION_21_PROMPT.md`와 `NEXT_SESSION_PROMPT.md` mirror

## 종료 조건

1. reference stack이 one command로 올라간다.
2. install/reference-stack smoke가 통과한다.
3. validation이 통과한다.

## 필수 validation

1. `python3 scripts/assistant/run_install_smoke.py`
2. `bash tests/test_install_smoke.sh`
3. `.agent-orchestrator/config.json`의 validation 명령
