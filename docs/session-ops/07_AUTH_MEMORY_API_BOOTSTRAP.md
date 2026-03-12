# S04 Auth Memory API Bootstrap

## 1. Purpose

This document translates the S02 runtime boundary and the S03 trust contract into a contract-first bootstrap that `assistant-api` can implement without reopening the architecture.

The goal of S04 is not a full production backend. The goal is to freeze:

1. the public request/response contracts,
2. the evidence lookup boundary,
3. the minimum bootstrap responsibilities for auth, memory, checkpoint, and trust reads.

## 2. What Landed in S04

The following bootstrap artifacts are now the source of truth:

| Path | Role |
|---|---|
| `packages/contracts/openapi/assistant-api.openapi.yaml` | Route-level draft for `assistant-api` |
| `packages/contracts/schemas/auth/*` | OpenAI-first auth start + first-party session contract |
| `packages/contracts/schemas/memory/*` | Memory item, revision, provenance contracts |
| `packages/contracts/schemas/checkpoint/*` | Cross-device checkpoint contract |
| `packages/contracts/schemas/evidence/*` | Public trust lookup payloads |
| `packages/evidence-contracts/schemas/*` | Ralph Loop trust-plane artifact contracts |
| `services/assistant-api/README.md` | Runtime bootstrap boundary |

This keeps the package split from S02:

- `packages/contracts`: user runtime contracts
- `packages/evidence-contracts`: trust-plane artifact contracts
- `services/assistant-api`: runtime implementation boundary

## 3. Runtime Contract Rules

### 3.1 Auth

The auth bootstrap stays `OpenAI-first provider adapter + assistant-api owned session`.

Locked rules:

1. browser never receives provider token material,
2. provider subject and scopes are stored behind a first-party session,
3. `assistant-web` only depends on `auth/openai/start` and `auth/session`.

Current bootstrap endpoints:

- `POST /v1/auth/openai/start`
- `GET /v1/auth/session`

The current session payload includes:

- internal `user_id`
- `device_session_id`
- auth state (`pending_consent`, `active`, `reauth_required`)
- provider identity metadata
- first-party session lifetime
- memory control flags

### 3.2 Memory

Memory stays a user-controlled system, not an opaque model cache.

Locked entities:

- `memory_item`
- `memory_revision`
- `memory_source`

Bootstrap rules:

1. MVP default remains explicit save,
2. `candidate` memory is excluded from retrieval until promoted,
3. every memory item can point back to provenance,
4. delete removes the item from retrieval immediately even if purge is deferred.

Current bootstrap endpoints:

- `GET /v1/memory/items`
- `POST /v1/memory/items`
- `PATCH /v1/memory/items/{memoryId}`
- `DELETE /v1/memory/items/{memoryId}`

## 4. Checkpoint Bootstrap

`session_checkpoint` remains the minimum cross-device resume unit.

Locked fields:

- `conversation_id`
- `last_message_id`
- `draft_text`
- `selected_memory_ids`
- `route`
- `device_session_id`
- `updated_at`
- `version`

Bootstrap endpoints:

- `GET /v1/checkpoints/current`
- `PUT /v1/checkpoints/current`

Conflict handling stays `last_write_wins` at the checkpoint level, with versioned memory writes handled separately.

## 5. Trust Read Bootstrap

The trust read path is now fixed:

`app_version -> evidence_ref -> bundle_id -> evidence_summary`

`assistant-api` responsibilities:

1. map deployed `app_version` to `evidence_ref`,
2. resolve the public `evidence_summary`,
3. return user-facing trust labels and links,
4. never expose raw internal artifacts through user routes.

Bootstrap endpoints:

- `GET /v1/trust/current`
- `GET /v1/trust/bundles/{bundleId}`

The public response deliberately depends on `packages/evidence-contracts` instead of duplicating Ralph Loop payloads inside `assistant-api`.

## 6. Ralph Loop Hardening Hook

S04 also starts the trust-plane hardening work that S03 requested.

What landed now:

1. `self_review.py` no longer trusts a manual top-level `score`; it computes `computed_score` from checklist status.
2. Ralph Loop artifact writes now go through an atomic write helper.
3. review loaders in `run.py` and `loop_runner.py` prefer `computed_score` and only fall back to legacy `score`.
4. shared artifact helpers now include hashing and latest bundle resolution primitives.

What is still pending:

1. bundle manifest/history publication for every stage,
2. stage-wide `bundle_id` propagation,
3. semantic release readiness validation,
4. assistant-api runtime implementation and storage adapters.

## 7. Implementation Order After S04

### P0 next

1. add `assistant-api` runtime skeleton and session middleware,
2. add storage tables/migrations for `user`, `auth_account`, `device_session`, `memory_*`, `session_checkpoint`, `evidence_ref`,
3. add trust lookup implementation that reads `latest bundle` or explicit `evidence_ref`,
4. add manifest/history write path in Ralph Loop.

### P1 next

1. wire auth callback and device session issuance,
2. add memory CRUD handlers with provenance and revision writes,
3. add checkpoint sync handler,
4. add bundle invalid/stale checks before trust responses are served.

## 8. Decision Summary

S04 locks one important boundary:

- user runtime reads stable contracts from `packages/contracts`,
- Ralph Loop publishes stable trust artifacts from `packages/evidence-contracts`,
- `assistant-api` is the only runtime bridge between them.
