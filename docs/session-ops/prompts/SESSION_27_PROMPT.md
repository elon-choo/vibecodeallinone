# SESSION_27_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S27`이며, 목적은 **later-wave evidence, validation, doc sync, chain decision을 마감하는 것**이다.

## Activation Note

- 이 prompt는 `S26`에서 memory broker opt-in/control state의 web control-plane + browser smoke alignment가 landing된 뒤 공식 `SESSION_27` prompt로 승격된 버전이다.
- 이번 세션은 later-wave closeout을 위한 official chain session이며, fully scoped next objective가 없으면 stop marker로 체인을 다시 닫아야 한다.

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
