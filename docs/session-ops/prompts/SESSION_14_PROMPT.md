# SESSION_14_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S14`이며, 목적은 **install/Telegram smoke, validation, doc sync를 마감하는 것**이다.

## Session Size Gate

- 이번 세션은 `smoke/validation/closeout`만 다룬다.
- install/backend/web를 다시 크게 재작업하지 마라.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/README.md`
6. `docs/session-ops/01_SESSION_BOARD.md`
7. `docs/session-ops/15_EXECUTION_WAVES.md`
8. `docs/session-ops/handovers/SESSION_13_HANDOVER.md`
9. `scripts/assistant/run_operator_smoke.py`
10. `scripts/assistant/run_browser_smoke.py`
11. `tests/test_install_smoke.sh`
12. `.agent-orchestrator/config.json`

## 이번 세션의 핵심 미션

1. install smoke와 Telegram mock smoke/evidence gap을 마감한다.
2. 현재 web/browser/operator 흐름을 포함한 targeted validation을 실행하고 결과를 기록한다.
3. `.agent-orchestrator/config.json` validation을 실행한다.
4. canonical docs와 root mirrors를 최신 상태로 sync한다.
5. 다음 wave가 준비됐으면 다음 prompt를 만들고, 없으면 stop marker를 남긴다.

## 강한 제약

1. S13에서 맞춘 `assistant-web` surface를 다시 설계하지 마라.
2. S12 backend contract shape를 다시 바꾸지 마라.
3. Telegram 실제 bot/runtime 구현은 넣지 마라.
4. validation 중 narrow break가 드러날 때만 최소 수정한다.
