# Ralph Loop v5 — External AI Review Prompts (Round 3)

> GPT Pro / Gemini Deep Think에 붙여넣을 리뷰 프롬프트 세트
>
> GitHub: https://github.com/elon-choo/vibecodeallinone
> Commit: `3f16719` (feat: Ralph Loop v5)

---

## 프롬프트 1/5: Architecture Review (GPT Pro)

```
You are a senior software architect reviewing an automated quality loop system called "Ralph Loop v5".

## Context
Ralph Loop is a self-improving code quality system for an MCP (Model Context Protocol) server.
It runs scan → review → fix → verify loops to reach a target quality score.

**Key architectural change (v4→v5):**
- v4: Python orchestrator calls `claude -p` CLI externally (7 AI reviews × $4-5/round, fresh context each)
- v5: Claude Code runs the loop internally (no external calls, persistent context, $0/round for reviews)

## Files to review

### 1. loop_runner.py (380 lines) — Integrated scan + score + action plan
- Loads gate scores, AI review scores, E2E scores, release scores from artifacts
- Builds prioritized action plan with specific fix suggestions
- Outputs JSON with total_score, breakdown, weakest_areas, estimated_gain

### 2. self_review.py (442 lines) — Self-review framework
- 7 perspectives with checklists (code_quality, security, testing, architecture, documentation, packaging, ux)
- Each checklist item has: id, check description, severity, how_to_verify
- Generates templates for Claude Code to fill, saves results as review JSON

### 3. run.py (498 lines) — Machine gates + scoring
- Stage 1: Machine Gates (G0-G8) — env, lint, forbidden scan, SDK deprecation, server dry-run
- Stage 2: AI Review — loads from artifacts/reviews/*.json (NEW: was hardcoded 0)
- Stage 3: E2E — loads from artifacts/e2e_score.json (NEW: was hardcoded 0)
- Stage 4: Release Gate — 10 checks (README, LICENSE, CHANGELOG, etc.)

### 4. t3_benchmark.py (423 lines) — Benchmark + E2E scoring
- 10 standard queries: vanilla grep vs KG hybrid search
- NEW: --e2e-score flag runs 4 checks (benchmark success, pytest, lint, smoke test)

## Review Focus
1. **Architecture**: Is the loop_runner → self_review → run.py → t3_benchmark pipeline well-designed?
2. **Scoring integrity**: Can the scoring system be gamed? Are there perverse incentives?
3. **Extensibility**: How easy is it to add new gates, perspectives, or E2E checks?
4. **Error handling**: What happens when individual components fail?
5. **Coupling**: Are the modules properly decoupled?

Rate each dimension 1-10 and provide specific improvement suggestions.
Output as JSON: {"dimensions": [{"name": "...", "score": N, "issues": [...], "suggestions": [...]}]}
```

---

## 프롬프트 2/5: Scoring Integrity Audit (Gemini Deep Think)

```
You are a quality assurance auditor. Analyze the scoring system of Ralph Loop v5 for integrity issues.

## Scoring System (100 points total)

| Stage | Points | Source |
|-------|--------|--------|
| Stage 1: Machine Gates | 30 | Automated: ruff lint, forbidden patterns, env check, server dry-run |
| Stage 2: AI Review | 30 | Self-review: 7 perspectives × 0-10 score, avg × 3 |
| Stage 3: E2E Validation | 20 | Automated: benchmark, pytest, lint, smoke test |
| Stage 4: Release Gate | 20 | File existence: README, LICENSE, CHANGELOG, etc. |

## AI Review Score Calculation
```python
avg = sum(perspective_scores) / 7  # 0-10 each
ai_score = round(avg * 3)          # 0-30 scale
# Cap: >=5 CRITICALs → max 15, >0 CRITICALs → max 20
```

## Potential Gaming Vectors
1. Self-review scores are self-assigned — what prevents inflation?
2. E2E checks: benchmark "success" gives 5 pts even with recall=0 (gives 3 pts)
3. Release gates check file existence, not content quality
4. Machine gates only check syntax errors (E9,F63,F7,F82), not style/complexity
5. CRITICAL cap relies on self-reported severity in review JSONs

## Questions
1. What are the top 3 gaming risks in this scoring system?
2. How would you redesign to prevent score inflation?
3. Is the 30/30/20/20 weight distribution appropriate?
4. Should self-review scores be validated by external reviewers?
5. What automated guardrails could replace the trust-based self-review?

Provide a structured audit report with risk ratings (Critical/High/Medium/Low) for each finding.
```

---

## 프롬프트 3/5: Code Quality Deep Dive (GPT Pro)

```
You are a Python code quality expert. Review these 4 files from Ralph Loop v5.

## File 1: loop_runner.py

Key concerns:
- load_gate_scores() imports from run.py at runtime (sys.path manipulation)
- load_ai_review_scores() reads all review JSONs, calculates avg with CRITICAL cap
- build_action_plan() combines all data sources into prioritized list
- estimate_gain() assumes 60% recovery of deficit, capped at 40

## File 2: self_review.py

Key concerns:
- PERSPECTIVES dict contains 7 × 5-6 checklist items as static data
- generate_review_template() outputs JSON for Claude Code to fill
- save_review() converts checklist results to standard review format
- Score calculation: (PASS + PARTIAL×0.5) / total × 10

## File 3: run.py (modified)

Key changes:
- NEW: load_e2e_score() reads artifacts/e2e_score.json
- NEW: load_ai_review_score() reads artifacts/reviews/*.json with CRITICAL cap
- calculate_score() now integrates all 4 stages (was 2 stages before)

## File 4: t3_benchmark.py (modified)

Key changes:
- NEW: check_benchmark_success(), check_pytest(), check_lint(), check_smoke_test()
- NEW: run_e2e_score() aggregates 4 checks into 0-20 score
- pytest path detection: tries tests/ then kg-mcp-server/tests/

## Review Questions
1. Are there any bugs or logic errors?
2. Are there import/dependency issues (circular imports, missing modules)?
3. Is error handling sufficient for production use?
4. Are there any security concerns (path traversal, injection, etc.)?
5. Code style: is it Pythonic and maintainable?

For each issue found, specify: file, line (approximate), severity, and fix suggestion.
Output as JSON array of issues.
```

---

## 프롬프트 4/5: Testing Strategy Review (Gemini Deep Think)

```
You are a test engineering lead. Ralph Loop v5 currently has:
- 58 tests passing, 2 skipped
- ~2% code coverage (5977 lines, 5855 uncovered)
- CI enforces --cov-fail-under=2 (just added)
- No integration tests for the loop itself

## Current Test Files (6)
- test_config.py — config defaults, env loading
- test_embedding_pipeline.py — embedding graceful degradation
- test_forbidden_scan.py — forbidden pattern detection
- test_server_core.py — server config (duplicates test_config.py)
- test_skill_frontmatter.py — SKILL.md YAML validation
- test_write_back.py — write_back module (3/4 skip if module missing)

## Untested Modules (30+)
- server.py (1100 lines) — tool dispatch, MCP handler
- hybrid_search.py — search pipeline
- graph_search.py — Neo4j graph queries
- feedback_loop.py — node weight updates
- All pipeline/* modules
- All dashboard/* modules
- All new Ralph Loop scripts (loop_runner, self_review, t3_benchmark)

## Questions
1. What's the optimal test strategy to go from 2% to 30% coverage with minimum effort?
2. Which 5 modules should be tested first for maximum risk reduction?
3. How should the Ralph Loop scripts themselves be tested?
4. Should self_review.py have tests that validate the checklist items programmatically?
5. What's a realistic --cov-fail-under target for the next milestone?

Provide a prioritized test plan with estimated effort (S/M/L) for each test file.
```

---

## 프롬프트 5/5: Loop Protocol Effectiveness (GPT Pro / Gemini)

```
You are a DevOps process consultant. Evaluate the Ralph Loop v5 protocol for effectiveness.

## The Protocol
```
while score < 90:
  1. SCAN: python3 loop_runner.py --rescan --run-e2e
  2. READ: Check weakest_areas from JSON output
  3. FIX: Edit code directly (Read → Edit → test)
  4. SELF-REVIEW: Fill checklist for modified perspective
  5. RE-SCAN: Verify score improvement
  6. COMMIT: Auto-commit if improved
  7. DECIDE: Continue, switch area, or stop (3 rounds no improvement)
```

## Cost Comparison
| Metric | v4 (External) | v5 (Native) |
|--------|---------------|-------------|
| Cost/round | $4-5 | $0 (self-review) |
| Context | Fresh each call | Persistent |
| Fix quality | Blind (no prior context) | Informed (sees all changes) |
| Timeout | 300s per call | No limit |
| E2E scoring | 0/20 (unimplemented) | 20/20 (now working) |

## Concerns
1. Self-review bias: Claude Code reviewing its own code
2. No external validation checkpoint
3. Score could plateau without genuine code improvement
4. RALPH_LOOP_PROMPT.md is instruction-only — no programmatic enforcement

## Questions
1. Is the v4→v5 transition a genuine improvement or just cheaper?
2. How to prevent "score farming" without actual quality improvement?
3. Should there be mandatory external review gates at certain thresholds (e.g., 80, 90)?
4. What metrics beyond the score would indicate real quality improvement?
5. How would you modify the protocol for a team of multiple AI agents?

Provide recommendations as a prioritized list with effort/impact ratings.
```

---

## 사용 방법

### GPT Pro (o3-pro-max)
1. 프롬프트 1, 3, 5를 순서대로 입력
2. 각 프롬프트 전에 GitHub에서 해당 파일 내용을 첨부:
   - `scripts/ralphloop/loop_runner.py`
   - `scripts/ralphloop/self_review.py`
   - `scripts/ralphloop/run.py`
   - `scripts/ralphloop/e2e/t3_benchmark.py`

### Gemini Deep Think (gemini-2.5-pro)
1. 프롬프트 2, 4를 순서대로 입력
2. GitHub 레포 URL 첨부: https://github.com/elon-choo/vibecodeallinone
3. "Analyze the scripts/ralphloop/ directory" 추가 지시

### 결과 수집
- 각 리뷰 결과를 `artifacts/reviews/external_round3_{perspective}.json` 에 저장
- loop_runner.py 재실행으로 점수 반영 확인
