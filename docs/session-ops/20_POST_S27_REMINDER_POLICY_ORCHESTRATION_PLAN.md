# Post-S27 Reminder Policy Orchestration Plan

## 1. Purpose

This document prepares the next post-later-wave slice after `S27`.

It does **not** reopen the paused chain by itself.

Current chain status must remain:

- `NEXT_SESSION_PROMPT.md` -> `SESSION_CHAIN_PAUSE`
- latest completed handover -> `docs/session-ops/handovers/SESSION_27_HANDOVER.md`

This packet exists so the next session can resume with:

1. a narrow post-`S27` objective
2. explicit scope boundaries
3. copy-paste-ready prompts
4. a concrete orchestration guide
5. stop rules that keep the chain honest

## 2. Why This Wave Now

The original product direction still includes:

1. reminders / scheduled nudges as first-class assistant convenience
2. auditable background jobs
3. cross-surface continuity with Telegram as a fast-action surface
4. explicit policy around reminder history, ownership, and operational safety

After `S27`, two reasonable next directions remained:

1. managed quickstart live pass evidence
2. reminder follow-up policy hardening

This packet chooses `reminder follow-up policy hardening` first because:

1. it advances the original user-facing assistant value directly
2. it can move forward inside the current repo without waiting for external managed OIDC/Telegram env
3. the current runtime already has one-shot reminder scheduling, cancel, delivery, and audit, so the next additive seam is follow-up policy
4. `S27` already productized the blocker path for live validation, so that branch is no longer under-specified

## 3. Current Baseline After S27

The next wave starts from the current `S27` baseline, not from older planning assumptions.

### Reminder/runtime baseline

1. `assistant-api` already supports reminder create/list/cancel
2. worker delivery already records success/failure/cancel audit
3. `assistant-web` already renders reminder state and supports schedule/cancel
4. browser smoke already covers reminder schedule/cancel and runtime ledger visibility
5. Telegram remains action-safe and summary-safe

### Managed/live baseline

1. managed quickstart contract and operator/bootstrap path are already documented
2. live provider/live Telegram validation path is productized
3. when env is absent, explicit blocker artifacts are already the correct output

### KG baseline

1. workspace/project memory broker backend foundation is landed
2. broker opt-in/control state is exposed in the web control plane
3. Telegram still does not receive raw KG retrieval

## 4. Locked Working Decisions For The Reminder Policy Wave

These are the defaults for the prepared prompts below unless the user explicitly overrides them.

1. This wave is about `reminder follow-up policy hardening`, not about re-opening managed quickstart or KG architecture.
2. Existing one-shot reminder scheduling and cancel behavior must remain valid and additive-only.
3. Follow-up policy should start with explicit state and audit semantics before broad UX redesign.
4. Telegram remains action-safe only.
   - no full planner/admin surface
   - no hidden retries without audit
5. Reminder follow-up state must stay user-scoped and job-scoped.
6. If retry/dead-letter behavior is added, it must be visible in runtime records and evidence.
7. If a follow-up action cannot be safely exposed in the current web shell, it should land as backend/operator contract first.
8. This wave should preserve the existing live-validation blocker rule:
   - no fake success when env is absent

## 5. Explicitly Deferred From This Wave

The chain below should not absorb these items.

1. managed quickstart live pass evidence with real external env
2. broad reminder planner redesign
3. cron-style or DSL-heavy recurring workflow design
4. team/shared reminder workflows
5. KG memory broker redesign
6. native packaging or broad mobile-specific UX work

## 6. Recommended Session Chain

Run the next post-`S27` wave as **three** narrow sessions.

Recommended order:

`S28 -> S29 -> S30`

### Summary Table

| Session | Main Objective | Recommended Bias | Depends On |
|---|---|---|---|
| `S28` | reminder follow-up policy contract | backend/contracts/docs | `S27` |
| `S29` | follow-up control-plane/operator alignment | web/smoke/docs | `S28` |
| `S30` | reminder-policy closeout | QA/supervisor | `S28`, `S29` |

### Orchestration Notes

1. `S28` should land the additive policy/state contract before any UI/control-plane exposure.
2. `S29` should consume the `S28` shape rather than redesigning it.
3. `S30` should close the chain with a stop marker unless a fully scoped next objective is immediately ready.

## 7. Session Details

### `S28` Reminder Follow-Up Policy Contract

#### Main objective

Define the additive reminder follow-up policy and minimal runtime seam for:

1. snooze/reschedule-ready state
2. retry/dead-letter-ready state
3. explicit ownership and audit semantics

#### Why this is isolated

This session changes reminder lifecycle semantics and job-state meaning.

It should land separately from any broader web UX or orchestration closeout work.

#### Read first

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
7. `docs/session-ops/15_EXECUTION_WAVES.md`
8. `docs/session-ops/20_POST_S27_REMINDER_POLICY_ORCHESTRATION_PLAN.md`
9. `docs/session-ops/handovers/SESSION_18_HANDOVER.md`
10. `docs/session-ops/handovers/SESSION_19_HANDOVER.md`
11. `docs/session-ops/handovers/SESSION_27_HANDOVER.md`
12. `packages/contracts/openapi/assistant-api.openapi.yaml`
13. `packages/contracts/schemas/reminders/*.json`
14. `services/assistant-api/assistant_api/models.py`
15. `services/assistant-api/assistant_api/store.py`
16. `services/assistant-api/assistant_api/app.py`
17. `services/assistant-api/assistant_api/worker.py`
18. `services/assistant-api/assistant_api/telegram_transport.py`

#### Current baseline to preserve

1. existing `GET|POST /v1/reminders` and `DELETE /v1/reminders/{reminder_id}` remain additive-only
2. existing one-shot reminder schedule/cancel flow keeps working
3. Telegram stays summary-safe and action-safe
4. existing runtime audit records remain readable

#### In scope

1. reminder follow-up contract/state shape
2. runtime/worker seam for snooze/reschedule/retry/dead-letter-ready lifecycle
3. targeted backend tests
4. minimal docs updates

#### Out of scope

1. broad planner UI redesign
2. live OIDC/Telegram validation
3. managed quickstart expansion
4. KG memory broker changes

#### Likely files touched

1. `packages/contracts/openapi/assistant-api.openapi.yaml`
2. `packages/contracts/schemas/reminders/**`
3. `services/assistant-api/assistant_api/models.py`
4. `services/assistant-api/assistant_api/store.py`
5. `services/assistant-api/assistant_api/app.py`
6. `services/assistant-api/assistant_api/worker.py`
7. possible new reminder follow-up focused tests

#### Exit gate

1. follow-up state is explicit and additive-only
2. one-shot reminder flow still passes
3. audit/runtime visibility remains intact
4. validation passes

#### Mandatory validation

1. `.agent-orchestrator/config.json` validation commands
2. targeted reminder follow-up lifecycle pytest

### `S29` Follow-Up Control-Plane / Operator Alignment

#### Main objective

Expose the `S28` follow-up policy state minimally through:

1. web control plane
2. operator-facing docs/runbook
3. browser/operator smoke

#### Why this is isolated

This is the consumption layer for the `S28` backend shape.

It should not redesign reminder UX more broadly than the new policy requires.

#### Read first

1. all `S28` handover artifacts
2. `apps/assistant-web/index.html`
3. `apps/assistant-web/app.js`
4. `apps/assistant-web/styles.css`
5. `apps/assistant-web/README.md`
6. `scripts/assistant/run_browser_smoke.py`
7. `scripts/assistant/run_operator_smoke.py`
8. `services/assistant-api/README.md`

#### Current baseline to preserve

1. existing reminder schedule/cancel flow remains valid
2. browser smoke still covers auth, Telegram, reminders, memory, and runtime ledger
3. Telegram remains scoped and summary-safe

#### In scope

1. minimal web control-plane alignment for follow-up state/actions
2. operator docs/runbook alignment
3. browser/operator smoke updates
4. docs refresh

#### Out of scope

1. broad planner redesign
2. managed quickstart live pass work
3. KG memory broker redesign

#### Likely files touched

1. `apps/assistant-web/index.html`
2. `apps/assistant-web/app.js`
3. `apps/assistant-web/styles.css`
4. `apps/assistant-web/README.md`
5. `scripts/assistant/run_browser_smoke.py`
6. `scripts/assistant/run_operator_smoke.py`
7. possible `ops/**` runbook updates

#### Exit gate

1. browser/operator smoke can observe the follow-up state/path
2. reminder shell behavior stays additive
3. Telegram boundaries remain intact
4. validation passes

#### Mandatory validation

1. `node --check apps/assistant-web/app.js`
2. `python3 scripts/assistant/run_browser_smoke.py`
3. `.agent-orchestrator/config.json` validation commands

### `S30` Reminder Policy Closeout

#### Main objective

Close the reminder-policy wave with refreshed evidence, validation, doc sync, and an explicit chain decision.

#### Why this is isolated

This should be a smoke/validation/doc-sync session only.

#### Read first

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/20_POST_S27_REMINDER_POLICY_ORCHESTRATION_PLAN.md`
7. `docs/session-ops/handovers/SESSION_28_HANDOVER.md`
8. `docs/session-ops/handovers/SESSION_29_HANDOVER.md`
9. `.agent-orchestrator/config.json`
10. reminder-policy smoke/validation entrypoints added in `S28` and `S29`

#### Current baseline to preserve

1. existing install/operator/browser evidence remains honest
2. follow-up policy artifacts reflect actual runtime behavior
3. blocker states are never hidden

#### In scope

1. rerun reminder-policy evidence and validation
2. sync canonical docs and root mirrors
3. write next prompt or stop marker

#### Out of scope

1. new feature redesign
2. broad bug hunt
3. unmanaged scope expansion

#### Exit gate

1. reminder-policy evidence artifacts are current
2. configured validation passes
3. canonical docs and root mirrors match the real result
4. chain decision is explicit

#### Mandatory validation

1. `.agent-orchestrator/config.json` validation commands
2. reminder-policy smoke entries added or updated in `S28` and `S29`

## 8. Orchestration Guide

Keep the chain paused until the user explicitly says this post-`S27` wave is now official.

### Activation steps

1. update `docs/session-ops/01_SESSION_BOARD.md` first
2. confirm `docs/session-ops/prompts/SESSION_28_PROMPT.md` is the active official prompt
3. mirror `docs/session-ops/prompts/SESSION_28_PROMPT.md` into `NEXT_SESSION_PROMPT.md`
4. then start the chain

### Recommended command

Background:

```bash
agent-orchestrator start --max-sessions 3
```

Foreground:

```bash
agent-orchestrator run
```

### Monitoring commands

```bash
agent-orchestrator status
```

```bash
ls -lt .agent-orchestrator/runtime/logs | head
```

```bash
tail -n 120 .agent-orchestrator/runtime/logs/<active-run>/runner.stderr.log
```

### Stall recovery rule

Treat the run as stalled if all of the following are true for several minutes:

1. `agent-orchestrator status` still says `running`
2. `runner.stderr.log` mtime stops advancing
3. the `codex exec` child is sleeping with near-zero CPU
4. no `last-message.txt` is produced

When that happens:

1. inspect the active run dir
2. stop the orchestrator
3. verify `NEXT_SESSION_PROMPT.md` still points at the intended active prompt
4. restart the orchestrator from the same prompt

### Stop rules

Stop the wave early if:

1. the policy requires a breaking public API change rather than additive-only evolution
2. the web/control-plane layer cannot stay scoped and additive
3. a required behavior depends on external env that is unavailable and no honest blocker path exists
4. validation fails and the narrow session cannot repair it without opening a broader redesign
