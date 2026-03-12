# SESSION_17_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S17`이며, 목적은 **Telegram-originated quick capture와 resume continuity backend path를 실제로 만드는 것**이다.

## Official Chain Note

- 이 prompt는 `S16`이 Telegram transport foundation으로 종료된 뒤 이어지는 canonical next-session prompt다.
- canonical next-wave context는 `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`에 잠겨 있다.
- 이번 세션 종료 시 `S18`이 여전히 다음 세션이면 `docs/session-ops/prompts/SESSION_18_PROMPT.md`를 만들고 `NEXT_SESSION_PROMPT.md`에 mirror하라.

## Session Size Gate

- 이번 세션은 `Telegram quick capture + resume backend`만 다룬다.
- reminder delivery, web UI, packaging, managed quickstart는 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
7. `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`
8. `docs/session-ops/handovers/SESSION_16_HANDOVER.md`
9. `services/assistant-api/README.md`
10. `services/assistant-api/assistant_api/app.py`
11. `services/assistant-api/assistant_api/models.py`
12. `services/assistant-api/assistant_api/store.py`
13. `services/assistant-api/assistant_api/telegram_transport.py`
14. `tests/test_assistant_api_runtime.py`
15. `tests/test_assistant_api_telegram.py`
16. `scripts/assistant/run_telegram_mock_smoke.py`

## 이번 세션의 핵심 미션

1. Telegram-originated quick capture path를 구현한다.
2. resume-link continuity metadata가 실제 Telegram runtime path에서 생성되게 만든다.
3. action-safe memory/continuity rules를 적용한다.
4. Telegram smoke 또는 targeted backend tests를 갱신한다.

## 강한 제약

1. reminder scheduling/delivery는 이번 세션에서 넣지 마라.
2. web UI는 건드리지 마라.
3. KG-backed memory broker를 이번 세션에서 설계하지 마라.
4. Telegram surface가 full memory admin UI처럼 동작하게 만들지 마라.

## 기대 산출물

1. quick capture backend path
2. real resume continuity backend path
3. targeted tests/smoke updates
4. `SESSION_17_HANDOVER.md`
5. 다음 세션이 계속되면 `SESSION_18_PROMPT.md`와 `NEXT_SESSION_PROMPT.md` mirror

## 종료 조건

1. Telegram-originated quick capture가 continuity 상태를 바꾼다.
2. resume link metadata가 실제 runtime path로 생성/유지된다.
3. 기존 web shell contract는 깨지지 않는다.
4. validation이 통과한다.

## 필수 validation

1. `.agent-orchestrator/config.json`의 validation 명령
2. quick capture/resume 관련 targeted backend tests 또는 smoke
