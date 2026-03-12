# SESSION_04_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S04`다.

반드시 먼저 읽을 문서:

1. `docs/session-ops/README.md`
2. `docs/session-ops/00_MASTER_PLAN.md`
3. `docs/session-ops/01_SESSION_BOARD.md`
4. `docs/session-ops/04_SYSTEM_ARCHITECTURE.md`
5. `docs/session-ops/05_DATA_AUTH_MEMORY_PLAN.md`
6. `docs/session-ops/06_RALPH_LOOP_TRUST_MODEL.md`
7. `docs/session-ops/handovers/SESSION_03_HANDOVER.md`
8. 필요하면 `/Users/elon/Documents/엘런_모바일연동/vibecodeallinone/AI피드백_v3/6_오픈소스_업그레이드_전략보고서.md`
9. 필요하면 `/Users/elon/Documents/엘런_모바일연동/vibecodeallinone/AI피드백_v3/2_Gemini_Scoring Integrity Audit.md`

필요하면 아래 파일도 추가로 읽는다.

- `scripts/ralphloop/self_review.py`
- `scripts/ralphloop/loop_runner.py`
- `scripts/ralphloop/run.py`
- `scripts/ralphloop/e2e/t3_benchmark.py`
- `kg-mcp-server/mcp_server/server.py`
- `README.md`

이번 세션 목표:

1. `S02`와 `S03`에서 고정한 auth/memory/runtime/trust contract를 실제 backend/bootstrap 수준으로 내린다.
2. `packages/contracts`와 `packages/evidence-contracts`의 최소 schema 집합을 정의한다.
3. `assistant-api`가 읽을 auth/session/memory/checkpoint/evidence read contract를 정한다.
4. 가능하면 `Ralph Loop` P0 hardening 항목 중 manual score override 제거와 artifact write skeleton까지 착수한다.

이번 세션 필수 산출물:

1. `docs/session-ops/07_AUTH_MEMORY_API_BOOTSTRAP.md`
2. 필요 시 `packages/contracts/`, `packages/evidence-contracts/`, `services/assistant-api/`, `scripts/ralphloop/` 하위 설계 문서 또는 코드 변경
3. 갱신된 `docs/session-ops/01_SESSION_BOARD.md`
4. `docs/session-ops/handovers/SESSION_04_HANDOVER.md`
5. `docs/session-ops/prompts/SESSION_05_PROMPT.md`

작업 규칙:

- 사용자 런타임 핵심 경로는 계속 `assistant-web -> assistant-api -> memory/auth store -> OpenAI adapter`를 유지한다.
- `Ralph Loop` raw artifact를 사용자 API에 직접 노출하지 말고 `evidence_summary`와 `evidence_ref`만 연결한다.
- 구조를 바꿔야 하면 먼저 `docs/session-ops/01_SESSION_BOARD.md`의 `Plan Change Log`를 수정한다.
- 코드 변경을 했다면 handover에 테스트/검증 결과를 반드시 남긴다.
- 문서만 수정했다면 handover에 그렇게 적는다.
