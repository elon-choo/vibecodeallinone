#!/usr/bin/env python3
"""
Ralph Loop v5 — Loop Runner (Scan + Score + Action Plan)
=========================================================
Claude Code 네이티브 루프의 핵심 스크립트.
run.py의 Gate/Release 스캔 + AI Review 점수 + E2E 점수를 통합하여
현재 점수와 구체적 액션플랜을 JSON으로 출력.

Usage:
  python3 scripts/ralphloop/loop_runner.py [--json] [--run-e2e]
"""

import argparse
import importlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

RALPH_LOOP_DIR = Path(__file__).parent
if str(RALPH_LOOP_DIR) not in sys.path:
    sys.path.insert(0, str(RALPH_LOOP_DIR))

artifact_io = importlib.import_module("artifact_io")
review_score_value = artifact_io.review_score_value

REPO_ROOT = Path(__file__).parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
REVIEWS_DIR = ARTIFACTS_DIR / "reviews"
BENCHMARK_FILE = ARTIFACTS_DIR / "benchmark_results.json"
E2E_SCORE_FILE = ARTIFACTS_DIR / "e2e_score.json"

# ── Action Templates per Area ──────────────────────────────

ACTION_TEMPLATES = {
    "testing": [
        "Add pytest-cov with --cov-fail-under=15 to CI workflow",
        "Write unit tests for server.py tool dispatch table",
        "Write tests for hybrid_search.py pipeline",
        "Replace pytest.skip() patterns with proper mocks",
        "Add integration test for config → server startup flow",
    ],
    "security": [
        "Add authentication middleware to dashboard endpoints",
        "Sanitize error responses to prevent info leakage",
        "Add rate limiting to MCP tool endpoints",
        "Fix shared mutable state race conditions in smart_context",
        "Scope file access to project directory only",
    ],
    "code_quality": [
        "Add cache eviction policy (LRU/TTL) to prevent unbounded growth",
        "Extract repeated BugRadar/VectorSearchEngine instantiation",
        "Add file locking for concurrent sync operations",
        "Replace threading.Lock with asyncio.Lock in async code",
        "Fix N+1 query patterns in graph traversal",
    ],
    "architecture": [
        "Extract tool dispatch into a registry pattern",
        "Separate config validation from loading",
        "Add proper error boundary between pipeline stages",
        "Implement plugin interface for search providers",
    ],
    "documentation": [
        "Add API reference for all MCP tools",
        "Document configuration options with examples",
        "Add architecture decision records (ADRs)",
        "Improve inline docstrings for public functions",
    ],
    "packaging": [
        "Pin dependency versions with upper bounds (e.g., mcp[cli]>=1.0,<2.0)",
        "Add --help flag to install.sh",
        "Add py.typed marker for type checking consumers",
        "Create pyproject.toml with proper metadata",
    ],
    "ux": [
        "Add colored output for CLI status messages",
        "Improve first-run experience with guided setup",
        "Add --verbose and --quiet flags consistently",
        "Better error messages with suggested fixes",
    ],
}


def load_gate_scores() -> dict:
    """Load latest gate scan results from run.py --json output."""
    gates_file = ARTIFACTS_DIR / "gates.json"
    if not gates_file.exists():
        return {"score": 0, "max": 30, "gates": [], "fails": []}

    gates = json.loads(gates_file.read_text())
    score = 30
    fails = []
    for g in gates:
        if g["status"] == "FAIL":
            if g["severity"] == "CRITICAL":
                score -= 10
            elif g["severity"] == "HIGH":
                score -= 5
            fails.append(g)
        elif g["status"] == "WARN":
            score -= 1

    return {"score": max(0, score), "max": 30, "gates": gates, "fails": fails}


def load_release_scores() -> dict:
    """Calculate release gate score from run.py output."""
    # Re-run the release gate check inline
    sys.path.insert(0, str(Path(__file__).parent))
    from run import check_release_gates

    checks = check_release_gates()
    score = sum(2 for c in checks if c["status"] == "PASS")
    score = min(20, score)
    fails = [c for c in checks if c["status"] == "FAIL"]

    return {"score": score, "max": 20, "checks": checks, "fails": fails}


def load_ai_review_scores() -> dict:
    """Load AI review scores from artifacts/reviews/*.json."""
    if not REVIEWS_DIR.exists():
        return {"score": 0, "max": 30, "perspectives": {}, "weakest": []}

    perspectives = {}
    for review_file in sorted(REVIEWS_DIR.glob("review_*.json")):
        if "_raw" in review_file.name:
            continue
        try:
            data = json.loads(review_file.read_text())
            name = data.get("perspective", review_file.stem.replace("review_", ""))
            normalized_score = review_score_value(data)
            perspectives[name] = {
                "score": normalized_score,
                "issues": data.get("issues", []),
                "critical_count": sum(1 for i in data.get("issues", []) if i.get("severity") == "CRITICAL"),
                "high_count": sum(1 for i in data.get("issues", []) if i.get("severity") == "HIGH"),
            }
        except (json.JSONDecodeError, KeyError):
            continue

    if not perspectives:
        return {"score": 0, "max": 30, "perspectives": {}, "weakest": []}

    # Average score (0-10) × 3 → 0-30 scale
    avg = sum(p["score"] for p in perspectives.values()) / len(perspectives)
    ai_score = round(avg * 3, 1)

    # Cap if CRITICAL issues exist
    total_critical = sum(p["critical_count"] for p in perspectives.values())
    if total_critical >= 5:
        ai_score = min(ai_score, 15)
    elif total_critical > 0:
        ai_score = min(ai_score, 20)

    ai_score = min(30, ai_score)

    # Sort by score ascending to find weakest
    weakest = sorted(perspectives.items(), key=lambda x: x[1]["score"])

    return {
        "score": ai_score,
        "max": 30,
        "perspectives": perspectives,
        "weakest": [(name, data) for name, data in weakest],
    }


def load_e2e_score() -> dict:
    """Load E2E score from artifacts/e2e_score.json."""
    if not E2E_SCORE_FILE.exists():
        return {"score": 0, "max": 20, "details": {}, "available": False}

    try:
        data = json.loads(E2E_SCORE_FILE.read_text())
        return {
            "score": data.get("total_score", 0),
            "max": 20,
            "details": data.get("checks", {}),
            "available": True,
        }
    except (json.JSONDecodeError, KeyError):
        return {"score": 0, "max": 20, "details": {}, "available": False}


def run_machine_scan():
    """Run run.py --json to refresh gate scores."""
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "run.py"), "--json"],
            capture_output=True, text=True, timeout=120, cwd=str(REPO_ROOT),
        )
        # run.py outputs JSON to stdout
        if result.stdout.strip():
            return json.loads(result.stdout)
    except Exception as e:
        print(f"  Warning: Machine scan failed: {e}", file=sys.stderr)
    return None


def run_e2e_benchmark():
    """Run t3_benchmark.py with --e2e-score to generate E2E score."""
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "e2e" / "t3_benchmark.py"), "--e2e-score"],
            capture_output=True, text=True, timeout=180, cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            print(f"  Warning: E2E benchmark returned code {result.returncode}", file=sys.stderr)
            if result.stderr:
                print(f"  {result.stderr[:300]}", file=sys.stderr)
    except Exception as e:
        print(f"  Warning: E2E benchmark failed: {e}", file=sys.stderr)


def build_action_plan(gate_data, release_data, ai_data, e2e_data) -> list:
    """Build prioritized action plan from all scores."""
    areas = []

    # Gate failures → highest priority
    if gate_data["fails"]:
        actions = []
        for g in gate_data["fails"]:
            actions.append(f"Fix {g['gate']}: {', '.join(str(i) for i in g.get('issues', [])[:2])}")
        areas.append({
            "area": "gates",
            "score": gate_data["score"],
            "max": gate_data["max"],
            "priority": 0,
            "top_actions": actions[:3],
        })

    # Release failures
    if release_data["fails"]:
        actions = [f"Create/fix {c['id']}: {c.get('hint', '')}" for c in release_data["fails"]]
        areas.append({
            "area": "release",
            "score": release_data["score"],
            "max": release_data["max"],
            "priority": 2,
            "top_actions": actions[:3],
        })

    # AI review weakest areas
    for name, data in ai_data.get("weakest", []):
        if data["score"] >= 8:
            continue  # Already good enough
        # Get actions from templates, prioritized by severity
        template_actions = ACTION_TEMPLATES.get(name, [])
        # Add issue-specific actions
        issue_actions = []
        for issue in data["issues"]:
            if issue.get("severity") in ("CRITICAL", "HIGH"):
                desc = issue.get("description", "")
                if len(desc) > 120:
                    desc = desc[:117] + "..."
                issue_actions.append(f"[{issue['severity']}] {desc}")

        combined = issue_actions[:3] + template_actions[:2]
        areas.append({
            "area": name,
            "score": data["score"],
            "max": 10,
            "priority": 1 if data["critical_count"] > 0 else 2,
            "top_actions": combined[:5],
        })

    # E2E area
    if not e2e_data.get("available") or e2e_data["score"] < 15:
        e2e_actions = [
            "Run: python3 scripts/ralphloop/e2e/t3_benchmark.py --e2e-score",
            "Ensure pytest passes: pytest kg-mcp-server/tests/ -x -q",
            "Ensure ruff lint passes: ruff check kg-mcp-server/",
            "Ensure server.py imports cleanly",
        ]
        areas.append({
            "area": "e2e",
            "score": e2e_data["score"],
            "max": e2e_data["max"],
            "priority": 1,
            "top_actions": e2e_actions,
        })

    # Sort by priority then by score ascending
    areas.sort(key=lambda x: (x["priority"], x["score"]))
    return areas


def estimate_gain(areas: list) -> int:
    """Estimate potential point gain if all actions completed."""
    gain = 0
    for area in areas:
        deficit = area["max"] - area["score"]
        # Assume 60% of deficit recoverable
        gain += int(deficit * 0.6)
    return min(gain, 40)  # Cap at reasonable estimate


def main():
    parser = argparse.ArgumentParser(description="Ralph Loop v5 — Loop Runner")
    parser.add_argument("--json", action="store_true", help="Output pure JSON (for programmatic use)")
    parser.add_argument("--run-e2e", action="store_true", help="Run E2E benchmark before scoring")
    parser.add_argument("--rescan", action="store_true", help="Re-run machine scan before scoring")
    args = parser.parse_args()

    start = time.time()
    os.chdir(REPO_ROOT)

    print("Ralph Loop v5 — Loop Runner", file=sys.stderr)
    print(f"  Repo: {REPO_ROOT}", file=sys.stderr)

    # Step 1: Optionally re-run scans
    if args.rescan:
        print("\n  Running machine scan...", file=sys.stderr)
        run_machine_scan()

    if args.run_e2e:
        print("  Running E2E benchmark...", file=sys.stderr)
        run_e2e_benchmark()

    # Step 2: Load all scores
    print("\n  Loading scores...", file=sys.stderr)
    gate_data = load_gate_scores()
    release_data = load_release_scores()
    ai_data = load_ai_review_scores()
    e2e_data = load_e2e_score()

    total = gate_data["score"] + round(ai_data["score"]) + e2e_data["score"] + release_data["score"]

    # Step 3: Build action plan
    weakest_areas = build_action_plan(gate_data, release_data, ai_data, e2e_data)
    estimated_gain = estimate_gain(weakest_areas)

    elapsed = time.time() - start

    # Step 4: Output
    output = {
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_score": total,
        "breakdown": {
            "gates": gate_data["score"],
            "ai_review": round(ai_data["score"]),
            "e2e": e2e_data["score"],
            "release": release_data["score"],
        },
        "weakest_areas": [
            {
                "area": a["area"],
                "score": a["score"],
                "max": a["max"],
                "top_actions": a["top_actions"],
            }
            for a in weakest_areas
        ],
        "estimated_gain": f"+{estimated_gain} points if all actions completed",
        "elapsed_s": round(elapsed, 1),
    }

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # Human-friendly output
        print(f"\n{'='*50}", file=sys.stderr)
        print(f"  Total Score: {total}/100", file=sys.stderr)
        print(f"  Gates:     {gate_data['score']}/30", file=sys.stderr)
        print(f"  AI Review: {round(ai_data['score'])}/30", file=sys.stderr)
        print(f"  E2E:       {e2e_data['score']}/20", file=sys.stderr)
        print(f"  Release:   {release_data['score']}/20", file=sys.stderr)
        print(f"{'='*50}", file=sys.stderr)

        if weakest_areas:
            print(f"\n  Weakest Areas (priority order):", file=sys.stderr)
            for a in weakest_areas[:5]:
                print(f"    [{a['area']}] {a['score']}/{a['max']}", file=sys.stderr)
                for action in a["top_actions"][:3]:
                    print(f"      → {action}", file=sys.stderr)

        print(f"\n  Estimated gain: +{estimated_gain} points", file=sys.stderr)
        print(f"  Elapsed: {elapsed:.1f}s", file=sys.stderr)

        # Also write JSON to stdout for piping
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
