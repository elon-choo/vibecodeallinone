# Next Wave Copy-Paste Prompt Pack

## 1. How To Use This Pack

These prompts are **prepared but inactive**.

Current chain state must stay:

- `NEXT_SESSION_PROMPT.md` -> `SESSION_CHAIN_PAUSE`

Use these prompts only when the user explicitly wants to resume the next wave.

If a prompt below is used in a manual session:

1. read the exact files it lists first
2. keep scope to one objective only
3. do not unpause `NEXT_SESSION_PROMPT.md` automatically unless the user explicitly promotes the session into the official chain
4. if the user does promote it into the official chain:
   - update `docs/session-ops/01_SESSION_BOARD.md` first
   - create the numbered handover
   - create the next numbered prompt
   - sync root mirrors

## 2. Copy-Paste Prompts

### Draft Prompt A: `S15 Worker Foundation`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S15`이며, 목적은 **projection-only runtime jobs를 executable worker foundation으로 승격하는 것**이다.

## Activation Note

- 이 prompt는 `S14` 이후 pause 상태에서 준비된 draft다.
- 사용자가 이 wave를 공식 재개한다고 명시하지 않은 이상 `NEXT_SESSION_PROMPT.md`는 건드리지 마라.
- 공식 세션으로 승격된 경우에만 canonical handover/next prompt/root mirror를 갱신하라.

## Session Size Gate

- 이번 세션은 `worker foundation`만 다룬다.
- Telegram transport, quick capture, reminder delivery UI, managed quickstart는 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
7. `docs/session-ops/15_EXECUTION_WAVES.md`
8. `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`
9. `docs/session-ops/handovers/SESSION_14_HANDOVER.md`
10. `services/assistant-api/README.md`
11. `services/assistant-api/assistant_api/app.py`
12. `services/assistant-api/assistant_api/store.py`
13. `services/assistant-api/assistant_api/models.py`
14. `services/assistant-api/assistant_api/config.py`
15. `services/assistant-api/migrations/0001_bootstrap.sql`
16. `tests/test_assistant_api_runtime.py`

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
5. 공식 세션이면 `SESSION_15_HANDOVER.md`와 `SESSION_16` next prompt

## 종료 조건

1. queued purge work가 실제로 실행된다.
2. runtime job 상태 전이가 DB에 남는다.
3. reminder job foundation이 persistence 수준에서 준비된다.
4. validation이 통과한다.

## 필수 validation

1. `.agent-orchestrator/config.json`의 validation 명령
2. 이번 세션이 추가한 worker/purge 관련 targeted tests
```

### Draft Prompt B: `S16 Telegram Transport Foundation`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S16`이며, 목적은 **polling-first self-host Telegram transport foundation을 추가하는 것**이다.

## Activation Note

- 이 prompt는 prepared draft다.
- 사용자가 wave 재개를 명시하지 않았다면 `NEXT_SESSION_PROMPT.md`는 유지하라.

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
13. `tests/test_assistant_api_runtime.py`
14. `scripts/assistant/run_telegram_mock_smoke.py`

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
5. 공식 세션이면 `SESSION_16_HANDOVER.md`와 `SESSION_17` next prompt

## 종료 조건

1. pending link가 smoke-only route 없이도 Telegram runtime path로 linked 상태가 된다.
2. self-host MVP에서 public webhook 없이 transport를 돌릴 수 있다.
3. validation이 통과한다.

## 필수 validation

1. `.agent-orchestrator/config.json`의 validation 명령
2. Telegram transport/runtime tests
```

### Draft Prompt C: `S17 Telegram Quick Capture + Resume Backend`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S17`이며, 목적은 **Telegram-originated quick capture와 resume continuity backend path를 실제로 만드는 것**이다.

## Session Size Gate

- 이번 세션은 `Telegram quick capture + resume backend`만 다룬다.
- reminder delivery, web control plane, packaging은 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
7. `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`
8. `docs/session-ops/handovers/SESSION_16_HANDOVER.md`
9. `services/assistant-api/assistant_api/app.py`
10. `services/assistant-api/assistant_api/store.py`
11. `services/assistant-api/assistant_api/models.py`
12. `tests/test_assistant_api_runtime.py`
13. `scripts/assistant/run_telegram_mock_smoke.py`

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
4. 공식 세션이면 `SESSION_17_HANDOVER.md`와 `SESSION_18` next prompt

## 종료 조건

1. Telegram-originated quick capture가 continuity 상태를 바꾼다.
2. resume link metadata가 실제 runtime path로 생성/유지된다.
3. 기존 web shell contract는 깨지지 않는다.
4. validation이 통과한다.
```

### Draft Prompt D: `S18 Reminder Backend + Delivery`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S18`이며, 목적은 **reminder scheduling/delivery를 background worker + Telegram transport 위에 올리는 것**이다.

## Session Size Gate

- 이번 세션은 `reminder backend + delivery`만 다룬다.
- web control plane과 packaging은 다음 세션으로 넘긴다.

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
13. worker/runtime files added in `S15`
14. Telegram transport files added in `S16`
15. `tests/test_assistant_api_runtime.py`

## 이번 세션의 핵심 미션

1. reminder persistence model을 추가한다.
2. reminder create/list/cancel execution path를 만든다.
3. background worker가 reminder delivery를 실행하게 만든다.
4. Telegram delivery 결과를 `runtime_job` audit trail에 남긴다.
5. targeted backend tests를 추가한다.

## 강한 제약

1. web control plane은 이번 세션에서 크게 열지 마라.
2. packaging/install은 이번 세션에서 열지 마라.
3. managed quickstart는 이번 세션에서 다루지 마라.

## 기대 산출물

1. reminder persistence + runtime execution
2. Telegram delivery audit path
3. reminder-focused tests
4. 공식 세션이면 `SESSION_18_HANDOVER.md`와 `SESSION_19` next prompt

## 종료 조건

1. reminder job lifecycle이 실행된다.
2. delivery 성공/실패가 audit에 남는다.
3. export/delete job behavior가 깨지지 않는다.
4. validation이 통과한다.
```

### Draft Prompt E: `S19 Web Control Plane + Browser Smoke`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S19`이며, 목적은 **assistant-web를 reminder/runtime 상태에 맞추고 browser smoke를 갱신하는 것**이다.

## Session Size Gate

- 이번 세션은 `web surface + browser smoke`만 다룬다.
- backend contract 재설계나 install packaging은 다음 세션으로 넘긴다.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`
7. `docs/session-ops/handovers/SESSION_18_HANDOVER.md`
8. `apps/assistant-web/README.md`
9. `apps/assistant-web/index.html`
10. `apps/assistant-web/app.js`
11. `apps/assistant-web/styles.css`
12. `scripts/assistant/run_browser_smoke.py`
13. `services/assistant-api/README.md`

## 이번 세션의 핵심 미션

1. reminder/runtime 상태를 web control plane에 최소 노출한다.
2. Telegram quick capture/resume 관련 상태를 필요한 만큼 정리한다.
3. browser smoke를 새 runtime state에 맞게 갱신한다.
4. docs를 최소 갱신한다.

## 강한 제약

1. backend shape를 크게 바꾸지 마라.
2. install/bootstrap story를 다시 열지 마라.
3. UI를 넓게 재디자인하지 마라.

## 기대 산출물

1. web control-plane alignment
2. browser smoke alignment
3. 공식 세션이면 `SESSION_19_HANDOVER.md`와 `SESSION_20` next prompt

## 종료 조건

1. browser smoke가 new runtime state를 실제로 밟는다.
2. auth/memory/trust 기존 흐름이 유지된다.
3. validation이 통과한다.
```

### Draft Prompt F: `S20 One-Command Self-Host Reference Stack`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S20`이며, 목적은 **thin bootstrap을 one-command self-host reference stack으로 승격하는 것**이다.

## Session Size Gate

- 이번 세션은 `install/ops/docs/reference-stack packaging`만 다룬다.
- backend feature redesign이나 web surface redesign은 다시 열지 마라.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`
7. `docs/session-ops/handovers/SESSION_19_HANDOVER.md`
8. `README.md`
9. `scripts/assistant/bootstrap_runtime.sh`
10. `scripts/assistant/run_install_smoke.py`
11. `scripts/assistant/run_telegram_mock_smoke.py`
12. `tests/test_install_smoke.sh`
13. `services/assistant-api/README.md`
14. `apps/assistant-web/README.md`

## 이번 세션의 핵심 미션

1. one-command self-host reference stack start/stop path를 만든다.
2. API + worker + web + Telegram runtime pieces를 같은 operator story로 묶는다.
3. install/reference-stack smoke를 갱신한다.
4. self-host docs를 현재 구현 수준에 맞게 정리한다.

## 강한 제약

1. hosted/managed quickstart는 만들지 마라.
2. product surface redesign은 하지 마라.
3. broad infra stack(Kubernetes 등)은 넣지 마라.

## 기대 산출물

1. one-command reference stack launcher
2. reference-stack smoke path
3. refreshed self-host docs
4. 공식 세션이면 `SESSION_20_HANDOVER.md`와 `SESSION_21` next prompt

## 종료 조건

1. reference stack이 one command로 올라간다.
2. install/reference-stack smoke가 통과한다.
3. validation이 통과한다.
```

### Draft Prompt G: `S21 Closeout`

```md
프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S21`이며, 목적은 **next-wave release evidence, validation, doc sync, chain decision을 마감하는 것**이다.

## Session Size Gate

- 이번 세션은 `smoke/validation/closeout`만 다룬다.
- 기능 재설계나 broad bug hunt로 세션을 넓히지 마라.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/15_EXECUTION_WAVES.md`
7. `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`
8. `docs/session-ops/handovers/SESSION_20_HANDOVER.md`
9. `.agent-orchestrator/config.json`
10. `scripts/assistant/run_install_smoke.py`
11. `scripts/assistant/run_telegram_mock_smoke.py` 또는 real Telegram runtime smoke entry
12. `scripts/assistant/run_operator_smoke.py`
13. `scripts/assistant/run_browser_smoke.py`

## 이번 세션의 핵심 미션

1. install/reference-stack smoke를 마감한다.
2. Telegram runtime smoke를 마감한다.
3. operator/browser smoke와 configured validation을 실행한다.
4. canonical docs와 root mirrors를 sync한다.
5. 다음 wave가 준비됐으면 새 prompt를 만들고, 아니면 stop marker를 남긴다.

## 강한 제약

1. feature redesign은 하지 마라.
2. narrow fix가 필요한 경우만 최소 수정하라.
3. docs와 evidence가 실제 결과와 어긋나지 않게 하라.

## 기대 산출물

1. full evidence artifact set
2. canonical closeout docs
3. root mirror sync
4. next prompt 또는 stop marker

## 종료 조건

1. all targeted smoke artifacts are current
2. `.agent-orchestrator/config.json` validation passes
3. canonical docs and root mirrors match the real result
4. chain decision is explicit
```
