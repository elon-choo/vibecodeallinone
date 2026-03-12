# SESSION_YY_PROMPT Template

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `SYY`다.

반드시 먼저 읽을 문서:

1. `docs/session-ops/README.md`
2. `docs/session-ops/00_MASTER_PLAN.md`
3. `docs/session-ops/01_SESSION_BOARD.md`
4. 직전 handover 문서
5. 이번 세션에 직접 관련된 산출물 문서

이번 세션 목표:

1. 목표 1
2. 목표 2
3. 목표 3

Session Size Gate:

- 이 세션은 하나의 main objective만 가진다.
- install / backend / web / smoke 중 2개 이상을 동시에 크게 건드리면 다음 prompt로 분해한다.
- unattended chain에서 멈추지 않게, 이번 세션에서 실제로 끝낼 수 있는 범위만 남긴다.

이번 세션 필수 산출물:

1. 문서 또는 코드 산출물
2. `docs/session-ops/handovers/SESSION_YY_HANDOVER.md`
3. `docs/session-ops/prompts/SESSION_ZZ_PROMPT.md`

작업 규칙:

- 계획이 바뀌면 먼저 `docs/session-ops/01_SESSION_BOARD.md`의 `Plan Change Log`를 수정한다.
- 세션 종료 전 handover와 다음 세션 prompt를 반드시 남긴다.
- 검증을 실행했다면 결과를 handover에 남긴다.
- 검증을 못 했다면 이유를 handover에 남긴다.
- 다음 prompt는 남은 작업을 더 작은 `micro-session` objective로 넘긴다.
