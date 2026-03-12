# SESSION_06_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S06`이다.

반드시 먼저 읽을 문서:

1. `docs/session-ops/README.md`
2. `docs/session-ops/00_MASTER_PLAN.md`
3. `docs/session-ops/01_SESSION_BOARD.md`
4. `docs/session-ops/04_SYSTEM_ARCHITECTURE.md`
5. `docs/session-ops/05_DATA_AUTH_MEMORY_PLAN.md`
6. `docs/session-ops/06_RALPH_LOOP_TRUST_MODEL.md`
7. `docs/session-ops/07_AUTH_MEMORY_API_BOOTSTRAP.md`
8. `docs/session-ops/handovers/SESSION_05_HANDOVER.md`
9. `packages/contracts/openapi/assistant-api.openapi.yaml`
10. `packages/contracts/schemas/`
11. `packages/evidence-contracts/schemas/`
12. `services/assistant-api/README.md`

필요하면 아래 파일도 추가로 읽는다.

- `services/assistant-api/assistant_api/app.py`
- `services/assistant-api/assistant_api/models.py`
- `scripts/ralphloop/trust_bundle.py`
- `scripts/ralphloop/run.py`

이번 세션 목표:

1. `apps/assistant-web`의 첫 shell을 만든다.
2. 로그인 시작점, 대화 홈, 메모리 화면, trust info surface를 mobile-first로 구현한다.
3. `packages/contracts`와 `packages/evidence-contracts`의 payload shape를 그대로 소비한다.
4. backend가 아직 없는 auth callback/provider path는 contract-shaped adapter 또는 stub로 막되, 이미 구현된 `assistant-api` route shape는 바꾸지 않는다.

이번 세션 필수 산출물:

1. `apps/assistant-web/` 초기 스캐폴드와 핵심 화면 또는 그에 준하는 코드
2. 필요 시 `docs/session-ops/08_ASSISTANT_WEB_SHELL.md`
3. 갱신된 `docs/session-ops/01_SESSION_BOARD.md`
4. `docs/session-ops/handovers/SESSION_06_HANDOVER.md`
5. `docs/session-ops/prompts/SESSION_07_PROMPT.md`

작업 규칙:

- `assistant-web`은 `assistant-api` 계약을 바꾸지 않는다. 필요한 mock/stub도 같은 schema shape를 따른다.
- 메모리 화면에는 provenance/control surface를 남긴다.
- trust info surface는 `evidence_summary`를 읽는 전제로 설계한다.
- raw Ralph Loop artifact, absolute path, 내부 로그 텍스트를 UI에 노출하지 않는다.
- 구조를 바꿔야 하면 먼저 `docs/session-ops/01_SESSION_BOARD.md`의 `Plan Change Log`를 수정한다.
- 코드 변경을 했다면 handover에 테스트/검증 결과를 반드시 남긴다.
