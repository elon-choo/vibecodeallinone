# Post-S21 Later-Wave Orchestration Plan

## 1. Purpose

This document prepares the next later wave after `S21`.

It does **not** reopen the paused chain by itself.

Current chain status must remain:

- `NEXT_SESSION_PROMPT.md` -> `SESSION_CHAIN_PAUSE`
- latest completed handover -> `docs/session-ops/handovers/SESSION_21_HANDOVER.md`

This packet exists so a later agent in a later session can resume work with:

1. a locked sequence
2. explicit dependency boundaries
3. clear stop/continue rules
4. file-level context
5. copy-paste-ready prompts

## 2. What Is Already Real After S21

The later wave must start from the current `S21` baseline, not from the older `S10` target state.

### Runtime baseline

1. `services/assistant-api` already provides:
   - auth/session bootstrap
   - explicit memory CRUD/export/delete
   - continuity checkpoint read/write
   - Telegram link state
   - Telegram-originated resume-link and quick-capture continuity
   - auditable runtime jobs
   - reminder create/list/cancel and worker delivery
2. `services/assistant-api/assistant_api/worker.py`
   - executes purge and reminder-delivery jobs
3. `services/assistant-api/assistant_api/telegram_transport.py`
   - supports polling-first Telegram transport
   - real `/start <token>` binding
   - quick capture
   - resume handoff refresh
   - outbound reminder delivery

### Web baseline

1. `apps/assistant-web`
   - consumes Telegram link state
   - consumes checkpoint continuity metadata
   - renders runtime jobs
   - renders/schedules/cancels Telegram reminders
2. browser smoke already proves:
   - auth
   - Telegram link visibility
   - continuity visibility
   - reminder schedule/cancel flow
   - memory save/export/delete
   - runtime ledger visibility

### Self-host / ops baseline

1. `scripts/assistant/bootstrap_runtime.sh`
   - generates a self-host reference-stack workspace
2. `scripts/assistant/reference_stack.sh`
   - provides `start|stop|restart|status|logs`
3. bootstrapped workspace already includes:
   - API launcher
   - web launcher
   - worker launcher
   - Telegram launcher
4. install smoke already proves:
   - bootstrap scaffold creation
   - stack start/stop
   - API/web/worker runtime health
   - Telegram disabled-state operator behavior when no bot token is configured

### Evidence baseline

`S21` refreshed all current evidence artifacts:

1. install smoke
2. Telegram runtime smoke
3. operator smoke
4. browser smoke
5. `e2e_score`

## 3. Why Another Wave Is Needed

The `S15`~`S21` wave closed the self-host MVP.

What still remains open is a different productization layer:

1. fastest user path is still supposed to be `managed quickstart`, but the repo only ships a self-host reference stack
2. live provider / real operator validation is still not productized; current operator smoke explicitly records OIDC blockers
3. project/workspace memory is still only a planned direction; there is no opt-in brokered runtime path yet
4. reminder follow-up policy hardening still remains later work, but it should not be mixed into the immediate chain below

## 4. Locked Working Decisions For The Later Wave

These are the working defaults for the prepared prompts below unless the user explicitly overrides them.

1. Later-wave priority should be:
   - `managed quickstart + live-ready productization`
   - then `KG-backed workspace/project memory broker`
   not the other way around.
2. Managed quickstart must reuse the same runtime pieces already built for self-host:
   - `assistant-api`
   - `assistant-web`
   - worker
   - Telegram transport
   It should not fork into a second backend/product path.
3. Live provider / real Telegram validation is capability-gated.
   - If real env is present, the session should exercise it.
   - If real env is absent, the session must emit explicit blocker artifacts and stop short of fake success claims.
4. KG-backed memory must be brokered in `assistant-api`, opt-in, and workspace-scoped.
   - It must not become an always-on hidden dependency for every user chat.
5. Web/PWA remains the control plane for memory scope selection, review, and consent.
6. Telegram remains action-safe and summary-safe only.
   - no raw KG dump
   - no full memory administration
7. Current self-host reference stack remains a first-class supported operator story while managed quickstart is added.
8. Reminder policy hardening remains explicitly deferred from this later wave unless a narrow fix is required.
   - recurring reminders
   - snooze/reschedule
   - retry/dead-letter expansion

## 5. Explicitly Deferred From This Later Wave

The chain below should not absorb these items.

1. recurring reminder/snooze/reschedule productization
2. team/shared memory
3. native desktop/mobile packaging
4. broad Telegram admin/moderation surface redesign
5. cloud-vendor-specific infra hardening beyond what is required to prove the managed quickstart path

## 6. Recommended Session Chain

Run the next later wave as **six** narrow sessions.

No parallel execution is recommended.

The same docs, contracts, and runtime files will be touched repeatedly, so the safest order is:

`S22 -> S23 -> S24 -> S25 -> S26 -> S27`

### Summary Table

| Session | Main Objective | Recommended Bias | Depends On |
|---|---|---|---|
| `S22` | managed quickstart deployment contract | ops/security/docs | `S21` |
| `S23` | managed quickstart operator/bootstrap path | install/ops/docs | `S22` |
| `S24` | live provider + real Telegram operator validation foundation | auth/security/operator | `S22`, `S23` |
| `S25` | KG memory broker foundation | backend/contracts/kg | `S21` |
| `S26` | broker opt-in + control-plane alignment | web/backend/smoke | `S25` |
| `S27` | later-wave closeout | QA/supervisor | `S22`~`S26` |

### Orchestration Notes

1. `S22` and `S23` should land the managed-quickstart contract and operator path before `S24` tries to validate it.
2. `S25` and `S26` are intentionally separated so the broker backend boundary lands before any web/control-plane exposure.
3. `S24` should never pretend a live env pass if the required credentials are absent.
4. `S27` should close the chain with a stop marker unless a fully scoped later objective is immediately ready.

## 7. Session Details

### `S22` Managed Quickstart Deployment Contract

#### Main objective

Define the hosted/managed quickstart runtime contract on top of the existing reference stack without introducing a second runtime architecture.

#### Why this is isolated

Managed quickstart is currently blocked less by UI than by:

1. unclear env/secret contract
2. missing deployment/operator boundary
3. unclear distinction between self-host and managed operator modes

#### Read first

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/13_PRODUCT_REPLAN_MASTER.md`
7. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
8. `docs/session-ops/15_EXECUTION_WAVES.md`
9. `docs/session-ops/18_POST_S21_LATER_WAVE_ORCHESTRATION_PLAN.md`
10. `docs/session-ops/handovers/SESSION_21_HANDOVER.md`
11. `README.md`
12. `scripts/assistant/bootstrap_runtime.sh`
13. `scripts/assistant/reference_stack.sh`
14. `scripts/assistant/run_operator_smoke.py`
15. `services/assistant-api/README.md`
16. `apps/assistant-web/README.md`

#### Current baseline to preserve

1. self-host reference stack start/stop/status works
2. `assistant-api` remains the single runtime backend
3. current public contracts remain additive-only
4. bootstrap still defaults to a safe local/mock path

#### In scope

1. managed quickstart env/secret contract
2. hosted-ready operator mode boundaries
3. deployment-ready status/readiness surface if additive and small
4. operator docs/templates for managed quickstart inputs
5. targeted validation/doc updates

#### Out of scope

1. final hosted infra vendor lock-in
2. web onboarding UX redesign
3. KG memory broker
4. reminder follow-up policy

#### Likely files touched

1. `scripts/assistant/bootstrap_runtime.sh`
2. `scripts/assistant/reference_stack.sh`
3. `services/assistant-api/assistant_api/config.py`
4. `services/assistant-api/assistant_api/app.py`
5. `services/assistant-api/README.md`
6. `README.md`
7. possible new `ops/managed/**` files

#### Exit gate

1. managed quickstart required env/secret surface is explicit
2. no second runtime path has been introduced
3. operator story distinguishes self-host vs managed quickstart without breaking self-host
4. validation passes

#### Mandatory validation

1. `.agent-orchestrator/config.json` validation commands
2. targeted operator/install checks added in this session

### `S23` Managed Quickstart Operator / Bootstrap Path

#### Main objective

Turn the `S22` contract into an operator-ready managed quickstart/bootstrap path that can be handed to a different operator or deployment automation layer.

#### Why this is isolated

The contract can land without proving the full operator path.

This session should focus on:

1. generated artifacts
2. operator commands
3. docs/runbooks
4. smoke alignment

#### Read first

1. all `S22` handover artifacts
2. `README.md`
3. `scripts/assistant/bootstrap_runtime.sh`
4. `scripts/assistant/reference_stack.sh`
5. `scripts/assistant/run_install_smoke.py`
6. `tests/test_install_smoke.sh`
7. `services/assistant-api/README.md`
8. `apps/assistant-web/README.md`

#### Current baseline to preserve

1. self-host reference stack remains the stable fallback
2. bootstrap/start/stop semantics from `S20` stay intact
3. managed quickstart stays additive to the current install story

#### In scope

1. managed quickstart bootstrap/generator path
2. operator-facing command surface
3. env templates/sample files
4. install/reference-stack smoke extension
5. operator docs and handoff docs

#### Out of scope

1. real OIDC live validation
2. KG memory broker
3. web control-plane redesign

#### Likely files touched

1. `scripts/assistant/bootstrap_runtime.sh`
2. `scripts/assistant/reference_stack.sh`
3. possible new `scripts/assistant/bootstrap_managed_quickstart.sh`
4. `tests/test_install_smoke.sh`
5. `scripts/assistant/run_install_smoke.py`
6. `README.md`
7. `services/assistant-api/README.md`
8. `apps/assistant-web/README.md`

#### Exit gate

1. one operator path for managed quickstart exists in repo artifacts/docs
2. install/reference-stack smoke can exercise the intended bootstrap contract
3. self-host path is not broken
4. validation passes

#### Mandatory validation

1. `python3 scripts/assistant/run_install_smoke.py`
2. `bash tests/test_install_smoke.sh`
3. `.agent-orchestrator/config.json` validation commands

### `S24` Live Provider + Real Telegram Operator Validation Foundation

#### Main objective

Add the real-operator validation path for OIDC/provider auth and real Telegram runtime so the product can stop relying only on mock/operator evidence.

#### Why this is isolated

This is security-sensitive and partially external-dependency-sensitive.

It should land separately from packaging or KG work.

#### Read first

1. all `S22` and `S23` handover artifacts
2. `services/assistant-api/README.md`
3. `scripts/assistant/run_operator_smoke.py`
4. `scripts/assistant/run_telegram_mock_smoke.py`
5. `scripts/assistant/smoke_support.py`
6. `.agent-orchestrator/config.json`
7. `artifacts/operator_smoke/assistant_api_operator_smoke.json`
8. `docs/session-ops/handovers/SESSION_08_HANDOVER.md`
9. `docs/session-ops/handovers/SESSION_09_HANDOVER.md`

#### Current baseline to preserve

1. mock/operator/browser/install evidence still passes without live creds
2. self-host reference stack can still start without live OIDC or Telegram credentials
3. operator smoke records blockers explicitly today

#### In scope

1. real OIDC/provider validation path
2. real Telegram operator validation path
3. stronger env preflight and blocker artifact output
4. targeted validation/runbook updates

#### Out of scope

1. managed quickstart UX
2. KG memory broker
3. broad feature redesign

#### Likely files touched

1. `scripts/assistant/run_operator_smoke.py`
2. `scripts/assistant/run_telegram_mock_smoke.py` or a new real Telegram smoke entry
3. `scripts/assistant/smoke_support.py`
4. `services/assistant-api/README.md`
5. possible `.env.example` or `ops/**` guidance files

#### Exit gate

1. operator tooling can attempt real provider and Telegram validation when env is present
2. when env is absent, the tooling emits explicit blockers and does not fake success
3. mock/self-host evidence remains intact
4. validation passes

#### Mandatory validation

1. `.agent-orchestrator/config.json` validation commands
2. targeted operator/live-validation checks added in this session

### `S25` KG Memory Broker Foundation

#### Main objective

Add the backend/contracts foundation for an opt-in workspace/project memory broker on top of current KG assets.

#### Why this is isolated

The memory broker changes:

1. data boundaries
2. consent rules
3. retrieval scope
4. audit semantics

It should not be mixed with web alignment in the same session.

#### Read first

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/13_PRODUCT_REPLAN_MASTER.md`
7. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
8. `docs/session-ops/15_EXECUTION_WAVES.md`
9. `docs/session-ops/18_POST_S21_LATER_WAVE_ORCHESTRATION_PLAN.md`
10. `docs/session-ops/handovers/SESSION_21_HANDOVER.md`
11. `kg-mcp-server/API.md`
12. `packages/contracts/openapi/assistant-api.openapi.yaml`
13. `services/assistant-api/assistant_api/models.py`
14. `services/assistant-api/assistant_api/store.py`
15. `services/assistant-api/assistant_api/app.py`

#### Current baseline to preserve

1. explicit user memory and continuity memory remain separate
2. Telegram remains summary-safe only
3. current memory CRUD/export/delete behavior remains intact
4. KG stays optional, not mandatory for every request

#### In scope

1. memory broker module/foundation
2. additive contracts for workspace/project memory opt-in
3. workspace-scoped retrieval boundary
4. audit/consent shape
5. backend tests

#### Out of scope

1. broad web UI
2. managed quickstart
3. Telegram full memory surface
4. team/shared memory

#### Likely files touched

1. `services/assistant-api/assistant_api/models.py`
2. `services/assistant-api/assistant_api/store.py`
3. `services/assistant-api/assistant_api/app.py`
4. possible new `services/assistant-api/assistant_api/memory_broker.py`
5. `packages/contracts/openapi/assistant-api.openapi.yaml`
6. possible new `packages/contracts/schemas/memory_broker/**`
7. possible new broker-focused tests

#### Exit gate

1. backend can represent workspace/project memory opt-in state
2. broker path is additive and workspace-scoped
3. no always-on KG dependency was introduced
4. validation passes

#### Mandatory validation

1. `.agent-orchestrator/config.json` validation commands
2. targeted memory-broker backend tests

### `S26` Broker Opt-In + Control-Plane Alignment

#### Main objective

Expose the broker opt-in/control state through web/PWA and evidence paths without turning Telegram into a full memory UI.

#### Why this is isolated

This is the UI/smoke slice that should consume the backend foundation from `S25`.

#### Read first

1. all `S25` handover artifacts
2. `apps/assistant-web/README.md`
3. `apps/assistant-web/index.html`
4. `apps/assistant-web/app.js`
5. `apps/assistant-web/styles.css`
6. `scripts/assistant/run_browser_smoke.py`
7. `services/assistant-api/README.md`
8. `packages/contracts/openapi/assistant-api.openapi.yaml`

#### Current baseline to preserve

1. reminder/runtime/Telegram cards already render correctly
2. current browser smoke still covers auth, Telegram, reminder, memory, runtime ledger
3. web remains the richer control plane; Telegram remains scoped

#### In scope

1. broker opt-in/control UI in web
2. scoped project/workspace memory visibility
3. browser/operator smoke updates
4. docs refresh

#### Out of scope

1. Telegram full memory admin
2. managed quickstart infra work
3. reminder follow-up policy
4. team/shared memory

#### Likely files touched

1. `apps/assistant-web/index.html`
2. `apps/assistant-web/app.js`
3. `apps/assistant-web/styles.css`
4. `apps/assistant-web/README.md`
5. `scripts/assistant/run_browser_smoke.py`
6. possible operator smoke/docs updates

#### Exit gate

1. browser smoke proves the broker opt-in/control path
2. web shows scoped broker state without contract churn
3. Telegram surfaces remain scoped/summarized
4. validation passes

#### Mandatory validation

1. `node --check apps/assistant-web/app.js`
2. `python3 scripts/assistant/run_browser_smoke.py`
3. `.agent-orchestrator/config.json` validation commands

### `S27` Later-Wave Closeout

#### Main objective

Close the later wave with refreshed evidence, validation, docs sync, and an explicit chain decision.

#### Why this is isolated

This should be a smoke/validation/doc sync session only.

#### Read first

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/15_EXECUTION_WAVES.md`
7. `docs/session-ops/18_POST_S21_LATER_WAVE_ORCHESTRATION_PLAN.md`
8. all `S22`~`S26` handovers
9. `.agent-orchestrator/config.json`
10. smoke/validation entrypoints added or updated in `S22`~`S26`

#### Current baseline to preserve

1. self-host evidence from `S21` remains valid
2. any live operator validation must stay honest about blockers
3. later-wave docs must reflect the actual result, not the desired result

#### In scope

1. rerun install/managed/operator/browser/Telegram/broker evidence as appropriate
2. rerun configured validation
3. sync canonical docs and root mirrors
4. write next prompt or stop marker

#### Out of scope

1. new product redesign
2. broad bug hunt
3. unmanaged scope expansion

#### Exit gate

1. later-wave evidence artifacts are current
2. `.agent-orchestrator/config.json` validation passes
3. canonical docs and root mirrors match the real result
4. chain decision is explicit

#### Mandatory validation

1. `.agent-orchestrator/config.json` validation commands
2. later-wave smoke entries added or updated in `S22`~`S26`

## 8. Later-Wave Activation Rule

Keep `NEXT_SESSION_PROMPT.md` on `SESSION_CHAIN_PAUSE` until the user explicitly says this later wave is now official.

When that happens:

1. update `docs/session-ops/01_SESSION_BOARD.md` first
2. create `docs/session-ops/prompts/SESSION_22_PROMPT.md`
3. mirror it into `NEXT_SESSION_PROMPT.md`
4. then start the chain

