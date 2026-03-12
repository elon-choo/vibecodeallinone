# SESSION_16_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S16`이며, 목적은 **polling-first self-host Telegram transport foundation을 추가하는 것**이다.

## Official Chain Note

- 이 prompt는 `S15`가 worker foundation으로 종료된 뒤 이어지는 canonical next-session prompt다.
- canonical next-wave context는 `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`에 잠겨 있다.
- 이번 세션 종료 시 `S17`이 여전히 다음 세션이면 `docs/session-ops/prompts/SESSION_17_PROMPT.md`를 만들고 `NEXT_SESSION_PROMPT.md`에 mirror하라.

## Session Size Gate

- 이번 세션은 `Telegram transport foundation`만 다룬다.
- quick capture, reminders, web UI, managed quickstart는 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
7. `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`
8. `docs/session-ops/handovers/SESSION_15_HANDOVER.md`
9. `services/assistant-api/README.md`
10. `services/assistant-api/assistant_api/app.py`
11. `services/assistant-api/assistant_api/store.py`
12. `services/assistant-api/assistant_api/config.py`
13. worker/runtime files added in `S15`
14. `tests/test_assistant_api_runtime.py`
15. `tests/test_assistant_api_worker.py`
16. `scripts/assistant/run_telegram_mock_smoke.py`

## 이번 세션의 핵심 미션

1. Telegram adapter/runtime foundation을 추가한다.
   - polling-first self-host mode
   - webhook-ready seam은 남기되 webhook 구현을 강제하지 마라
2. bot token/runtime env를 추가한다.
3. hidden smoke-only completion route와 별도로, 실제 Telegram-side message handling으로 link completion이 가능하게 만든다.
4. backend tests를 추가한다.

## 강한 제약

1. quick capture semantics는 이번 세션에서 구현하지 마라.
2. reminder delivery는 이번 세션에서 구현하지 마라.
3. Telegram secrets는 절대 browser/web surface로 내보내지 마라.
4. public `GET|POST /v1/surfaces/telegram/link` shape는 additive-only로 유지하라.

## 기대 산출물

1. Telegram transport/adapter module
2. polling runtime entrypoint
3. secure link completion path
4. transport-focused tests
5. `SESSION_16_HANDOVER.md`
6. 다음 세션이 계속되면 `SESSION_17_PROMPT.md`와 `NEXT_SESSION_PROMPT.md` mirror

## 종료 조건

1. pending link가 smoke-only route 없이도 Telegram runtime path로 linked 상태가 된다.
2. self-host MVP에서 public webhook 없이 transport를 돌릴 수 있다.
3. validation이 통과한다.

## 필수 validation

1. `.agent-orchestrator/config.json`의 validation 명령
2. Telegram transport/runtime tests
