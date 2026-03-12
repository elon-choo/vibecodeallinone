# Session Ops

이 폴더는 `vibecodeallinone`을 100점짜리 오픈소스로 끌고 가기 위한 세션 운영 허브다.

## 읽는 순서

1. `00_MASTER_PLAN.md`
2. `01_SESSION_BOARD.md`
3. `handovers/SESSION_00_HANDOVER.md` 또는 가장 최신 handover
4. `prompts/SESSION_01_PROMPT.md` 또는 가장 최신 prompt

## 운영 원칙

- 세션 시작 전에는 위 4개 문서를 먼저 읽는다.
- 세션 중 계획이 바뀌면 `01_SESSION_BOARD.md`의 `Plan Change Log`를 먼저 갱신한다.
- 세션 종료 전에는 handover 문서를 반드시 남긴다.
- 더 이어갈 세션이 없으면 루트 `NEXT_SESSION_PROMPT.md`에 stop marker 한 줄만 남긴다.
- 다음 세션이 실제로 필요할 때만 다음 세션 prompt를 만든다.
- 코드 작업을 했으면 검증 결과를 handover에 남긴다.
- 문서 작업만 했으면 그 사실을 handover에 명시한다.

## Unattended Mode

- unattended chain은 `micro-session` 기준으로 쪼갠다.
- 한 세션은 `하나의 main objective`만 가진다.
- 한 세션이 동시에 install + API + web + smoke를 모두 다루면 범위가 너무 넓다고 보고 다음 prompt를 먼저 분해한다.
- 권장 범위는 아래 중 하나다.
  - install/docs/bootstrap
  - contracts + backend foundation
  - web surface
  - smoke/tests/validation
- watchdog는 stalled worker를 재시작할 수 있지만, prompt 자체가 과도하게 넓으면 반복 정지될 수 있으므로 prompt 분해가 우선이다.

## 정본 문서

- 마스터 플랜: `00_MASTER_PLAN.md`
- 현재 상태판: `01_SESSION_BOARD.md`
- 템플릿: `templates/`
- 세션별 인수인계: `handovers/`
- 세션별 시작 프롬프트: `prompts/`

## 주의

- 저장소 루트의 기존 `NEXT-SESSION-PROMPT.md`는 Round 2 시점의 이력 문서다.
- 이번부터의 정본 세션 운영 문서는 `docs/session-ops/` 아래 파일들이다.
