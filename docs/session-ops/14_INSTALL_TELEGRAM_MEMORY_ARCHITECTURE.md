# S10 Install Telegram Memory Architecture

## 1. Scope

This document defines four things together because they fail together in practice:

1. easy install
2. Telegram as a first-class surface
3. cross-surface continuity
4. memory and security architecture

## 2. Easy Install Strategy

### 2.1 Installation Tracks

| Track | Target User | Decision | Current Repo Basis | Notes |
|---|---|---|---|---|
| `Managed Quickstart` | non-developer end user | strategic default | not implemented yet | ideal entry path once hosted operations exist |
| `Self-host Reference Stack` | operator / OSS user | MVP build priority | `assistant-web`, `assistant-api`, contracts, smoke harness already exist | must become one-command and documented |
| `Power Pack Developer Install` | developer using skills/KG | keep separate | current `README.md` and `scripts/install.sh` already cover this | should not be confused with assistant-runtime install |

### 2.2 Install Principle

The product cannot rely on a single "install" sentence anymore. It needs distinct entry points:

1. `Try the assistant`
2. `Self-host the assistant`
3. `Install the power pack developer toolkit`

### 2.3 MVP Recommendation

Build the `Self-host Reference Stack` first because it is achievable from the current repo and can later back both demo and managed environments.

Minimum MVP stack:

- `assistant-api`
- `assistant-web`
- persistent database for auth/memory/checkpoint/job state
- Telegram bridge inside the existing runtime boundary
- documented environment bootstrap

## 3. Telegram First-Class Model

### 3.1 Product Role

Telegram is not the full workspace. It is the quick-action, notification, and re-entry layer.

### 3.2 Telegram Responsibilities

| Capability | Telegram Role | Web/PWA Role |
|---|---|---|
| quick capture | first-class | review and edit later |
| reminders / scheduled nudges | first-class | configure, audit, snooze policy |
| approvals / confirmations | first-class for lightweight approval | require web confirmation for sensitive actions |
| resume context | send re-entry links and summary | restore full checkpoint and memory context |
| long-form chat | limited | first-class |
| memory CRUD | limited to lightweight capture/archive | first-class full management |
| trust / evidence view | summary link only | full surface |

### 3.3 Linking Flows

#### Web-first link

1. user signs in on web/PWA
2. user chooses `Link Telegram`
3. runtime issues a short-lived linking token
4. user opens Telegram deep link or enters a code
5. Telegram surface binds to the existing user identity

#### Telegram-first entry

1. user starts the Telegram bot
2. bot provides a secure web completion link
3. user finishes auth/consent on web
4. runtime returns to Telegram with linked status and available actions

Sensitive setup should terminate on web, not inside Telegram.

## 4. Cross-Surface Continuity Model

### 4.1 Existing Reuse Base

Current repo already has the main continuity primitive:

- `session_checkpoint`
  - `conversation_id`
  - `last_message_id`
  - `draft_text`
  - `selected_memory_ids`
  - `route`
  - `version`

This should be preserved and extended, not replaced.

### 4.2 Continuity Planes

| Plane | Current Asset | Proposed Extension |
|---|---|---|
| identity | first-party `auth_session` in `assistant-api` | linked Telegram account and per-surface capability scope |
| work continuity | `session_checkpoint` | `surface`, `handoff_kind`, `resume_token_ref`, `last_surface_at` |
| memory selection | `selected_memory_ids` | surface-aware recall rules so only active memories can cross into Telegram summaries |
| delivery state | none | reminder/job receipt state and last notification outcome |

### 4.3 Surface Continuity Rules

1. web/PWA remains the canonical restore surface for full conversation state.
2. Telegram can initiate or resume lightweight actions, but full restore happens through the checkpoint-aware web/PWA shell.
3. any surface handoff must be auditable:
   - who
   - from which surface
   - to which surface
   - when
4. deleted or archived memories must never be reintroduced through handoff or notification payloads.

## 5. Memory Architecture Synthesis

### 5.1 Memory Layers

| Layer | Purpose | Current Repo Basis | S10 Decision |
|---|---|---|---|
| `Explicit User Memory` | preferences, profile, facts user wants retained | `memory_item`, `memory_source`, `memory_revision`, export/delete flows | keep explicit-save-first; candidates stay out of retrieval until approved |
| `Continuity Memory` | resume current work across surfaces | `session_checkpoint`, IndexedDB cache, conflict handling | extend for surface handoff, do not replace |
| `Workspace / Project Memory` | project-aware coding context | KG hybrid search, shared memory pool, conversation memory, graph search | expose through a brokered opt-in layer, not as always-on user chat dependency |
| `Automation Memory` | reminders, schedules, pending jobs, delivery receipts | delete/export queue tables show the first pattern | formalize into background job state and reminder history |

### 5.2 Memory Broker Decision

`assistant-api` should grow a `memory broker` role that decides which memory layers can be read or written for a given action.

MVP broker rules:

1. user chat uses explicit user memory and continuity memory
2. project/workspace memory is opt-in and workspace-scoped
3. automation memory is job-scoped and auditable
4. Telegram receives summarized or action-safe memory views, not unrestricted retrieval

### 5.3 Provenance And Consent Rules

1. every explicit memory keeps provenance
2. candidate memory never enters the active retrieval set without promotion
3. project/workspace memory must disclose its source workspace or graph scope
4. automation-generated memory must identify the job that produced it
5. export and delete must cover all user-controlled layers that store personal context

## 6. Assistant Convenience And Scheduled Automation

### MVP

- reminder creation and delivery
- lightweight Telegram quick capture
- resume links from Telegram to web/PWA
- purge/export jobs made real instead of queue-only placeholders

### V1

- recurring reminders
- Telegram approvals for low-risk actions
- workspace/project check-ins using KG-backed retrieval

### V2

- richer autonomous routines
- multi-project scheduling
- broader cross-surface assistant flows

## 7. Security Baseline

### 7.1 Secret Custody

1. provider tokens stay server-side only
2. Telegram bot tokens stay server-side only
3. browser and Telegram never receive long-lived provider secrets
4. local `.env` handling remains for self-host/operator installs only

### 7.2 Identity And Surface Scope

1. one human user identity can bind multiple surfaces
2. each surface gets a scoped capability profile
3. Telegram actions default to lower privilege than web/PWA
4. sensitive actions require web confirmation or a stronger trust path

### 7.3 Link And Handoff Safety

1. use short-lived signed linking or resume tokens
2. bind tokens to intended user and purpose
3. expire tokens aggressively
4. log surface handoffs for audit

### 7.4 Memory Safety

1. explicit memory control remains user-visible
2. deleted memories are excluded immediately from retrieval and notifications
3. exports should be time-limited and auditable
4. retention, purge, and reminder history need explicit operational policy

### 7.5 Background Job Safety

1. job execution must be per-user scoped
2. reminder or automation jobs must have clear ownership and cancellation paths
3. abuse protections and rate limits are required before Telegram-triggered automation expands
4. job outcomes must be logged for evidence and troubleshooting

## 8. Assumptions

1. Telegram can serve as a first-class messaging surface without becoming the full admin UI.
2. current `assistant-api` boundary is still the right place for link/account/job state in MVP.
3. PWA install remains the near-term PC/mobile answer.

## 9. Needed Inputs

1. exact Telegram bot constraints and desired command set
2. external `openclaw` reference material for convenience comparison
3. external `Jarvis` memory architecture material for convergence decisions
4. hosting decision for managed quickstart

## 10. Research Follow-up

1. choose the concrete job runner pattern for reminders, purge, and export delivery
2. define the precise Telegram abuse and moderation model
3. verify whether the current `OpenAI-first` login language is deployable as a public product promise
