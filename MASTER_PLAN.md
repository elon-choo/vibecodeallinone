# Master Plan

이 파일은 `agent-orchestrator`가 읽는 루트 계획 미러다.
정본 계획은 `docs/session-ops/01_SESSION_BOARD.md`, `13_PRODUCT_REPLAN_MASTER.md`, `14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`, `15_EXECUTION_WAVES.md`다.

## Current State

- Current status: `post-S30 reminder-policy mini-wave complete / chain paused`
- Next official session: none (`NEXT_SESSION_PROMPT.md` currently contains `SESSION_CHAIN_PAUSE`)
- Stable entry prompt: `NEXT_SESSION_PROMPT.md` (`SESSION_CHAIN_PAUSE`)

## Latest Completed Wave

| Session | Theme | Exit Gate | Status |
|---|---|---|---|
| S15 | worker foundation | worker runtime, purge execution, reminder persistence skeleton | Done |
| S16 | Telegram transport foundation | polling runtime, secure link completion, transport validation | Done |
| S17 | Telegram quick capture + resume backend | real continuity runtime path, Telegram smoke alignment | Done |
| S18 | reminder backend + delivery | reminder API, worker delivery, audit trail, validation | Done |
| S19 | web control plane + browser smoke | reminder/runtime web alignment, browser evidence | Done |
| S20 | one-command self-host reference stack | stack orchestration, docs, validation | Done |
| S21 | closeout | final validation, evidence sync, stop-marker decision | Done |
| S22 | managed quickstart deployment contract | operator mode/readiness contract, docs/templates, validation | Done |
| S23 | managed quickstart operator/bootstrap path | generated operator artifacts, smoke alignment, runbook | Done |
| S24 | live provider + real Telegram operator validation | productized live validation path, blocker artifacts, targeted tests/docs | Done |
| S25 | KG memory broker foundation | additive broker seam, opt-in workspace state, workspace-scoped query/tests/docs | Done |
| S26 | broker opt-in + control-plane alignment | web-only broker control plane, browser smoke alignment, docs/handover sync | Done |
| S27 | later-wave closeout | refreshed later-wave evidence, validation, doc sync, stop-marker decision | Done |
| S28 | reminder follow-up policy contract | additive reminder follow-up contract/state, targeted backend tests/docs | Done |
| S29 | follow-up control-plane/operator alignment | minimal web/operator/smoke consumption of follow-up state | Done |
| S30 | reminder-policy closeout | refreshed reminder-policy evidence, validation, doc sync, stop-marker decision | Done |

## Orchestrator Rules

- Canonical session docs stay under `docs/session-ops/`.
- Every worker session must update both:
  - canonical session docs
  - root orchestrator mirrors (`HANDOVER.md`, `NEXT_SESSION_PROMPT.md`)
- If no further session is needed, write one of the configured stop markers into `NEXT_SESSION_PROMPT.md`.

## Replanning Rules

- S10 decisions are locked in the new canonical docs.
- unattended runs should use micro-session chaining, not a single broad implementation prompt.
- If the plan changes, update `docs/session-ops/01_SESSION_BOARD.md` first, then sync this mirror.

## Current Chain State

- The `S15 -> S21` wave, the `S22 -> S27` later wave, and the `S28 -> S30` reminder-policy mini-wave are complete.
- No numbered session is currently active.
- `docs/session-ops/prompts/SESSION_30_PROMPT.md` is the latest completed numbered prompt.
- `NEXT_SESSION_PROMPT.md` now contains `SESSION_CHAIN_PAUSE`.

## Wave Status

No numbered session is currently active.

- previous completed-wave orchestration: `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`
- previous completed-wave prompt pack: `docs/session-ops/17_NEXT_WAVE_PROMPT_PACK.md`
- later-wave orchestration plan: `docs/session-ops/18_POST_S21_LATER_WAVE_ORCHESTRATION_PLAN.md`
- later-wave prompt pack: `docs/session-ops/19_POST_S21_LATER_WAVE_PROMPT_PACK.md`
- latest completed prompt: `docs/session-ops/prompts/SESSION_30_PROMPT.md`
- current entrypoint: `NEXT_SESSION_PROMPT.md` (`SESSION_CHAIN_PAUSE`)
- latest reminder-policy orchestration plan: `docs/session-ops/20_POST_S27_REMINDER_POLICY_ORCHESTRATION_PLAN.md`
- latest reminder-policy prompt pack: `docs/session-ops/21_POST_S27_REMINDER_POLICY_PROMPT_PACK.md`

## Completed Later Wave

The `S22 -> S27` later wave and the scoped `S28 -> S30` reminder-policy mini-wave are complete.

- later-wave orchestration plan: `docs/session-ops/18_POST_S21_LATER_WAVE_ORCHESTRATION_PLAN.md`
- later-wave copy-paste prompt pack: `docs/session-ops/19_POST_S21_LATER_WAVE_PROMPT_PACK.md`

Prepared sequence:

| Session | Theme | Status |
|---|---|---|
| S22 | managed quickstart deployment contract | Done |
| S23 | managed quickstart operator/bootstrap path | Done |
| S24 | live provider + real Telegram operator validation | Done |
| S25 | KG memory broker foundation | Done |
| S26 | broker opt-in + control-plane alignment | Done |
| S27 | later-wave closeout | Done |

Execution rule:

- managed quickstart/live-ready productization first, KG memory broker second
- live validation is capability-gated and must emit blockers instead of fake success when env is absent
- KG memory broker must remain opt-in, workspace-scoped, and additive-only

Resume rule:

- create a new numbered prompt only after a single fully scoped next objective is ready
- keep `NEXT_SESSION_PROMPT.md` on a configured stop marker until that next objective exists
- once resumed, keep `NEXT_SESSION_PROMPT.md` aligned to the currently active numbered prompt
- do not widen the next chain beyond one narrow objective
