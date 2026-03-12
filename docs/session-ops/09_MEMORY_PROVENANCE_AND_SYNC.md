# S07 Memory Provenance And Sync

## 1. What Changed

S07 closes the three remaining bootstrap gaps from S06:

1. `memory_source` now participates in real runtime write/read paths.
2. memory export/delete controls now reach an actual runtime handler or queue entry.
3. `assistant-web` no longer treats IndexedDB and server checkpoint state as the same thing.

## 2. Provenance Surface

### Runtime contract

- `POST /v1/memory/items` accepts `sources[]`.
- `GET /v1/memory/items` returns `sources[]` on every memory item.
- `POST /v1/memory/exports` returns each memory item together with provenance and revision history.

### Storage behavior

- `assistant-api` writes `memory_item`, `memory_source`, and `memory_revision` in the same SQLite transaction.
- the shell writes a provenance record for explicit manual saves using the current checkpoint context:
  - `conversation_id`
  - optional `message_id`
  - operator-readable `note`
  - `captured_at`
- provenance is rendered in the shell under each memory card instead of being hidden in storage only.

## 3. Export And Delete Control

### Export

- `POST /v1/memory/exports` creates a JSON export bundle with:
  - memory item payload
  - provenance (`memory_source`)
  - revision history (`memory_revision`)
- the runtime persists an internal artifact under `artifacts/memory_exports/` and stores job metadata in `memory_export_job`.
- the shell downloads the returned bundle using the API-provided `suggested_filename`.
- internal artifact paths are not exposed to the browser response.

### Delete

- `DELETE /v1/memory/items/{memoryId}` now returns a `202 Accepted` receipt instead of a silent `204`.
- the runtime immediately marks the memory item as `deleted`, writes a revision entry, and queues a purge follow-up in `memory_delete_job`.
- the shell shows the pending purge timestamp so delete is user-visible, not just database-visible.

## 4. Checkpoint Conflict Hardening

### Runtime rule

- `PUT /v1/checkpoints/current` now accepts:
  - `base_version`
  - `force`
- if the server already has a newer checkpoint version and `force=false`, the API returns `409 checkpoint_conflict` with both:
  - `server_checkpoint`
  - `client_checkpoint`
- selected memory ids are filtered server-side to `active` memories only, so deleted or archived items cannot quietly re-enter the resume set.

### Shell UX

- IndexedDB now stores a local checkpoint envelope:
  - `checkpoint`
  - `dirty`
  - `cached_at`
- the shell tracks:
  - latest server checkpoint
  - local editable draft
  - dirty state
  - pending conflict
- when a conflict appears, the user gets two explicit paths:
  - `Use Server Copy`
  - `Keep Local Draft`

## 5. Live Provider Validation Checklist

Live OIDC validation was not executed in S07 because this session did not have a real provider credential set.

The minimum checklist for the next live validation pass is:

1. set `ASSISTANT_API_PROVIDER_MODE=oidc`
2. set `ASSISTANT_API_PUBLIC_BASE_URL` to the externally reachable API origin
3. register `${ASSISTANT_API_PUBLIC_BASE_URL}/v1/auth/openai/callback` as the provider callback URL
4. set `ASSISTANT_API_WEB_ALLOWED_ORIGINS` to the exact shell origin that will send credentialed requests
5. use HTTPS and `ASSISTANT_API_SECURE_COOKIES=true` outside localhost
6. provide:
   - `ASSISTANT_API_PROVIDER_CLIENT_ID`
   - optional `ASSISTANT_API_PROVIDER_CLIENT_SECRET`
   - `ASSISTANT_API_PROVIDER_AUTH_URL`
   - `ASSISTANT_API_PROVIDER_TOKEN_URL`
   - `ASSISTANT_API_PROVIDER_USERINFO_URL`
7. verify the provider returns a stable subject claim through `id_token` or `userinfo`
8. manually test:
   - sign-in success
   - sign-in denial
   - callback expiry or invalid `state`
   - token exchange failure path

## 6. Remaining Gaps

1. repeatable browser smoke는 추가됐지만, real OpenAI-compatible credential validation은 아직 checklist/preflight + mock smoke 단계다.
2. export retention and actual purge execution are bootstrap tables, not background workers yet
