# Assistant API Contracts

This package is the contract-first source of truth for the user runtime.

Scope:
- Auth bootstrap for `assistant-web -> assistant-api -> provider adapter`
- Auth callback redirect that returns control to `assistant-web`
- Memory CRUD payloads and provenance records
- Cross-surface `session_checkpoint` sync and continuity metadata
- Telegram companion link state
- Auditable runtime job records
- Trust read contracts that resolve `app_version -> bundle_id -> evidence_summary`

Layout:
- `openapi/assistant-api.openapi.yaml`: route-level contract draft
- `schemas/auth/*`: auth/session requests and responses
- `schemas/memory/*`: memory entities, provenance, export, and delete receipt records
- `schemas/checkpoint/*`: checkpoint read/write payloads and conflict responses
- `schemas/telegram/*`: Telegram link state
- `schemas/jobs/*`: auditable runtime jobs
- `schemas/evidence/*`: public trust lookup payloads

Non-goals:
- Raw Ralph Loop artifacts
- Internal operator-only evidence fields
- Database migrations or ORM models
