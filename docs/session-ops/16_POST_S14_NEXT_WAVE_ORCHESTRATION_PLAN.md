# Post-S14 Next Wave Orchestration Plan

## 1. Purpose

This document prepares the next implementation wave after `S14`.

It does **not** reopen the paused chain by itself.

Current chain status must remain:

- `NEXT_SESSION_PROMPT.md` -> `SESSION_CHAIN_PAUSE`
- latest completed handover -> `docs/session-ops/handovers/SESSION_14_HANDOVER.md`

This document exists so a different agent in a different session can resume work with:

1. a locked sequence
2. explicit dependency boundaries
3. narrow session scopes
4. concrete file-level context
5. copy-paste-ready prompts

## 2. What Is Already Real

The next wave should start from the current implemented baseline, not from the older S10 wish list.

### Runtime baseline

1. `services/assistant-api/assistant_api/app.py`
   - public Telegram companion state routes exist:
     - `GET /v1/surfaces/telegram/link`
     - `POST /v1/surfaces/telegram/link`
   - public job audit route exists:
     - `GET /v1/jobs`
   - continuity metadata already rides on `GET|PUT /v1/checkpoints/current`
2. `services/assistant-api/assistant_api/store.py`
   - Telegram state is persisted in `telegram_link_state`
   - runtime audit rows are persisted in `runtime_job`
   - export/delete jobs are recorded, but only as projections
   - purge/reminder execution does not exist yet
3. `services/assistant-api/migrations/0001_bootstrap.sql`
   - additive continuity fields exist on `session_checkpoint`
   - `telegram_link_state` and `runtime_job` tables already exist

### Web baseline

1. `apps/assistant-web/app.js`
   - reads Telegram link state
   - reads continuity metadata (`surface`, `handoff_kind`, `resume_token_ref`, `last_surface_at`)
   - reads auditable runtime jobs
2. `apps/assistant-web/index.html`
   - has Telegram companion card
   - has continuity summary surface
   - has runtime jobs panel
3. `scripts/assistant/run_browser_smoke.py`
   - already proves:
     - mock auth
     - Telegram link state render
     - continuity metadata render
     - runtime job visibility

### Evidence baseline

1. `scripts/assistant/run_install_smoke.py`
   - wraps install smoke into a structured artifact
2. `scripts/assistant/run_telegram_mock_smoke.py`
   - proves mock Telegram link issuance, mock completion, resume continuity, quick capture continuity
3. `scripts/assistant/run_operator_smoke.py`
   - proves current operator runtime flow, but still records live OIDC blockers when real env is absent

### Install baseline

1. `scripts/install.sh`
   - developer toolkit installer only
2. `scripts/assistant/bootstrap_runtime.sh`
   - thin self-host runtime bootstrap only
   - explicitly says it does not configure Telegram, managed hosting, or later runtime waves
3. `tests/test_install_smoke.sh`
   - verifies developer install + runtime bootstrap scaffold

## 3. What Is Still Missing

The next wave should attack only the concrete gaps still left after `S14`.

### Missing runtime capabilities

1. real Telegram bot/runtime transport
2. real Telegram account completion path that does not rely on the hidden smoke-only route
3. executable background worker for purge/reminder jobs
4. reminder creation, delivery, and cancellation path
5. real quick-capture ingress from Telegram to runtime state
6. one-command self-host reference stack beyond the thin bootstrap scaffold

### Explicitly deferred from this wave

These are still important, but they should **not** be mixed into the immediate chain below.

1. hosted/managed quickstart implementation
2. final hosted ownership model
3. KG-backed workspace/project memory broker
4. shared/team memory
5. native desktop/mobile packaging
6. public parity claims against `openclaw`
7. unsupported `Jarvis`-internal assumptions

## 4. Locked Working Decisions For The Next Wave

These decisions are now the working defaults for the prepared prompts below unless the user explicitly overrides them.

1. Telegram self-host MVP should be `polling-first`, not `webhook-first`.
   - Reason:
     - current repo is optimized for self-host/open-source reuse
     - polling avoids HTTPS/public ingress requirements on day one
     - webhook readiness can still be preserved as a later adapter mode
2. Background execution should use a `separate worker entrypoint`, not API in-process loops.
   - Reason:
     - export/delete jobs are already modeled as auditable runtime jobs
     - purge/reminder delivery need long-running execution semantics
     - separation keeps `assistant-api` as request broker instead of becoming a mixed request+daemon process
3. Immediate packaging target is a `one-command self-host reference stack`, not hosted quickstart.
   - Reason:
     - current bootstrap already points in this direction
     - hosted quickstart still lacks owner, hosting path, and external env decisions
4. Current public contract shape from `S12` should remain additive-only.
   - Do not break existing `assistant-web` behavior.
   - Prefer new internal modules, internal routes, or additive fields over response rewrites.
5. The hidden Telegram mock completion route stays test-only until the real transport path exists.
6. Memory broker/KG integration is a later wave.
   - In this wave, Telegram must only use action-safe, continuity-safe data.

## 5. Recommended Session Chain

The next implementation wave should be run as **seven** narrow sessions.

No parallel execution is recommended.

The same files will be touched repeatedly, and the chain will be safer if it stays strictly sequential:

`S15 -> S16 -> S17 -> S18 -> S19 -> S20 -> S21`

### Summary Table

| Session | Main Objective | Recommended Bias | Depends On |
|---|---|---|---|
| `S15` | executable worker foundation | backend/runtime | `S14` |
| `S16` | real Telegram transport foundation | backend/security | `S15` |
| `S17` | Telegram quick-capture + resume backend path | backend/product runtime | `S16` |
| `S18` | reminder backend + delivery execution | backend/jobs | `S15`, `S16`, `S17` |
| `S19` | web control-plane alignment + browser smoke | frontend/smoke | `S17`, `S18` |
| `S20` | one-command self-host reference stack | install/ops/docs | `S15`~`S19` |
| `S21` | release-evidence closeout | QA/supervisor | `S15`~`S20` |

## 6. Session Details

### `S15` Worker Foundation

#### Main objective

Turn `runtime_job` from a read-only audit projection into a real executable worker foundation without touching Telegram transport or web UI.

#### Why this is isolated

Current Telegram and reminder work are blocked less by schema and more by the lack of a real executor.

Without a worker:

1. purge is still a queued receipt only
2. reminders cannot actually deliver
3. Telegram actions cannot safely hand work off to a background runtime

#### Read first

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

#### Current baseline to preserve

1. `delete_memory_item()` already enqueues purge intent into `memory_delete_job` and `runtime_job`
2. `create_memory_export()` already writes export artifacts synchronously and records a succeeded job row
3. `assistant-api` is still the single request/runtime broker

#### In scope

1. worker entrypoint and runtime loop
2. job claim/lease/update lifecycle
3. purge execution path
4. reminder job persistence foundation
5. backend tests for worker behavior
6. minimal docs for local worker run

#### Out of scope

1. real Telegram ingress
2. web UI work
3. managed quickstart
4. KG memory broker

#### Likely files touched

1. `services/assistant-api/assistant_api/store.py`
2. `services/assistant-api/assistant_api/models.py`
3. `services/assistant-api/assistant_api/config.py`
4. `services/assistant-api/migrations/0001_bootstrap.sql`
5. `services/assistant-api/assistant_api/worker.py` or equivalent new module
6. `scripts/assistant/run_job_worker.py` or equivalent new entrypoint
7. `tests/test_assistant_api_runtime.py`
8. possible new worker-specific test file

#### Exit gate

1. queued purge work can be claimed and executed
2. runtime job status transitions are persisted (`queued -> running -> succeeded/failed`)
3. reminder-delivery jobs have a durable persistence path, even if Telegram delivery itself lands later
4. no Telegram transport code has been introduced yet

#### Mandatory validation

1. `.agent-orchestrator/config.json` validation commands
2. targeted worker tests added in this session

### `S16` Telegram Transport Foundation

#### Main objective

Add a real Telegram transport/adapter path for self-host MVP so link completion no longer depends only on the hidden smoke-only route.

#### Why this is isolated

Transport, token handling, and inbound update handling are security-sensitive and should land before quick capture or reminder features build on top.

#### Read first

1. all `S15` handover artifacts
2. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
3. `services/assistant-api/README.md`
4. `services/assistant-api/assistant_api/app.py`
5. `services/assistant-api/assistant_api/store.py`
6. `services/assistant-api/assistant_api/config.py`
7. `tests/test_assistant_api_runtime.py`
8. `scripts/assistant/run_telegram_mock_smoke.py`

#### Current baseline to preserve

1. public Telegram route shape must stay:
   - `GET /v1/surfaces/telegram/link`
   - `POST /v1/surfaces/telegram/link`
2. hidden test route can remain for smoke, but must stop being the only path that can complete binding
3. all Telegram secrets stay server-side

#### In scope

1. Telegram adapter abstraction
2. polling-first self-host runtime entrypoint
3. config/env additions for bot token and runtime mode
4. secure link completion via actual Telegram-side message handling
5. backend tests for inbound link completion

#### Out of scope

1. quick capture semantics
2. reminder delivery semantics
3. web control-plane updates

#### Likely files touched

1. `services/assistant-api/assistant_api/config.py`
2. `services/assistant-api/assistant_api/app.py`
3. `services/assistant-api/assistant_api/store.py`
4. new Telegram adapter/runtime files under `services/assistant-api/assistant_api/`
5. new runtime launcher under `scripts/assistant/`
6. tests for Telegram transport/runtime path

#### Exit gate

1. a Telegram runtime path exists that can complete a pending link without using the smoke-only route
2. transport can run in self-host MVP mode without public webhook infrastructure
3. public Telegram link state reflects the linked result of the real runtime path

#### Mandatory validation

1. `.agent-orchestrator/config.json` validation commands
2. targeted Telegram runtime/backend tests

### `S17` Telegram Quick Capture + Resume Backend

#### Main objective

Implement actual Telegram-originated quick capture and resume-handoff backend behavior on top of the real transport.

#### Why this is isolated

Current continuity metadata exists, but it is only written by tests and smoke. This session should make Telegram-originated state changes real without dragging reminder delivery or web UI into the same prompt.

#### Read first

1. `S16` handover
2. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
3. `services/assistant-api/assistant_api/app.py`
4. `services/assistant-api/assistant_api/store.py`
5. `services/assistant-api/assistant_api/models.py`
6. `tests/test_assistant_api_runtime.py`
7. `scripts/assistant/run_telegram_mock_smoke.py`

#### Current baseline to preserve

1. Telegram remains a fast-action surface, not the full admin UI
2. web/PWA remains the canonical restore surface for full context
3. continuity metadata must remain additive and compatible with existing web shell logic

#### In scope

1. Telegram-originated quick capture path
2. resume-link continuity updates
3. action-safe memory handling for Telegram-originated data
4. API/runtime tests covering real Telegram-originated continuity updates
5. updating Telegram smoke to use the new runtime path where appropriate

#### Out of scope

1. reminder scheduling/delivery
2. major web UI redesign
3. KG-backed workspace memory

#### Likely files touched

1. `services/assistant-api/assistant_api/app.py`
2. `services/assistant-api/assistant_api/store.py`
3. `services/assistant-api/assistant_api/models.py`
4. possible new helper/service modules for Telegram action handling
5. `tests/test_assistant_api_runtime.py`
6. `scripts/assistant/run_telegram_mock_smoke.py` or a successor runtime smoke

#### Exit gate

1. Telegram-originated quick capture can update continuity state without synthetic test-only writes
2. resume token / handoff metadata is preserved end to end
3. Telegram actions only touch action-safe memory/continuity paths

#### Mandatory validation

1. `.agent-orchestrator/config.json` validation commands
2. targeted Telegram continuity tests

### `S18` Reminder Backend + Delivery

#### Main objective

Add real reminder creation, scheduling, delivery, and audit lifecycle on top of the worker and Telegram transport.

#### Why this is isolated

Reminder execution spans:

1. persistence
2. scheduling
3. background execution
4. Telegram delivery
5. audit visibility

It is already broad enough on the backend and should not also take web work in the same session.

#### Read first

1. `S15`, `S16`, `S17` handovers
2. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
3. `services/assistant-api/assistant_api/app.py`
4. `services/assistant-api/assistant_api/store.py`
5. `services/assistant-api/assistant_api/models.py`
6. `packages/contracts/openapi/assistant-api.openapi.yaml`
7. `tests/test_assistant_api_runtime.py`

#### Current baseline to preserve

1. existing export/delete audit visibility
2. existing web shell consumption of `GET /v1/jobs`
3. existing surface-scoped security assumptions from S10

#### In scope

1. reminder persistence model
2. reminder job scheduling / execution
3. Telegram delivery path for reminders
4. cancel/snooze-ready audit shape if small and additive
5. backend tests for reminder lifecycle

#### Out of scope

1. major web UI work
2. managed quickstart
3. workspace/project memory broker

#### Likely files touched

1. `packages/contracts/openapi/assistant-api.openapi.yaml`
2. `packages/contracts/schemas/jobs/*`
3. `services/assistant-api/assistant_api/models.py`
4. `services/assistant-api/assistant_api/store.py`
5. `services/assistant-api/assistant_api/app.py`
6. worker modules added in `S15`
7. `tests/test_assistant_api_runtime.py`

#### Exit gate

1. reminder jobs can be created and delivered in the runtime
2. runtime jobs show reminder delivery lifecycle, not only export/delete
3. delivery failures are auditable

#### Mandatory validation

1. `.agent-orchestrator/config.json` validation commands
2. targeted reminder lifecycle tests

### `S19` Web Control Plane + Browser Smoke

#### Main objective

Expose the new reminder/runtime state cleanly in `assistant-web` and align browser smoke with the new real Telegram/runtime behaviors.

#### Why this is isolated

The backend wave should settle first. This session is only for control-plane consumption and evidence alignment.

#### Read first

1. `S18` handover
2. `apps/assistant-web/README.md`
3. `apps/assistant-web/index.html`
4. `apps/assistant-web/app.js`
5. `apps/assistant-web/styles.css`
6. `scripts/assistant/run_browser_smoke.py`
7. `services/assistant-api/README.md`
8. `tests/test_assistant_api_runtime.py`

#### Current baseline to preserve

1. current auth/memory/trust flow must not regress
2. Telegram link and continuity cards already exist
3. browser smoke already proves current web shell basics

#### In scope

1. reminder/runtime state in the web control plane
2. continuity display refinements if required by backend changes
3. browser smoke update for real Telegram/runtime-backed flows
4. minimal README refresh for new operator path

#### Out of scope

1. backend contract redesign
2. install/bootstrap redesign
3. managed quickstart

#### Likely files touched

1. `apps/assistant-web/index.html`
2. `apps/assistant-web/app.js`
3. `apps/assistant-web/styles.css`
4. `apps/assistant-web/README.md`
5. `scripts/assistant/run_browser_smoke.py`

#### Exit gate

1. browser smoke exercises the new Telegram/reminder/job state
2. web shell can inspect reminder/runtime outcomes without backend contract churn
3. no auth/memory/trust regression

#### Mandatory validation

1. `node --check apps/assistant-web/app.js`
2. `python3 scripts/assistant/run_browser_smoke.py`
3. `.agent-orchestrator/config.json` validation commands

### `S20` One-Command Self-Host Reference Stack

#### Main objective

Turn the current thin bootstrap into a one-command self-host reference stack that can start web, API, worker, and Telegram runtime pieces together.

#### Why this is isolated

Packaging and docs tend to sprawl. This session should focus only on operator experience and stack startup/stop behavior after the runtime pieces are already in place.

#### Read first

1. `S15`~`S19` handovers
2. `README.md`
3. `scripts/assistant/bootstrap_runtime.sh`
4. `scripts/assistant/run_install_smoke.py`
5. `tests/test_install_smoke.sh`
6. `services/assistant-api/README.md`
7. `apps/assistant-web/README.md`

#### Current baseline to preserve

1. install story split from `S11`
2. thin bootstrap script still valid for local scaffold generation
3. current install smoke artifact wrapper

#### In scope

1. one-command reference stack launcher and stop path
2. operator-facing env/template cleanup
3. self-host docs refresh
4. install smoke wrapper expansion for worker/runtime stack
5. Telegram runtime smoke wrapper if the real transport is now available in self-host mode

#### Out of scope

1. hosted/managed quickstart
2. Kubernetes/cloud deployment
3. product surface redesign

#### Likely files touched

1. `README.md`
2. `scripts/assistant/bootstrap_runtime.sh`
3. new stack runner scripts under `scripts/assistant/`
4. `tests/test_install_smoke.sh`
5. `scripts/assistant/run_install_smoke.py`
6. possible new Telegram runtime smoke wrapper

#### Exit gate

1. operator can start the full reference stack with one command
2. install/reference-stack smoke proves the new path
3. docs explain what is still self-host only and what remains deferred

#### Mandatory validation

1. `.agent-orchestrator/config.json` validation commands
2. install/reference-stack smoke
3. Telegram runtime smoke if created here

### `S21` Closeout

#### Main objective

Run all release-evidence checks for the new wave, sync docs, and explicitly decide whether the chain pauses again or moves into a later wave.

#### Why this is isolated

Closeout should not be mixed with implementation. This is the same discipline that made `S14` reliable.

#### Read first

1. `S15`~`S20` handovers
2. `docs/session-ops/01_SESSION_BOARD.md`
3. `docs/session-ops/15_EXECUTION_WAVES.md`
4. `.agent-orchestrator/config.json`
5. all smoke entrypoints under `scripts/assistant/`

#### In scope

1. install/reference-stack smoke
2. Telegram runtime smoke
3. operator smoke
4. browser smoke
5. configured validation
6. canonical doc sync
7. root mirror sync
8. stop-marker or next-wave prompt decision

#### Out of scope

1. feature redesign
2. broad runtime refactor
3. managed quickstart build-out

#### Exit gate

1. all targeted smoke artifacts exist and are current
2. `.agent-orchestrator/config.json` validation passes
3. canonical docs and root mirrors match the real result
4. `NEXT_SESSION_PROMPT.md` contains either a new explicit prompt or a stop marker

## 7. Manual Orchestration Rules For Other Agents

If the user starts these sessions manually with separate agents:

1. keep the chain paused until the user explicitly says this next wave is now official
2. use the prompt pack from `17_NEXT_WAVE_PROMPT_PACK.md`
3. run only one session objective per agent/session
4. do not skip handover quality even in manual sessions
5. if a session discovers the scope is too big, split before coding

## 8. Deferred Topics After This Wave

These deserve their own later planning packet and should not be pulled into `S15`~`S21`.

1. KG-backed workspace/project memory broker
2. managed quickstart / hosted deployment implementation
3. real OIDC/live provider productization
4. team/shared memory
5. native packaging
