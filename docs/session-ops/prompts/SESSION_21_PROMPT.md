# SESSION_21_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S21`이며, 목적은 **next-wave release evidence, validation, doc sync, chain decision을 마감하는 것**이다.

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
7. `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`
8. `docs/session-ops/handovers/SESSION_20_HANDOVER.md`
9. `.agent-orchestrator/config.json`
10. `scripts/assistant/run_install_smoke.py`
11. `scripts/assistant/run_telegram_mock_smoke.py` 또는 real Telegram runtime smoke entry
12. `scripts/assistant/run_operator_smoke.py`
13. `scripts/assistant/run_browser_smoke.py`

## 이번 세션의 핵심 미션

1. install/reference-stack smoke를 마감한다.
2. Telegram runtime smoke를 마감한다.
3. operator/browser smoke와 configured validation을 실행한다.
4. canonical docs와 root mirrors를 sync한다.
5. 다음 wave가 준비됐으면 새 prompt를 만들고, 아니면 stop marker를 남긴다.

## 강한 제약

1. feature redesign은 하지 마라.
2. narrow fix가 필요한 경우만 최소 수정하라.
3. docs와 evidence가 실제 결과와 어긋나지 않게 하라.

## 기대 산출물

1. full evidence artifact set
2. canonical closeout docs
3. root mirror sync
4. next prompt 또는 stop marker

## 종료 조건

1. all targeted smoke artifacts are current
2. `.agent-orchestrator/config.json` validation passes
3. canonical docs and root mirrors match the real result
4. chain decision is explicit
