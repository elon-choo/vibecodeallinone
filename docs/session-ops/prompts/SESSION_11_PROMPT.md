# SESSION_11_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S11`이며, 목적은 **install story를 분리하고 assistant runtime bootstrap foundation만 만드는 것**이다.

## Session Size Gate

- 이번 세션은 `install/bootstrap`만 다룬다.
- contracts/API/web/smoke 전체를 한 번에 건드리지 마라.
- 남은 backend/web/smoke 작업은 다음 세션 prompt로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/README.md`
6. `docs/session-ops/01_SESSION_BOARD.md`
7. `docs/session-ops/13_PRODUCT_REPLAN_MASTER.md`
8. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
9. `docs/session-ops/15_EXECUTION_WAVES.md`
10. `docs/session-ops/handovers/SESSION_10_HANDOVER.md`
11. `README.md`
12. `scripts/install.sh`
13. `tests/test_install_smoke.sh`

## 이번 세션의 핵심 미션

1. `README.md`에서 power-pack developer install story와 assistant runtime install story를 분리한다.
2. assistant runtime용 얇은 bootstrap entrypoint를 추가한다.
3. install smoke를 새 bootstrap 경로에 맞게 갱신한다.
4. canonical docs와 root mirrors를 sync하고 `SESSION_12_PROMPT.md`로 넘긴다.

## 강한 제약

1. contracts/API/web 전체 구현까지 이번 세션에 억지로 넣지 마라.
2. `openclaw`, `Jarvis`, Telegram 세부를 local 근거 없이 지어내지 마라.
3. 계획이 바뀌면 먼저 `docs/session-ops/01_SESSION_BOARD.md`의 `Plan Change Log`를 수정하라.

## 이번 세션 종료 조건

1. install story가 두 갈래로 명확히 분리됐다.
2. assistant runtime bootstrap entry가 저장소에 생겼다.
3. install smoke가 그 entrypoint를 기준으로 갱신됐다.
4. `docs/session-ops/handovers/SESSION_11_HANDOVER.md`와 `docs/session-ops/prompts/SESSION_12_PROMPT.md`가 준비됐다.
