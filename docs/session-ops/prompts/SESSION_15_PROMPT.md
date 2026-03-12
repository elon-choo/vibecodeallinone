# SESSION_15_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S15`이며, 목적은 **projection-only runtime jobs를 executable worker foundation으로 승격하는 것**이다.

## Official Chain Note

- 이 prompt는 사용자가 `S15 -> S21` next wave를 공식 재개한 뒤 활성화한 canonical entrypoint다.
- canonical next-wave context는 `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`에 잠겨 있다.
- 이번 세션 종료 시 `S16`이 여전히 다음 세션이면 `docs/session-ops/prompts/SESSION_16_PROMPT.md`를 만들고 `NEXT_SESSION_PROMPT.md`에 mirror하라.

## Session Size Gate

- 이번 세션은 `worker foundation`만 다룬다.
- Telegram transport, quick capture, reminder delivery UI, managed quickstart는 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/README.md`
6. `docs/session-ops/01_SESSION_BOARD.md`
7. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
8. `docs/session-ops/15_EXECUTION_WAVES.md`
9. `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`
10. `docs/session-ops/handovers/SESSION_14_HANDOVER.md`
11. `services/assistant-api/README.md`
12. `services/assistant-api/assistant_api/app.py`
13. `services/assistant-api/assistant_api/store.py`
14. `services/assistant-api/assistant_api/models.py`
15. `services/assistant-api/assistant_api/config.py`
16. `services/assistant-api/migrations/0001_bootstrap.sql`
17. `tests/test_assistant_api_runtime.py`
18. `.agent-orchestrator/config.json`

## 이번 세션의 핵심 미션

1. runtime job worker foundation을 추가한다.
   - separate worker entrypoint
   - claim/lease/update lifecycle
   - queue -> running -> succeeded/failed status transition
2. purge execution을 실제로 수행할 수 있는 최소 경로를 만든다.
3. reminder job persistence foundation을 추가하되 delivery는 다음 세션으로 넘긴다.
4. targeted backend tests를 추가한다.

## 강한 제약

1. Telegram polling/webhook runtime은 이번 세션에 넣지 마라.
2. web UI는 건드리지 마라.
3. current public `S12` route shape를 함부로 바꾸지 마라.
4. KG/memory broker를 끌어오지 마라.

## 기대 산출물

1. worker runtime module / entrypoint
2. purge execution path
3. reminder job persistence skeleton
4. worker-focused tests
5. `SESSION_15_HANDOVER.md`
6. 다음 세션이 계속되면 `SESSION_16_PROMPT.md`와 `NEXT_SESSION_PROMPT.md` mirror

## 종료 조건

1. queued purge work가 실제로 실행된다.
2. runtime job 상태 전이가 DB에 남는다.
3. reminder job foundation이 persistence 수준에서 준비된다.
4. validation이 통과한다.

## 필수 validation

1. `.agent-orchestrator/config.json`의 validation 명령
2. 이번 세션이 추가한 worker/purge 관련 targeted tests
