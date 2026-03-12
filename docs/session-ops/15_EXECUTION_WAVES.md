# S10 Execution Waves

## 1. Goal

Translate the S10 replan into implementation waves that respect current repo assets, avoid unnecessary rewrites, and keep install / Telegram / memory / security aligned.

## 2. Reuse Strategy Summary

| Area | Decision |
|---|---|
| `assistant-web` | extend, do not rewrite |
| `assistant-api` | extend, do not split into multiple runtime services in MVP |
| `packages/contracts` | extend with new surface/job schemas |
| `packages/evidence-contracts` | extend for new evidence flows |
| smoke harness | extend with install and Telegram validation |
| `kg-mcp-server` | keep as support plane and integrate through brokered opt-in paths |
| current `README.md` / install story | split into product install vs developer toolkit install |

## 3. Wave Definition

### MVP

#### Outcome

An open-source self-host reference stack that lets a user run the assistant, link Telegram, continue through web/PWA, and control explicit memory with security guardrails.

#### In Scope

1. one-command self-host reference install
2. `assistant-web` onboarding and install guidance refresh
3. Telegram account linking and webhook/action ingestion inside `assistant-api`
4. cross-surface continuity contract extensions built on `session_checkpoint`
5. explicit memory + checkpoint + basic reminder/job persistence
6. purge/export queues upgraded into real executable jobs
7. operator/browser smoke extended with install and Telegram mock evidence

#### Out Of Scope

1. managed hosted quickstart
2. native desktop/mobile wrappers
3. shared workspaces and team memory
4. always-on KG-backed project memory
5. unsupported `openclaw` / `Jarvis` parity claims

#### Exit Gate

1. fresh-machine self-host setup succeeds through documented steps
2. Telegram link flow can be exercised in a mock/testable path
3. web/PWA can restore continuity from a Telegram handoff
4. memory export/delete/reminder jobs are observable and auditable
5. release evidence includes install smoke, browser smoke, operator smoke, and Telegram mock smoke

### V1

#### Outcome

A broader product release that reduces install friction further and adds project-aware memory and richer Telegram workflows.

#### In Scope

1. managed quickstart or hosted reference environment
2. Telegram reminders, approvals, and status flows refined from MVP learnings
3. opt-in workspace/project memory broker backed by KG assets
4. clearer operator controls for consent, retention, and linked surfaces
5. stronger live-provider validation and release evidence coverage

#### Exit Gate

1. end-user can start from managed web or Telegram with minimal operator help
2. project/workspace memory is explicit, scoped, and auditable
3. Telegram action safety and abuse controls are validated in evidence

### V2

#### Outcome

A mature assistant platform with richer packaging, deeper automation, and broader collaboration features.

#### In Scope

1. native desktop/mobile packaging if still justified after PWA usage
2. richer automation and recurring workflows
3. shared/team memory models
4. operational scaling and compliance hardening

## 4. Recommended Unattended Micro-Session Sequence

The first implementation wave should be decomposed so the orchestrator can finish one narrow objective per session.

### S11

1. split install stories in docs and scripts
2. add an assistant-runtime bootstrap entry
3. update install smoke for that bootstrap path

### S12

1. define and implement new runtime contracts:
   - Telegram account/link state
   - surface handoff / continuity
   - reminder and job records
2. extend `assistant-api` storage and runtime skeleton for those contracts

### S13

1. extend `assistant-web` for Telegram link / continuity / job visibility
2. update browser smoke for the new surface state

### S14

1. add install/Telegram mock smoke completion
2. run targeted validation
3. sync docs, handover, and next-wave prompt

## 5. Repo Impact Map

| Path | MVP Impact | V1/V2 Follow-up |
|---|---|---|
| `README.md` | split product install vs developer toolkit install narrative | managed quickstart docs |
| `scripts/install.sh` | either scope to power-pack only or introduce explicit assistant-runtime mode | richer packaging/install UX |
| `apps/assistant-web` | Telegram linking, install guidance, handoff restore UI, reminder/job visibility | richer project memory UX |
| `services/assistant-api` | Telegram adapter state, reminder/job execution, continuity extensions, security policy enforcement | hosted/runtime scale hardening |
| `packages/contracts` | new Telegram/surface/job schemas and OpenAPI updates | broader collaboration/project schemas |
| `packages/evidence-contracts` | install/Telegram smoke evidence shapes | broader release/audit evidence |
| `scripts/assistant` | install smoke + Telegram mock smoke | live Telegram validation tooling |
| `kg-mcp-server` | brokered project memory interfaces only | deeper productized workspace memory |

## 6. Evidence And Test Gates

### MVP Gates

1. contract validation for new Telegram / continuity / job schemas
2. `assistant-api` runtime tests for link state, job state, and continuity rules
3. browser smoke for web/PWA flow
4. operator smoke for auth/memory/checkpoint/job flow
5. Telegram mock smoke for link, quick capture, and resume handoff
6. install smoke from a clean environment

### V1 Gates

1. live provider validation
2. managed deployment install/onboarding evidence
3. KG-backed memory opt-in evidence
4. Telegram abuse-control validation

## 7. Risks To Carry Forward

1. `openclaw` and `Jarvis` references remain under-specified locally
2. managed quickstart has no owner or implementation yet
3. Telegram operational details are still unknown
4. background job execution model is not selected yet
5. current install docs still describe the developer toolkit, not the assistant runtime

## 8. Assumptions

1. MVP should maximize reuse of the current repo rather than introduce a new repo split.
2. Telegram can live inside the existing runtime boundary through MVP.
3. PWA-first continuity is the right prerequisite before native packaging.
