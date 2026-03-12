# S10 Product Replan Master

## 1. Why This Replan Exists

`S01~S09` produced a usable bootstrap: `assistant-web`, `assistant-api`, runtime contracts, trust evidence lookup, provenance/export/delete, and repeatable smoke. What it did not lock was the product shape the user now wants:

- easy install for non-developers
- Telegram as a first-class surface
- one assistant experience across web / PC / mobile / Telegram
- a memory strategy that combines current explicit memory/checkpoint assets with KG-backed project intelligence
- security as a design baseline, not a postscript

This document replaces the old "web/PWA bootstrap only" framing with a broader product model while keeping current repo assets reusable.

## 2. North Star

Build an open-source assistant that a non-developer vibe-coder can start quickly from web or Telegram, continue across devices without losing context, and trust because memory is explicit, inspectable, exportable, deletable, and backed by visible release evidence.

## 3. Primary User And JTBD

### Primary User

`non-developer vibe-coder / solo operator`

- wants help across coding, project execution, reminders, and context recall
- is comfortable with chat surfaces but not with complex local setup
- needs quick capture in messaging and deeper control in a richer UI

### Secondary Users

- `developer + non-developer mixed team` that wants the same assistant with better memory controls
- `power user/operator` who self-hosts and wants evidence-backed behavior plus project-aware memory

### Core JTBD

1. Start the assistant without a long local setup.
2. Capture or resume work from Telegram when away from the main workspace.
3. Switch to web or installed PWA for memory control, longer conversations, settings, and trust review.
4. Keep user memory, current work continuity, and project context separate but coordinated.
5. Retain control over exports, deletion, retention, and assistant-triggered automation.

## 4. Product Thesis

### 4.1 Surface Thesis

- `assistant-web` stays the control plane.
- Telegram becomes the fast-action surface for capture, reminders, approvals, alerts, and handoff links.
- PC and mobile are the same `assistant-web` product through PWA install first.
- Separate native desktop/mobile wrappers are deferred until continuity and onboarding are proven.

### 4.2 Runtime Thesis

- `assistant-api` remains the single runtime backend and identity/session broker.
- `packages/contracts` remains the source of truth for public runtime contracts.
- `packages/evidence-contracts` remains the source of truth for release evidence payloads.
- `KG MCP` remains an intelligence/memory augmentation plane, not a mandatory user-request path in MVP.
- `Ralph Loop` remains a trust/evidence plane, not the end-user product itself.

### 4.3 Convenience Thesis

The user-requested `openclaw` reference is treated as a capability direction, not a copied specification. In this plan it translates into three product buckets:

1. assistant convenience
2. memory convenience
3. scheduled automation convenience

Exact feature parity is intentionally not claimed because no local `openclaw` source of truth was found in this repo.

## 5. Reuse-First Repo Assessment

| Asset | Verdict | Why It Matters In The Replan |
|---|---|---|
| `apps/assistant-web` | Reuse and extend | Already provides PWA/mobile-first shell, auth round trip, memory CRUD, provenance render, checkpoint conflict UX, trust surface |
| `services/assistant-api` | Reuse and extend | Already owns auth/session/memory/checkpoint/trust runtime boundary; best place to add Telegram linking, job scheduling, and continuity APIs |
| `packages/contracts` | Reuse and extend | Already defines auth/memory/checkpoint/trust contracts; should expand to Telegram account, reminder/job, and cross-surface handoff schemas |
| `packages/evidence-contracts` | Reuse | Already holds public trust payload shape; should extend to install and Telegram smoke evidence, not be replaced |
| `scripts/assistant/*` smoke harness | Reuse and extend | Already gives repeatable operator/browser validation; should add install smoke and Telegram mock smoke |
| `kg-mcp-server` | Reuse as support plane | Already contains search, shared memory, session memory, and project intelligence primitives useful for project/workspace memory |
| current root `README.md` + `scripts/install.sh` | Rework | Current story is for the power-pack skill installer, not the assistant runtime product install story the user now wants |

## 6. Surface Model

| Surface | Primary Role | Must Support | Must Not Own |
|---|---|---|---|
| `Web/PWA` | control plane | onboarding, auth completion, long-form chat, memory CRUD, exports, trust, settings, Telegram linking | provider secrets, Telegram bot secret management, raw evidence internals |
| `Telegram` | fast-action surface | quick capture, reminders, approvals, alerts, resume links, short replies | privileged settings changes without confirmation, full memory administration, raw secret entry |
| `PC` | installed PWA form factor | same as web with faster re-entry | separate desktop-only product logic in MVP |
| `Mobile` | browser/PWA form factor | same as web with compact UI and resume continuity | separate native app in MVP |

## 7. Install And Distribution Principles

### 7.1 Split The Stories

The repo now has two distinct install stories and they must stop being mixed together:

1. `Power Pack / KG install`
   - for developer productivity features already described in `README.md`
2. `Assistant runtime install`
   - for the end-user assistant product (`assistant-web` + `assistant-api` + memory + Telegram bridge)

### 7.2 Recommended Default Story

- fastest product experience: `managed quickstart + optional Telegram connect + PWA install`
- fastest buildable open-source experience from current assets: `one-command self-host reference stack`

Because the managed path does not exist in the repo yet, MVP implementation should prioritize the self-host reference stack while documenting the managed path as the long-term default for non-developers.

## 8. What Is Explicitly Deferred

1. native desktop or native mobile clients before PWA continuity is proven
2. team/shared workspace memory before single-user memory and Telegram continuity stabilize
3. "always-on KG in every user chat" before explicit opt-in project memory exists
4. unsupported parity claims against `openclaw`
5. unsupported architectural claims about `Jarvis` internals

## 9. Planning Decisions Locked In S10

1. `assistant-web` is the control plane across desktop and mobile.
2. Telegram is a first-class companion and re-entry surface, not an afterthought.
3. `assistant-api` remains the single runtime backend and identity/session broker.
4. Current runtime contracts, evidence contracts, smoke harness, and KG assets are reuse-first.
5. The install strategy is dual-track: managed quickstart target, self-host reference MVP priority.
6. The memory strategy must separate explicit user memory, continuity memory, project/workspace memory, and automation memory.
7. Security and retention controls are product requirements for every surface, including Telegram and background jobs.

## 10. Assumptions

1. `openclaw` is treated as a reference for convenience expectations, not as a locally verified feature spec.
2. `Jarvis + Knowledge Graph` is treated as a direction toward project-aware memory and orchestration, not as a locally verified storage design.
3. Telegram will require a secure account-linking step with web confirmation for sensitive actions.
4. PWA install is the near-term PC/mobile packaging path because this repo already has that foundation.

## 11. Needed Inputs

1. the actual `openclaw` repo or design docs for memory / assistant / cron convenience comparison
2. the actual `Jarvis` memory architecture docs, schemas, or repos
3. Telegram operating constraints:
   - deployment environment
   - allowed bot scopes/commands
   - whether group chats are in scope
4. decision owner for managed quickstart / hosted deployment
5. confirmation that `OpenAI-first` remains the provider strategy for the user-facing assistant runtime

## 12. Research Follow-up

1. verify live provider/auth constraints before promising `GPT OAuth` as the final public language
2. validate Telegram bot operational model and abuse controls before implementation
3. choose the MVP background job execution model:
   - in-process worker
   - separate worker entrypoint
   - external queue later
4. define how KG-backed project memory is enabled per workspace without making KG a hard dependency for all users
