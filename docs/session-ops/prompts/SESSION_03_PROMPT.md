# SESSION_03_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S03`다.

반드시 먼저 읽을 문서:

1. `docs/session-ops/README.md`
2. `docs/session-ops/00_MASTER_PLAN.md`
3. `docs/session-ops/01_SESSION_BOARD.md`
4. `docs/session-ops/04_SYSTEM_ARCHITECTURE.md`
5. `docs/session-ops/05_DATA_AUTH_MEMORY_PLAN.md`
6. `docs/session-ops/handovers/SESSION_02_HANDOVER.md`
7. `/Users/elon/Documents/엘런_모바일연동/vibecodeallinone/AI피드백_v3/6_오픈소스_업그레이드_전략보고서.md`
8. 필요하면 `/Users/elon/Documents/엘런_모바일연동/vibecodeallinone/AI피드백_v3/2_Gemini_Scoring Integrity Audit.md`

필요하면 아래 파일도 추가로 읽는다.

- `scripts/ralphloop/loop_runner.py`
- `scripts/ralphloop/run.py`
- `scripts/ralphloop/self_review.py`
- `scripts/ralphloop/e2e/t3_benchmark.py`
- `kg-mcp-server/mcp_server/server.py`

이번 세션 목표:

1. `Ralph Loop`를 사용자 앱과 연결 가능한 `evidence-based trust plane`으로 재정의한다.
2. artifact metadata, manifest/history, score integrity, stage status를 어떤 계약으로 고정할지 정한다.
3. `assistant-api`와 사용자 UI가 읽을 수 있는 evidence summary schema를 만든다.
4. S04의 auth/memory backend가 바로 사용할 수 있는 contract와 우선순위를 남긴다.

이번 세션 필수 산출물:

1. `docs/session-ops/06_RALPH_LOOP_TRUST_MODEL.md`
2. 필요 시 `scripts/ralphloop/` 하위 설계 문서 또는 코드 변경
3. 갱신된 `docs/session-ops/01_SESSION_BOARD.md`
4. `docs/session-ops/handovers/SESSION_03_HANDOVER.md`
5. `docs/session-ops/prompts/SESSION_04_PROMPT.md`

작업 규칙:

- 이번 세션은 `S02`의 사용자 런타임 경계를 깨면 안 된다.
- `Ralph Loop`는 사용자 요청 처리 경로가 아니라 release evidence와 trust plane 역할에 집중한다.
- 제품 구조를 바꿔야 하면 먼저 `docs/session-ops/01_SESSION_BOARD.md`의 `Plan Change Log`를 수정한다.
- 문서만 수정했다면 handover에 그렇게 적고, 코드나 테스트를 수행했다면 결과를 반드시 남긴다.
