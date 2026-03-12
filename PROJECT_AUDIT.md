# Project Audit

이 파일은 `agent-orchestrator`용 루트 진입점이다.
정본 문서는 `docs/session-ops/` 아래에 있고, 이 파일은 현재 상태를 빠르게 이어받기 위한 압축 미러다.

## Canonical Sources

- 상태판: `docs/session-ops/01_SESSION_BOARD.md`
- replan master: `docs/session-ops/13_PRODUCT_REPLAN_MASTER.md`
- install/Telegram/memory/security: `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
- execution waves: `docs/session-ops/15_EXECUTION_WAVES.md`
- prepared `S15`~`S21` orchestration: `docs/session-ops/16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`
- prepared `S15`~`S21` copy-paste prompts: `docs/session-ops/17_NEXT_WAVE_PROMPT_PACK.md`
- prepared later-wave orchestration: `docs/session-ops/18_POST_S21_LATER_WAVE_ORCHESTRATION_PLAN.md`
- prepared later-wave copy-paste prompts: `docs/session-ops/19_POST_S21_LATER_WAVE_PROMPT_PACK.md`
- prepared reminder-policy orchestration: `docs/session-ops/20_POST_S27_REMINDER_POLICY_ORCHESTRATION_PLAN.md`
- prepared reminder-policy copy-paste prompts: `docs/session-ops/21_POST_S27_REMINDER_POLICY_PROMPT_PACK.md`
- 최신 handover: `docs/session-ops/handovers/SESSION_30_HANDOVER.md`
- 최신 prompt: `docs/session-ops/prompts/SESSION_30_PROMPT.md`
- official next prompt: none (`NEXT_SESSION_PROMPT.md` currently contains `SESSION_CHAIN_PAUSE`)

## Snapshot

- Date: 2026-03-12
- Current status: `post-S30 reminder-policy mini-wave complete / chain paused`
- Current focus: keep the chain paused until a single post-wave objective is explicitly scoped; the current reminder-policy evidence/validation/doc closeout is complete and live pass remains external-env dependent

## What Already Exists

1. `assistant-web` / `assistant-api` bootstrap runtime with auth, memory, checkpoint, trust flows
2. `packages/contracts` and `packages/evidence-contracts`
3. provenance/export/delete/checkpoint conflict handling
4. operator/browser smoke and release evidence helpers
5. `KG MCP` assets that can be reused for workspace/project memory
6. S10 replan docs that lock product direction before new build waves
7. split install story in `README.md`
8. assistant runtime bootstrap entry at `scripts/assistant/bootstrap_runtime.sh` that now generates a reference-stack workspace
9. install smoke that now checks both developer install and real reference-stack start/stop behavior
10. public contracts + `assistant-api` foundation for Telegram link state, checkpoint continuity metadata, and auditable runtime jobs
11. `assistant-web` consumption of Telegram link state, checkpoint continuity metadata, and auditable jobs
12. browser smoke coverage for Telegram linking state, continuity render, and runtime job visibility
13. structured install smoke artifact generation via `scripts/assistant/run_install_smoke.py`
14. dedicated Telegram mock smoke artifact generation via `scripts/assistant/run_telegram_mock_smoke.py`
15. separate worker runtime entrypoint with claim/lease/update lifecycle
16. executable purge path for queued `memory_delete` jobs
17. reminder-delivery persistence foundation via durable runtime job + reminder tables
18. public reminder create/list/cancel contract and backend execution path
19. worker-driven Telegram reminder delivery with success/failure/cancel audit in `runtime_job` and `reminder_delivery`
20. polling-first Telegram transport runtime with secure token-based link completion and persisted polling cursor state
21. Telegram-originated resume-link and quick-capture continuity updates that now mutate the linked web/PWA checkpoint through the real runtime path
22. `assistant-web` control-plane reminder panel and Telegram reminder summary on top of the additive reminder contract
23. browser smoke coverage for reminder schedule/cancel plus runtime ledger visibility on the web shell
24. one-command self-host reference stack launcher with `start|stop|restart|status|logs`
25. operator-facing self-host docs aligned to the same API/web/worker/Telegram story
26. refreshed `S21` evidence artifacts for install, Telegram, operator, browser, and `e2e_score`
27. additive operator-mode/readiness contract on top of the same reference stack runtime surface
28. managed quickstart env/secret contract helper in `scripts/assistant/deployment_contract.py`
29. managed quickstart operator workspace generator in `scripts/assistant/bootstrap_managed_quickstart.sh`
30. placeholder-aware managed readiness blockers on the shared runtime status surface
31. install smoke that now proves both self-host start/stop and managed quickstart operator artifact/status generation
32. operator-facing managed quickstart docs, runbook, and env template under `ops/managed/`
33. capability-gated live provider/live Telegram validation helpers in `scripts/assistant/smoke_support.py`
34. operator smoke that now records live provider/live Telegram preflight plus `blocked|manual-step-required|pass|fail` status alongside the existing mock smoke
35. dedicated real Telegram operator validation entry at `scripts/assistant/run_telegram_live_validation.py`
36. explicit blocker artifacts for live validation under `artifacts/operator_smoke/` and `artifacts/telegram_smoke/`
37. additive-only workspace/project memory broker foundation in `assistant-api` with optional provider seam, consent/audit metadata, and workspace-scoped query routes
38. contract/schema/runtime test coverage for the broker foundation, including default disabled-provider behavior and no-raw-Telegram retrieval guardrails
39. `assistant-web` control-plane exposure for broker opt-in/control state with web-only scope/probe UI on top of the `S25` backend shape
40. browser smoke coverage for broker opt-in/control plus disabled-provider audit render while Telegram keeps the summary-safe boundary copy
41. refreshed later-wave closeout evidence artifacts for install, operator, live Telegram validation, browser smoke, browser screenshot, and `e2e_score`
42. configured validation plus later-wave targeted checks re-run successfully in `S27`
43. explicit live-validation blocker artifacts remain authoritative when managed OIDC/Telegram env is absent
44. reminder-policy activation/closeout docs now exist across `docs/session-ops/prompts/SESSION_28_PROMPT.md`~`SESSION_30_PROMPT.md`, and the root entrypoint has been returned to `SESSION_CHAIN_PAUSE` after `S30`
45. additive reminder follow-up policy/state, retry/dead-letter runtime seam, and snooze/reschedule-ready store seam are now landed on top of the existing reminder lifecycle
46. `assistant-web` now minimally consumes follow-up policy/state with retry-policy form inputs, follow-up summary/ledger visibility, updated browser smoke, updated operator smoke, and aligned operator docs while Telegram stays summary-safe/action-safe
47. refreshed `S30` reminder-policy closeout artifacts now cover operator smoke, browser smoke, browser screenshot, and `e2e_score`, with configured validation rerun against the same state

## What Is Still Missing Relative To The New Plan

1. no single post-`S30` numbered objective is scoped yet, so the chain is intentionally paused on `SESSION_CHAIN_PAUSE`
2. recurring reminder productization, public snooze/reschedule admin routes, and broader planner UX remain deferred beyond this mini-wave
3. live pass evidence for provider/Telegram remains external-env dependent, but the blocker/attempt path is now productized

## Recommended Next Step

- Do not resume the chain until a single post-reminder-policy objective is explicitly scoped.
- Keep `NEXT_SESSION_PROMPT.md` on `SESSION_CHAIN_PAUSE` until that objective is ready.
- When resuming, keep the next wave narrow and avoid mixing managed quickstart/live validation, KG memory broker redesign, and broad reminder planner UX into one session.
