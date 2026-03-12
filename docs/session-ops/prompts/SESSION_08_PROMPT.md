# SESSION_08_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S08`이다.

반드시 먼저 읽을 문서:

1. `docs/session-ops/README.md`
2. `docs/session-ops/00_MASTER_PLAN.md`
3. `docs/session-ops/01_SESSION_BOARD.md`
4. `docs/session-ops/08_ASSISTANT_WEB_SHELL.md`
5. `docs/session-ops/09_MEMORY_PROVENANCE_AND_SYNC.md`
6. `docs/session-ops/handovers/SESSION_07_HANDOVER.md`
7. `packages/contracts/openapi/assistant-api.openapi.yaml`
8. `services/assistant-api/README.md`
9. `apps/assistant-web/README.md`

필요하면 아래 파일도 추가로 읽는다.

- `services/assistant-api/assistant_api/app.py`
- `services/assistant-api/assistant_api/store.py`
- `apps/assistant-web/app.js`
- `tests/test_assistant_api_runtime.py`

이번 세션 목표:

1. real OpenAI-compatible provider live validation 또는 최소 repeatable operator smoke를 실제 결과와 함께 남긴다.
2. `assistant-web` browser E2E 또는 그에 준하는 repeatable smoke를 추가한다.
3. stale trust fallback copy와 release evidence polish를 마무리한다.
4. 필요하면 export retention/purge worker를 bootstrap queue에서 한 단계 더 구체화한다.

이번 세션 필수 산출물:

1. live validation 또는 smoke 관련 코드/스크립트/문서
2. browser E2E 또는 smoke evidence
3. 갱신된 `docs/session-ops/01_SESSION_BOARD.md`
4. `docs/session-ops/handovers/SESSION_08_HANDOVER.md`
5. `docs/session-ops/prompts/SESSION_09_PROMPT.md`

작업 규칙:

- live provider 검증이 불가능하면 정확히 어떤 env/policy가 없어 막혔는지와 어떤 수동 검증이 대신 수행됐는지 남긴다.
- shell 테스트는 auth round trip, memory export/delete, checkpoint conflict UX 중 최소 하나 이상의 실제 사용자 흐름을 덮어야 한다.
- raw Ralph Loop artifact나 internal export artifact path는 사용자 표면에 노출하지 않는다.
- 계획이 바뀌면 먼저 `docs/session-ops/01_SESSION_BOARD.md`의 `Plan Change Log`를 수정한다.
- 코드 변경을 했다면 handover에 검증 명령과 결과를 반드시 남긴다.
