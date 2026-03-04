#!/usr/bin/env python3
"""
Ralph Loop Orchestrator v4
===========================
Each phase runs as an independent `claude` CLI call → automatic fresh context.
The orchestrator manages the loop: scan → fix → verify → repeat.

Usage:
  python scripts/ralphloop/orchestrator.py [options]

Options:
  --max-rounds N       Maximum fix rounds (default: 5)
  --stop-score N       Stop when score >= N (default: 90)
  --model MODEL        Claude model to use (default: sonnet)
  --dry-run            Show what would be done without calling claude
  --auto-commit        Auto commit+push after each successful fix round
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Constants ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
ORCHESTRATOR_LOG = ARTIFACTS_DIR / "orchestrator_log.json"
RUN_PY = REPO_ROOT / "scripts" / "ralphloop" / "run.py"

CLAUDE_BIN = shutil.which("claude") or "claude"
ALLOWED_TOOLS = "Bash,Read,Write,Edit,Glob,Grep"


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "ℹ", "OK": "✓", "FAIL": "✗", "WARN": "⚠", "RUN": "▶"}
    print(f"  [{ts}] {icon.get(level, '·')} {msg}", file=sys.stderr)


# ── Phase 1: Machine Scan ──────────────────────────────────

def run_machine_scan() -> dict:
    """Run run.py --json and return parsed results."""
    log("Running machine scan (run.py)...", "RUN")
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "--review-mode", "off", "--json"],
        capture_output=True, text=True, timeout=120, cwd=str(REPO_ROOT),
    )

    # run.py outputs JSON to stdout, logs to stderr
    if result.stdout.strip():
        try:
            data = json.loads(result.stdout.strip())
            score = data.get("score", {})
            log(f"Score: {score.get('total', '?')}/100  "
                f"(S1={score.get('stage1_gates','?')}/30  "
                f"S4={score.get('stage4_release','?')}/20)", "OK")
            return data
        except json.JSONDecodeError:
            log(f"Failed to parse run.py JSON output", "FAIL")

    # Fallback: read from artifacts
    gates_file = ARTIFACTS_DIR / "gates.json"
    if gates_file.exists():
        gates = json.loads(gates_file.read_text())
        return {"gates": gates, "release": [], "score": {"total": 0}}

    return {"gates": [], "release": [], "score": {"total": 0}}


# ── Phase 2: Generate Fix Prompts ──────────────────────────

def generate_fix_prompts(scan: dict) -> list:
    """Analyze scan results and generate focused fix prompts."""
    prompts = []

    # Failed gates → fix prompts
    for gate in scan.get("gates", []):
        if gate["status"] == "FAIL":
            issues_text = "\n".join(
                f"  - {i}" if isinstance(i, str) else f"  - [{i.get('severity','?')}] {i.get('file','')}: {i.get('pattern','')}"
                for i in gate.get("issues", [])[:10]
            )
            prompts.append({
                "id": f"fix_{gate['gate']}",
                "priority": 0 if gate["severity"] == "CRITICAL" else 1,
                "prompt": (
                    f"Fix the {gate['gate']} gate failure in the vibecodeallinone project.\n\n"
                    f"Gate: {gate['gate']}\n"
                    f"Severity: {gate['severity']}\n"
                    f"Issues:\n{issues_text}\n\n"
                    f"Project root: {REPO_ROOT}\n"
                    f"Fix these issues. Do NOT create new files unless absolutely necessary. "
                    f"After fixing, verify by running: ruff check --select E9,F63,F7,F82 kg-mcp-server/ hooks/"
                ),
            })

    # Failed release checks → fix prompts
    for check in scan.get("release", []):
        if check["status"] == "FAIL":
            prompts.append({
                "id": f"fix_{check['id']}",
                "priority": 2,
                "prompt": (
                    f"Fix the release gate '{check['id']}' for vibecodeallinone.\n\n"
                    f"Check: {check['id']}\n"
                    f"Hint: {check.get('hint', '')}\n\n"
                    f"Project root: {REPO_ROOT}\n"
                    f"Create or update the necessary file to make this check pass."
                ),
            })

    # Sort by priority
    prompts.sort(key=lambda p: p["priority"])
    return prompts


# ── Phase 2.5: AI Review via Claude CLI ───────────────────

AI_REVIEW_PERSPECTIVES = [
    {
        "id": "review_code_quality",
        "name": "Code Quality",
        "prompt": (
            "Review the kg-mcp-server codebase for code quality.\n"
            "Focus on: error handling, type safety, edge cases, resource cleanup.\n"
            "Read the key files: kg-mcp-server/mcp_server/server.py, config.py, "
            "pipeline/hybrid_search.py, pipeline/write_back.py\n\n"
            "Output a JSON object with this exact structure:\n"
            '{{"perspective": "code_quality", "score": <0-10>, '
            '"issues": [{{"severity": "CRITICAL|HIGH|MEDIUM|LOW", "file": "path", "description": "..."}}], '
            '"summary": "one paragraph"}}\n\n'
            "Only output the JSON, nothing else."
        ),
    },
    {
        "id": "review_security",
        "name": "Security",
        "prompt": (
            "Security review of the kg-mcp-server codebase.\n"
            "Check for: hardcoded secrets, injection risks, unsafe deserialization, "
            "missing input validation, insecure defaults.\n"
            "Read the key files in kg-mcp-server/mcp_server/\n\n"
            "Output a JSON object with this exact structure:\n"
            '{{"perspective": "security", "score": <0-10>, '
            '"issues": [{{"severity": "CRITICAL|HIGH|MEDIUM|LOW", "file": "path", "description": "..."}}], '
            '"summary": "one paragraph"}}\n\n'
            "Only output the JSON, nothing else."
        ),
    },
    {
        "id": "review_architecture",
        "name": "Architecture",
        "prompt": (
            "Architecture review of the kg-mcp-server codebase.\n"
            "Focus on: module separation, dependency direction, extensibility, "
            "pipeline design, config management.\n"
            "Read the directory structure and key files.\n\n"
            "Output a JSON object with this exact structure:\n"
            '{{"perspective": "architecture", "score": <0-10>, '
            '"issues": [{{"severity": "CRITICAL|HIGH|MEDIUM|LOW", "file": "path", "description": "..."}}], '
            '"summary": "one paragraph"}}\n\n'
            "Only output the JSON, nothing else."
        ),
    },
    {
        "id": "review_documentation",
        "name": "Documentation",
        "prompt": (
            "Documentation review of the vibecodeallinone project.\n"
            "Check: README quality, inline docs, API documentation, "
            "CONTRIBUTING guide, CHANGELOG, install instructions.\n"
            "Read: README.md, CONTRIBUTING.md, CHANGELOG.md, SECURITY.md\n\n"
            "Output a JSON object with this exact structure:\n"
            '{{"perspective": "documentation", "score": <0-10>, '
            '"issues": [{{"severity": "CRITICAL|HIGH|MEDIUM|LOW", "file": "path", "description": "..."}}], '
            '"summary": "one paragraph"}}\n\n'
            "Only output the JSON, nothing else."
        ),
    },
    {
        "id": "review_testing",
        "name": "Testing",
        "prompt": (
            "Testing review of the vibecodeallinone project.\n"
            "Check: test coverage, test quality, edge case coverage, "
            "CI pipeline, test isolation.\n"
            "Read: tests/ directory, .github/workflows/, scripts/ralphloop/\n\n"
            "Output a JSON object with this exact structure:\n"
            '{{"perspective": "testing", "score": <0-10>, '
            '"issues": [{{"severity": "CRITICAL|HIGH|MEDIUM|LOW", "file": "path", "description": "..."}}], '
            '"summary": "one paragraph"}}\n\n'
            "Only output the JSON, nothing else."
        ),
    },
    {
        "id": "review_packaging",
        "name": "Packaging",
        "prompt": (
            "Packaging & distribution review of vibecodeallinone.\n"
            "Check: install script, requirements.txt, dependency pinning, "
            "version management, MCP server registration.\n"
            "Read: scripts/install.sh, kg-mcp-server/requirements.txt, README.md\n\n"
            "Output a JSON object with this exact structure:\n"
            '{{"perspective": "packaging", "score": <0-10>, '
            '"issues": [{{"severity": "CRITICAL|HIGH|MEDIUM|LOW", "file": "path", "description": "..."}}], '
            '"summary": "one paragraph"}}\n\n'
            "Only output the JSON, nothing else."
        ),
    },
    {
        "id": "review_ux",
        "name": "User Experience",
        "prompt": (
            "User experience review of vibecodeallinone.\n"
            "Evaluate: first-run experience, error messages, help text, "
            "skill discoverability, landing page quality.\n"
            "Read: README.md, docs/landing/index.html, skills/*/SKILL.md (sample 3)\n\n"
            "Output a JSON object with this exact structure:\n"
            '{{"perspective": "user_experience", "score": <0-10>, '
            '"issues": [{{"severity": "CRITICAL|HIGH|MEDIUM|LOW", "file": "path", "description": "..."}}], '
            '"summary": "one paragraph"}}\n\n'
            "Only output the JSON, nothing else."
        ),
    },
]


def _extract_json(text: str) -> dict | None:
    """Extract JSON object from text that may contain markdown code blocks."""
    import re

    # Try 1: markdown code block ```json ... ```
    match = re.search(r'```(?:json)?\s*\n?(\{.*?\})\s*\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try 2: raw JSON object
    start = text.find("{")
    if start >= 0:
        # Find matching closing brace
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i+1])
                    except json.JSONDecodeError:
                        break

    return None


def run_ai_reviews(model: str = "sonnet", dry_run: bool = False) -> list:
    """Run Stage 2: AI reviews via independent claude CLI calls."""
    log("Starting Stage 2: AI Multi-Perspective Review", "RUN")

    reviews_dir = ARTIFACTS_DIR / "reviews"
    reviews_dir.mkdir(exist_ok=True)

    results = []
    for perspective in AI_REVIEW_PERSPECTIVES:
        review_file = reviews_dir / f"{perspective['id']}.json"

        result = call_claude(
            prompt=perspective["prompt"],
            task_id=perspective["id"],
            model=model,
            dry_run=dry_run,
            timeout=180,
        )

        if result.get("status") == "success" and result.get("output"):
            # Try to extract JSON from output (may be in markdown code block)
            output = result["output"]
            review_data = _extract_json(output)

            if review_data and isinstance(review_data, dict) and "score" in review_data:
                review_file.write_text(json.dumps(review_data, indent=2))
                results.append(review_data)
                log(f"[{perspective['name']}] Score: {review_data.get('score', '?')}/10  "
                    f"Issues: {len(review_data.get('issues', []))}", "OK")
                continue

            log(f"[{perspective['name']}] Could not parse review JSON", "WARN")
            # Save raw output for debugging
            (reviews_dir / f"{perspective['id']}_raw.txt").write_text(output[:5000])
        elif dry_run:
            # Simulate for dry-run
            results.append({"perspective": perspective["id"], "score": 7, "issues": [], "summary": "dry-run"})
        else:
            log(f"[{perspective['name']}] Review failed", "FAIL")

    return results


def calculate_ai_review_score(reviews: list) -> int:
    """Calculate Stage 2 score (0-30) from AI reviews.

    Uses average of per-perspective scores (0-10) scaled to 0-30.
    CRITICAL issues cap the score (can't exceed 20 if any CRITICAL exists).
    """
    if not reviews:
        return 0

    # Average score across perspectives (each 0-10), scaled to 0-30
    total = sum(r.get("score", 0) for r in reviews)
    avg = total / len(reviews)  # 0-10
    score = round(avg * 3)  # scale 0-10 → 0-30

    # Count unique CRITICAL issues (deduplicated)
    critical_count = sum(
        1 for r in reviews
        for i in r.get("issues", [])
        if i.get("severity") == "CRITICAL"
    )

    # Cap score if CRITICAL issues exist (but don't zero out)
    if critical_count > 0:
        score = min(score, 20)  # cap at 20/30 if any CRITICAL
    if critical_count > 5:
        score = min(score, 15)  # further cap if many CRITICALs

    return max(0, min(30, score))


# ── Phase 3: Execute Fix via Claude CLI ────────────────────

def call_claude(prompt: str, task_id: str, model: str = "sonnet",
                dry_run: bool = False, timeout: int = 300) -> dict:
    """Call claude CLI in print mode → fresh context each time."""

    system = (
        "You are a code fixer. Fix the issue described. "
        "Work in the project directory. Be concise. Fix only what's needed. "
        "Do NOT add unnecessary files, comments, or refactoring."
    )

    cmd = [
        CLAUDE_BIN,
        "-p",  # print mode (non-interactive)
        "--model", model,
        "--allowedTools", ALLOWED_TOOLS,
        "--append-system-prompt", system,
        "--no-session-persistence",
        "--output-format", "json",
    ]

    # Build clean env: remove CLAUDECODE to avoid nested session block
    clean_env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    clean_env["CLAUDE_CODE_ENTRYPOINT"] = "cli"

    if dry_run:
        log(f"[DRY-RUN] Would call: claude -p --model {model} '{prompt[:80]}...'", "WARN")
        return {"status": "dry_run", "task_id": task_id}

    log(f"Calling claude CLI for [{task_id}]...", "RUN")
    start = time.perf_counter()

    try:
        result = subprocess.run(
            cmd,
            input=prompt,  # pass prompt via stdin to avoid shell escaping issues
            capture_output=True, text=True, timeout=timeout,
            cwd=str(REPO_ROOT),
            env=clean_env,
        )
        elapsed = time.perf_counter() - start

        success = result.returncode == 0
        error = result.stderr.strip()[-500:] if result.stderr else ""

        # Parse JSON envelope from --output-format json
        output = ""
        if result.stdout and result.stdout.strip():
            try:
                envelope = json.loads(result.stdout.strip())
                output = envelope.get("result", "")
                cost = envelope.get("total_cost_usd", 0)
                if cost:
                    log(f"  Cost: ${cost:.4f}", "INFO")
            except json.JSONDecodeError:
                output = result.stdout.strip()[-2000:]

        log(f"[{task_id}] {'OK' if success else 'FAIL'} ({elapsed:.1f}s)",
            "OK" if success else "FAIL")

        return {
            "status": "success" if success else "error",
            "task_id": task_id,
            "elapsed": round(elapsed, 1),
            "output": output,  # full output for JSON extraction
            "output_tail": output[-500:],  # for log serialization
            "error_tail": error,
        }

    except subprocess.TimeoutExpired:
        log(f"[{task_id}] Timed out after {timeout}s", "FAIL")
        return {"status": "timeout", "task_id": task_id}
    except Exception as e:
        log(f"[{task_id}] Error: {e}", "FAIL")
        return {"status": "error", "task_id": task_id, "error": str(e)}


# ── Phase 4: Auto-commit ──────────────────────────────────

def auto_commit(round_num: int) -> bool:
    """Stage changed files and commit."""
    log("Auto-committing changes...", "RUN")

    # Check for changes
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if not status.stdout.strip():
        log("No changes to commit", "WARN")
        return False

    # Stage tracked file changes (not untracked)
    subprocess.run(["git", "add", "-u"], cwd=str(REPO_ROOT))

    # Commit
    msg = f"ralph-loop: auto-fix round {round_num}"
    result = subprocess.run(
        ["git", "commit", "-m", msg],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )

    if result.returncode == 0:
        log(f"Committed: {msg}", "OK")
        # Push
        push = subprocess.run(
            ["git", "push"], capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        if push.returncode == 0:
            log("Pushed to remote", "OK")
        return True
    else:
        log(f"Commit failed: {result.stderr.strip()[:200]}", "FAIL")
        return False


# ── AI Review Fix Prompts ────────────────────────────────

def _generate_ai_review_fix_prompts(reviews: list) -> list:
    """Generate fix prompts from AI review CRITICAL/HIGH issues."""
    prompts = []
    for r in reviews:
        perspective = r.get("perspective", "unknown")
        critical_issues = [
            i for i in r.get("issues", [])
            if i.get("severity") in ("CRITICAL", "HIGH")
        ]
        if not critical_issues:
            continue

        issues_text = "\n".join(
            f"  - [{i['severity']}] {i.get('file', '?')}: {i.get('description', '?')[:200]}"
            for i in critical_issues[:8]
        )
        prompts.append({
            "id": f"fix_ai_{perspective}",
            "priority": 0,
            "prompt": (
                f"Fix the following {perspective} issues in the vibecodeallinone project.\n"
                f"Project root: {REPO_ROOT}\n\n"
                f"Issues to fix (from AI review):\n{issues_text}\n\n"
                f"Focus on CRITICAL issues first. Make minimal, targeted changes. "
                f"Do NOT refactor entire files — fix only what's listed above. "
                f"After fixing, verify the changes don't break anything."
            ),
        })

    prompts.sort(key=lambda p: p["priority"])
    return prompts


# ── Main Loop ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ralph Loop Orchestrator v4")
    parser.add_argument("--max-rounds", type=int, default=5, help="Max fix rounds")
    parser.add_argument("--stop-score", type=int, default=90, help="Target score")
    parser.add_argument("--model", default="sonnet", help="Claude model (sonnet/opus/haiku)")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    parser.add_argument("--auto-commit", action="store_true", help="Auto commit+push after fixes")
    parser.add_argument("--fix-limit", type=int, default=3,
                        help="Max fixes per round (to avoid infinite loops)")
    args = parser.parse_args()

    ARTIFACTS_DIR.mkdir(exist_ok=True)

    history = []
    start_time = time.time()
    ai_review_score = 0
    ai_review_done = False

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  Ralph Loop Orchestrator v4", file=sys.stderr)
    print(f"  Target: {args.stop_score}/100 | Max rounds: {args.max_rounds}", file=sys.stderr)
    print(f"  Model: {args.model} | Dry-run: {args.dry_run}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    for round_num in range(1, args.max_rounds + 1):
        print(f"\n{'─'*60}", file=sys.stderr)
        print(f"  ROUND {round_num}/{args.max_rounds}", file=sys.stderr)
        print(f"{'─'*60}", file=sys.stderr)

        # ── Stage 1+4: Machine Scan ──
        scan = run_machine_scan()
        base_score = scan.get("score", {}).get("total", 0)
        score = base_score + ai_review_score  # include previous AI review score

        # Check stop condition
        if score >= args.stop_score:
            log(f"Score {score} >= target {args.stop_score}. Done!", "OK")
            history.append({"round": round_num, "score": score, "action": "target_reached"})
            break

        # ── Stage 1+4 Fix: Generate fix prompts for gate/release failures ──
        prompts = generate_fix_prompts(scan)

        if prompts:
            log(f"Found {len(prompts)} fix tasks", "INFO")

            # Execute fixes (up to limit per round)
            round_results = []
            for prompt_info in prompts[:args.fix_limit]:
                result = call_claude(
                    prompt=prompt_info["prompt"],
                    task_id=prompt_info["id"],
                    model=args.model,
                    dry_run=args.dry_run,
                )
                round_results.append(result)

            # Auto-commit if requested
            if args.auto_commit and not args.dry_run:
                auto_commit(round_num)

            # Re-scan to verify fixes
            if not args.dry_run:
                verify = run_machine_scan()
                new_base = verify.get("score", {}).get("total", 0)
                new_score = new_base + ai_review_score
                delta = new_score - score
                log(f"Score: {score} → {new_score} (Δ{delta:+d})", "OK" if delta > 0 else "WARN")
            else:
                new_score = score
                delta = 0
                round_results = [{"task_id": p["id"], "status": "dry_run"} for p in prompts[:args.fix_limit]]

            history.append({
                "round": round_num,
                "phase": "fix",
                "score_before": score,
                "score_after": new_score,
                "delta": delta,
                "fixes": [r["task_id"] for r in round_results],
                "results": [{k: v for k, v in r.items() if k != "output"} for r in round_results],
            })

            if delta <= 0 and not args.dry_run:
                log("No score improvement from fixes.", "WARN")

        # ── Stage 2: AI Review (run once when gates are clean) ──
        gate_failures = [g for g in scan.get("gates", []) if g["status"] == "FAIL"]
        if not gate_failures and not ai_review_done:
            log("All gates PASS → Running Stage 2: AI Review", "RUN")
            ai_review_done = True
            reviews = run_ai_reviews(model=args.model, dry_run=args.dry_run)
            ai_review_score = calculate_ai_review_score(reviews)
            new_score = base_score + ai_review_score
            log(f"AI Review Score: {ai_review_score}/30  Total: {new_score}/100", "OK")

            history.append({
                "round": round_num,
                "phase": "ai_review",
                "score_before": base_score,
                "ai_review_score": ai_review_score,
                "score_after": new_score,
                "delta": ai_review_score,
                "fixes": [r.get("perspective", "?") for r in reviews],
            })

            # If AI review found CRITICAL issues → generate fix prompts for this round
            critical_issues = [
                i for r in reviews
                for i in r.get("issues", [])
                if i.get("severity") == "CRITICAL"
            ]
            if critical_issues:
                log(f"AI Review found {len(critical_issues)} CRITICAL issues → attempting auto-fix", "WARN")

                # Group critical issues by perspective for focused fixes
                fix_prompts_ai = _generate_ai_review_fix_prompts(reviews)
                for fix_prompt in fix_prompts_ai[:args.fix_limit]:
                    call_claude(
                        prompt=fix_prompt["prompt"],
                        task_id=fix_prompt["id"],
                        model=args.model,
                        dry_run=args.dry_run,
                    )

                if args.auto_commit and not args.dry_run:
                    auto_commit(round_num)

            score = new_score

        # ── Stop check after all phases ──
        if score >= args.stop_score:
            log(f"Score {score} >= target {args.stop_score}. Done!", "OK")
            break

        if not prompts and ai_review_done:
            # No gate failures remain, continue to next round for re-review
            log("Gates clean, will re-run AI review in next round to measure improvement.", "INFO")
            ai_review_done = False  # allow re-review next round
            continue

    # ── Final Summary ──
    elapsed = time.time() - start_time
    final_scan = run_machine_scan() if not args.dry_run else scan
    final_score = final_scan.get("score", {}).get("total", 0) + ai_review_score

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  ORCHESTRATOR COMPLETE", file=sys.stderr)
    print(f"  Final Score: {final_score}/100", file=sys.stderr)
    print(f"  Rounds: {len(history)}", file=sys.stderr)
    print(f"  Elapsed: {elapsed:.1f}s", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # Score history table
    print(f"\n  Round | Before | After | Δ   | Fixes", file=sys.stderr)
    print(f"  ------|--------|-------|-----|------", file=sys.stderr)
    for h in history:
        fixes = ", ".join(h.get("fixes", []))
        before = h.get("score_before", h.get("score", "?"))
        after = h.get("score_after", "?")
        delta = h.get("delta", "?")
        print(f"  {h['round']:5} | {str(before):6} | {str(after):5} | {str(delta):3} | {fixes}", file=sys.stderr)

    # Save log
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "final_score": final_score,
        "target_score": args.stop_score,
        "rounds": history,
        "elapsed_seconds": round(elapsed, 1),
        "model": args.model,
    }
    ORCHESTRATOR_LOG.write_text(json.dumps(log_data, indent=2, ensure_ascii=False))
    log(f"Log saved: {ORCHESTRATOR_LOG}", "OK")

    # Exit code
    sys.exit(0 if final_score >= args.stop_score else 1)


if __name__ == "__main__":
    main()
