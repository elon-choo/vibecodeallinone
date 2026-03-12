# SESSION_07_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S07`이다.

반드시 먼저 읽을 문서:

1. `docs/session-ops/README.md`
2. `docs/session-ops/00_MASTER_PLAN.md`
3. `docs/session-ops/01_SESSION_BOARD.md`
4. `docs/session-ops/05_DATA_AUTH_MEMORY_PLAN.md`
5. `docs/session-ops/07_AUTH_MEMORY_API_BOOTSTRAP.md`
6. `docs/session-ops/08_ASSISTANT_WEB_SHELL.md`
7. `docs/session-ops/handovers/SESSION_06_HANDOVER.md`
8. `packages/contracts/openapi/assistant-api.openapi.yaml`
9. `services/assistant-api/README.md`
10. `apps/assistant-web/README.md`

필요하면 아래 파일도 추가로 읽는다.

- `services/assistant-api/assistant_api/app.py`
- `services/assistant-api/assistant_api/store.py`
- `services/assistant-api/assistant_api/provider.py`
- `apps/assistant-web/app.js`

이번 세션 목표:

1. `memory_source` provenance를 실제 write/read surface까지 연결한다.
2. memory export/delete control surface를 runtime handler 또는 job entry로 연결한다.
3. shell IndexedDB cache와 `session_checkpoint` 간 conflict/recovery UX를 강화한다.
4. real OpenAI-compatible provider live validation 또는 그에 준하는 env/policy checklist를 남긴다.

이번 세션 필수 산출물:

1. provenance/export/delete 관련 코드 또는 문서
2. 필요 시 `docs/session-ops/09_MEMORY_PROVENANCE_AND_SYNC.md`
3. 갱신된 `docs/session-ops/01_SESSION_BOARD.md`
4. `docs/session-ops/handovers/SESSION_07_HANDOVER.md`
5. `docs/session-ops/prompts/SESSION_08_PROMPT.md`

작업 규칙:

- `assistant-web`은 계속 `assistant-api` contract shape를 우선 소비한다.
- raw Ralph Loop artifact와 내부 token 값을 UI에 노출하지 않는다.
- provider live validation이 불가능하면 왜 불가능한지와 필요한 env/policy를 문서로 명시한다.
- 계획이 바뀌면 먼저 `docs/session-ops/01_SESSION_BOARD.md`의 `Plan Change Log`를 수정한다.
- 코드 변경을 했다면 handover에 검증 명령과 결과를 반드시 남긴다.
