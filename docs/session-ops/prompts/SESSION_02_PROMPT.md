# SESSION_02_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S02`다.

반드시 먼저 읽을 문서:

1. `docs/session-ops/README.md`
2. `docs/session-ops/00_MASTER_PLAN.md`
3. `docs/session-ops/01_SESSION_BOARD.md`
4. `docs/session-ops/02_PRODUCT_BRIEF.md`
5. `docs/session-ops/03_WIN_RUBRIC.md`
6. `docs/session-ops/handovers/SESSION_01_HANDOVER.md`
7. `/Users/elon/Documents/엘런_모바일연동/vibecodeallinone/AI피드백_v3/1_GPT_Architecture Review.md`
8. `/Users/elon/Documents/엘런_모바일연동/vibecodeallinone/AI피드백_v3/6_오픈소스_업그레이드_전략보고서.md`

필요하면 아래 문서도 추가로 읽는다.

- `/Users/elon/Documents/엘런_모바일연동/vibecodeallinone/AI피드백_v3/2_Gemini_Scoring Integrity Audit.md`
- `/Users/elon/Documents/엘런_모바일연동/vibecodeallinone/AI피드백_v3/4_Gemini_Testing Strategy Review.md`
- `/Users/elon/Documents/elon_opensource/claude-code-power-pack/README.md`
- `kg-mcp-server/mcp_server/server.py`
- `scripts/ralphloop/loop_runner.py`

이번 세션 목표:

1. `S01 Product Brief`를 깨지 않는 시스템 아키텍처를 고정한다.
2. 앱 표면, API, 메모리 저장소, KG MCP, `Ralph Loop`의 책임 경계를 문서화한다.
3. `GPT OAuth(OpenAI-first)`의 인증 구조와 메모리 데이터 흐름 초안을 제안한다.
4. 현재 저장소 안에서 어떤 패키지 구조로 확장할지 정한다.
5. S03 이후 구현 세션이 바로 착수할 수 있게 워크스트림 기준을 만든다.

이번 세션 필수 산출물:

1. `docs/session-ops/04_SYSTEM_ARCHITECTURE.md`
2. `docs/session-ops/05_DATA_AUTH_MEMORY_PLAN.md`
3. 갱신된 `docs/session-ops/01_SESSION_BOARD.md`
4. `docs/session-ops/handovers/SESSION_02_HANDOVER.md`
5. `docs/session-ops/prompts/SESSION_03_PROMPT.md`

작업 규칙:

- 이번 세션은 아키텍처 정의 세션이다. 큰 코드 구현은 하지 않는다.
- 제품 정의를 뒤집는 변경이 필요하면 먼저 `docs/session-ops/01_SESSION_BOARD.md`의 `Plan Change Log`를 수정한다.
- 인증, 메모리, 패키지 구조는 비개발자 온보딩과 크로스디바이스 UX를 우선 기준으로 판단한다.
- `Ralph Loop`는 사용자 기능이 아니라 품질 엔진이라는 전제를 유지한다.
- 세션 종료 전 handover와 다음 세션 prompt를 반드시 남긴다.
