# Claude Code Power Pack - External Review Prompt (Round 2)

> 대상 모델: Gemini 3.1 DeepThink
>
> 리뷰 목적: `S28 -> S29 -> S30` 결과가 correctness, safety, smoke integrity, release evidence 관점에서 얼마나 믿을 수 있는지 깊게 평가받는다.

---

## Prompt

```md
You are a reliability and validation auditor.

Audit the `S28 -> S29 -> S30` reminder-policy wave of `claude-code-power-pack`.

## What this wave changed

This wave added and closed out reminder follow-up policy hardening.

### Backend/runtime
- reminder create can now optionally accept `follow_up_policy`
- reminder records expose `follow_up_state`
- runtime jobs expose `available_at` and `attempt_count`
- retryable failures requeue the same auditable job
- terminal failures become explicit `dead_letter`
- backend seam exists for snooze/reschedule-ready state

### Web/operator
- web reminder form can configure retry policy
- reminder card / Telegram summary-safe card / runtime ledger render follow-up state
- operator smoke and browser smoke now explicitly observe this follow-up path

### Closeout
- operator smoke rerun
- browser smoke rerun
- configured validation rerun
- chain paused with `SESSION_CHAIN_PAUSE`

## Important constraints that must remain true

1. existing one-shot reminder schedule/cancel flow must not be broken
2. Telegram must remain action-safe / summary-safe
3. no fake success is allowed for live provider/live Telegram
4. no broad planner redesign should be hidden inside this wave
5. failure/retry/hold state must stay auditable

## Actual evidence state

### Operator smoke
- file: `artifacts/operator_smoke/assistant_api_operator_smoke.json`
- timestamp: `2026-03-12T08:27:49Z`
- mock smoke: `pass`
- live provider validation: `blocked`
- live Telegram validation: `blocked`

### Browser smoke
- file: `artifacts/browser_smoke/assistant_web_browser_smoke.json`
- timestamp: `2026-03-12T08:28:01Z`
- status: `pass`
- includes reminder follow-up policy surface checks

### e2e score
- file: `artifacts/e2e_score.json`
- timestamp: `2026-03-12T08:28:01Z`
- `20/20`

### Validation gate rerun
- `ruff check ...`
- `node --check apps/assistant-web/app.js`
- `python3 -m pytest tests/test_ralphloop_artifact_io.py tests/test_ralphloop_trust_bundle.py tests/test_assistant_api_runtime.py tests/test_assistant_api_worker.py tests/test_assistant_api_telegram.py -q`

All passed.

## Files to inspect

### Evidence / closeout
- `docs/session-ops/handovers/SESSION_30_HANDOVER.md`
- `docs/session-ops/handovers/SESSION_29_HANDOVER.md`
- `docs/session-ops/handovers/SESSION_28_HANDOVER.md`
- `docs/session-ops/01_SESSION_BOARD.md`
- `PROJECT_AUDIT.md`
- `MASTER_PLAN.md`
- `HANDOVER.md`

### Runtime
- `services/assistant-api/assistant_api/models.py`
- `services/assistant-api/assistant_api/store.py`
- `services/assistant-api/assistant_api/worker.py`
- `tests/test_assistant_api_runtime.py`
- `tests/test_assistant_api_worker.py`

### Web/smoke
- `apps/assistant-web/app.js`
- `apps/assistant-web/index.html`
- `apps/assistant-web/styles.css`
- `scripts/assistant/run_browser_smoke.py`
- `scripts/assistant/run_operator_smoke.py`

## Audit questions

1. Is the new follow-up policy path truly additive, or are there hidden behavior regressions?
2. Is the retry/dead-letter lifecycle sufficiently auditable?
3. Are smoke checks strong enough to justify the current evidence claims?
4. Is the explicit `blocked` handling for live provider/live Telegram honest and robust?
5. Did this wave preserve the promised Telegram safety boundary?
6. Are there gaps between what the docs claim and what the evidence actually proves?
7. Should the chain have paused here, or is one more mandatory closeout/fix session still needed?

## Required output

Return:

1. `Reliability score /100`
2. `Evidence trust score /100`
3. `Pass / Pass with reservations / Fail`
4. `Top 7 findings`, each with:
   - severity
   - affected file(s)
   - why it matters
   - recommended fix
5. `What evidence is strong`
6. `What evidence is still missing`
7. `Whether pausing the chain now is the correct decision`

Be strict. If an area is only indirectly tested, say so explicitly.
```

---

## Recommended Attachments

- `artifacts/operator_smoke/assistant_api_operator_smoke.json`
- `artifacts/browser_smoke/assistant_web_browser_smoke.json`
- `artifacts/e2e_score.json`
- `docs/session-ops/handovers/SESSION_30_HANDOVER.md`
- `services/assistant-api/assistant_api/store.py`
- `services/assistant-api/assistant_api/worker.py`
- `tests/test_assistant_api_runtime.py`
- `tests/test_assistant_api_worker.py`
- `scripts/assistant/run_browser_smoke.py`
- `scripts/assistant/run_operator_smoke.py`
