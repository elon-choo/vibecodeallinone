# SESSION_09_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S09`다.

먼저 읽을 문서:

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/README.md`
6. `docs/session-ops/00_MASTER_PLAN.md`
7. `docs/session-ops/01_SESSION_BOARD.md`
8. `docs/session-ops/08_ASSISTANT_WEB_SHELL.md`
9. `docs/session-ops/09_MEMORY_PROVENANCE_AND_SYNC.md`
10. `docs/session-ops/handovers/SESSION_08_HANDOVER.md`
11. `docs/session-ops/prompts/SESSION_09_PROMPT.md`
12. `services/assistant-api/README.md`
13. `apps/assistant-web/README.md`
14. `artifacts/operator_smoke/assistant_api_operator_smoke.json`
15. `artifacts/browser_smoke/assistant_web_browser_smoke.json`

필요하면 아래 파일도 추가로 읽는다.

- `scripts/assistant/run_operator_smoke.py`
- `scripts/assistant/run_browser_smoke.py`
- `services/assistant-api/assistant_api/trust.py`
- `apps/assistant-web/app.js`
- `tests/test_assistant_api_runtime.py`

이번 세션 목표:

1. real OpenAI-compatible provider credential과 callback origin이 준비됐으면 실제 live validation을 수행하고 결과를 남긴다.
2. live validation이 여전히 외부 env/policy 때문에 막히면 mock smoke를 다시 만드는 대신 `SESSION_CHAIN_PAUSE` 또는 `NO_FURTHER_SESSION` 여부를 판단한다.
3. 추가 제품 하드닝이 필요하면 export retention/purge worker를 bootstrap queue에서 실제 worker로 승격한다.

이번 세션 필수 산출물:

1. live validation evidence 또는 stop-marker 결정
2. 갱신된 `docs/session-ops/01_SESSION_BOARD.md`
3. `docs/session-ops/handovers/SESSION_09_HANDOVER.md` 또는 stop marker에 준하는 종료 기록
4. 필요 시 `docs/session-ops/prompts/SESSION_10_PROMPT.md`
5. 갱신된 루트 `HANDOVER.md`
6. 갱신된 루트 `NEXT_SESSION_PROMPT.md`

작업 규칙:

- real provider 검증을 시도할 때는 현재 env에 실제로 있는 값만 사용하고, secret value 자체는 handover에 기록하지 않는다.
- live validation이 막히면 어떤 env/policy가 남았는지와 이번 세션이 왜 stop 또는 pause로 가는지 명확히 남긴다.
- raw Ralph Loop artifact path나 internal export artifact path를 사용자 표면에 노출하지 않는다.
- 계획이 바뀌면 먼저 `docs/session-ops/01_SESSION_BOARD.md`의 `Plan Change Log`를 수정한다.
- 코드 변경을 했다면 handover에 검증 명령과 결과를 반드시 남긴다.
- 더 이어갈 필요가 없으면 `NEXT_SESSION_PROMPT.md`에 `SESSION_CHAIN_PAUSE`, `NO_FURTHER_SESSION`, 또는 `ORCHESTRATOR_STOP` 중 하나를 남긴다.
