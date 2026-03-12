# SESSION_18_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S18`이며, 목적은 **reminder scheduling/delivery를 background worker + Telegram transport 위에 올리는 것**이다.

## Official Chain Note

- 이 prompt는 `S17`이 Telegram quick capture + resume backend로 종료된 뒤 이어지는 canonical next-session prompt다.
- canonical next-wave context는 `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`에 잠겨 있다.
- 이번 세션 종료 시 `S19`가 여전히 다음 세션이면 `docs/session-ops/prompts/SESSION_19_PROMPT.md`를 만들고 `NEXT_SESSION_PROMPT.md`에 mirror하라.

## Session Size Gate

- 이번 세션은 `reminder backend + delivery`만 다룬다.
- web control plane, packaging, managed quickstart는 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
7. `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`
8. `docs/session-ops/handovers/SESSION_17_HANDOVER.md`
9. `packages/contracts/openapi/assistant-api.openapi.yaml`
10. `services/assistant-api/assistant_api/models.py`
11. `services/assistant-api/assistant_api/store.py`
12. `services/assistant-api/assistant_api/app.py`
13. `services/assistant-api/assistant_api/worker.py`
14. `services/assistant-api/assistant_api/telegram_transport.py`
15. `tests/test_assistant_api_runtime.py`
16. `tests/test_assistant_api_worker.py`

## 이번 세션의 핵심 미션

1. reminder persistence model을 runtime에 연결한다.
2. reminder create/list/cancel execution path를 만든다.
3. background worker가 reminder delivery를 실행하게 만든다.
4. Telegram delivery 결과를 `runtime_job` audit trail에 남긴다.
5. targeted backend tests를 추가한다.

## 강한 제약

1. web control plane은 이번 세션에서 크게 열지 마라.
2. packaging/install은 이번 세션에서 열지 마라.
3. managed quickstart는 이번 세션에서 다루지 마라.
4. KG-backed memory broker는 이번 세션에서 다루지 마라.

## 기대 산출물

1. reminder persistence + runtime execution
2. Telegram delivery audit path
3. reminder-focused tests
4. `SESSION_18_HANDOVER.md`
5. 다음 세션이 계속되면 `SESSION_19_PROMPT.md`와 `NEXT_SESSION_PROMPT.md` mirror

## 종료 조건

1. reminder job lifecycle이 실제 worker에서 실행된다.
2. delivery 성공/실패가 audit에 남는다.
3. export/delete/quick-capture behavior가 깨지지 않는다.
4. validation이 통과한다.

## 필수 validation

1. `.agent-orchestrator/config.json`의 validation 명령
2. reminder-focused targeted backend tests
