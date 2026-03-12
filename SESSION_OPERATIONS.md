# Session Operations

이 파일은 `agent-orchestrator`의 작업 규칙 미러다.
세션 정본 운영 문서는 `docs/session-ops/README.md` 아래 체계를 따른다.

## Session Start

1. `git status --short`로 dirty tree를 확인한다.
2. 아래 루트 미러를 읽는다.
   - `PROJECT_AUDIT.md`
   - `MASTER_PLAN.md`
   - `HANDOVER.md`
   - `NEXT_SESSION_PROMPT.md`
3. 이어서 canonical 문서를 읽는다.
   - `docs/session-ops/README.md`
   - `docs/session-ops/00_MASTER_PLAN.md`
   - `docs/session-ops/01_SESSION_BOARD.md`
   - 최신 `docs/session-ops/handovers/SESSION_XX_HANDOVER.md`
   - 최신 `docs/session-ops/prompts/SESSION_XX_PROMPT.md`
4. 세션 범위를 하나의 main objective로 잠근다.
5. unattended run이면 범위를 `micro-session` 크기로 잘랐는지 확인한다.
   - install/docs/bootstrap
   - contracts/backend
   - web surface
   - smoke/validation
   위 4개를 한 세션에 모두 넣지 않는다.

## Session End

1. 변경사항과 남은 리스크를 정리한다.
2. `.agent-orchestrator/config.json`의 validation 명령을 실행한다.
3. canonical 문서를 먼저 갱신한다.
   - `docs/session-ops/01_SESSION_BOARD.md`
   - 최신 handover 문서
   - 다음 prompt 문서
4. 루트 미러를 canonical 상태와 동기화한다.
   - `HANDOVER.md`
   - `NEXT_SESSION_PROMPT.md`
   - 필요 시 `PROJECT_AUDIT.md`, `MASTER_PLAN.md`
5. 더 이어갈 세션이 없으면 `NEXT_SESSION_PROMPT.md`에 stop marker를 남긴다.

## Unattended Rule

- 사용자가 장시간 자리를 비우는 스타일이면, 세션은 항상 작게 나눈다.
- watchdog는 stalled orchestrator를 재시작할 수 있지만, 넓은 prompt를 자동으로 잘라 주지는 못한다.
- 따라서 다음 prompt를 쓸 때는 항상 `이번 세션에서 끝낼 수 있는 하나의 objective`만 남긴다.

## Mirror Mapping

- `PROJECT_AUDIT.md` -> 현재 상태판 + 주요 출시 리스크 압축본
- `MASTER_PLAN.md` -> 잔여 세션 체인과 stop rule 압축본
- `HANDOVER.md` -> 최신 canonical handover 미러
- `NEXT_SESSION_PROMPT.md` -> 최신 canonical prompt 미러
