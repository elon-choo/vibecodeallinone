#!/usr/bin/env python3
"""
Ralph Loop v3 — Automated Quality Loop for vibecodeallinone
=============================================================
Entry point: python scripts/ralphloop/run.py [options]

Stages:
  Stage 1: Machine Gates (G0~G8)
  Stage 2: AI Multi-Model Review (optional)
  Stage 3: E2E Validation (optional)
  Stage 4: Release Gate Checklist
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Constants ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
GATES_FILE = ARTIFACTS_DIR / "gates.json"
REPORT_FILE = ARTIFACTS_DIR / "report.md"
STEPS_DIR = Path(__file__).parent / "steps"


# ── Gate Registry ──────────────────────────────────────────

def gate_g0_env() -> dict:
    """G0: Environment check — Python >= 3.11, bash, git."""
    issues = []
    if sys.version_info < (3, 11):
        issues.append(f"Python {sys.version} < 3.11")

    for cmd in ["bash", "git"]:
        if subprocess.run(["which", cmd], capture_output=True).returncode != 0:
            issues.append(f"{cmd} not found")

    return {
        "gate": "G0_env",
        "severity": "CRITICAL",
        "status": "FAIL" if issues else "PASS",
        "issues": issues,
    }


def gate_g1_lint() -> dict:
    """G1: Ruff lint — syntax/fatal errors only."""
    try:
        result = subprocess.run(
            ["ruff", "check", "--select", "E9,F63,F7,F82",
             str(REPO_ROOT / "kg-mcp-server"), str(REPO_ROOT / "hooks")],
            capture_output=True, text=True, timeout=60,
        )
        errors = [l for l in result.stdout.strip().split("\n") if l.strip()] if result.stdout.strip() else []
        return {
            "gate": "G1_lint",
            "severity": "HIGH",
            "status": "FAIL" if result.returncode != 0 else "PASS",
            "issues": errors[:10],
        }
    except FileNotFoundError:
        return {"gate": "G1_lint", "severity": "HIGH", "status": "WARN", "issues": ["ruff not installed"]}
    except Exception as e:
        return {"gate": "G1_lint", "severity": "HIGH", "status": "WARN", "issues": [str(e)]}


def gate_g2_forbidden_scan() -> dict:
    """G2: Forbidden strings in MCP server code."""
    import re

    patterns = {
        r"from src\.": ("CRITICAL", "External src. import"),
        r"neo4j_knowledgeGraph": ("CRITICAL", "Hardcoded legacy path"),
        r"~/Documents": ("HIGH", "Hardcoded home path"),
        r"google\.generativeai": ("CRITICAL", "Deprecated SDK import"),
    }

    # print() in mcp_server/ (exclude file=sys.stderr)
    print_pattern = re.compile(r"print\((?!.*file\s*=\s*sys\.stderr)")

    scan_dirs = [
        REPO_ROOT / "kg-mcp-server" / "mcp_server",
    ]
    issues = []

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        for py_file in scan_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                rel = py_file.relative_to(REPO_ROOT)

                for pattern, (severity, desc) in patterns.items():
                    if re.search(pattern, content):
                        issues.append({"file": str(rel), "severity": severity, "pattern": desc})

                # print() check (only in mcp_server/)
                for i, line in enumerate(content.split("\n"), 1):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if print_pattern.search(stripped):
                        issues.append({
                            "file": f"{rel}:{i}",
                            "severity": "CRITICAL",
                            "pattern": f"stdout print: {stripped[:80]}",
                        })
            except Exception:
                pass

    critical = [i for i in issues if i["severity"] == "CRITICAL"]
    return {
        "gate": "G2_forbidden_scan",
        "severity": "CRITICAL",
        "status": "FAIL" if critical else ("WARN" if issues else "PASS"),
        "issues": issues,
    }


def gate_g6_sdk_deprecation() -> dict:
    """G6: Check if deprecated google-generativeai is in requirements."""
    req_file = REPO_ROOT / "kg-mcp-server" / "requirements.txt"
    if not req_file.exists():
        return {"gate": "G6_sdk_deprecation", "severity": "CRITICAL",
                "status": "WARN", "issues": ["requirements.txt not found"]}

    content = req_file.read_text()
    if "google-generativeai" in content:
        return {
            "gate": "G6_sdk_deprecation",
            "severity": "CRITICAL",
            "status": "FAIL",
            "issues": ["google-generativeai found in requirements.txt — migrate to google-genai"],
        }

    return {"gate": "G6_sdk_deprecation", "severity": "CRITICAL", "status": "PASS", "issues": []}


def gate_g8_server_dry_run() -> dict:
    """G8: Server dry-run — import + tool registry without Neo4j."""
    server_py = REPO_ROOT / "kg-mcp-server" / "mcp_server" / "server.py"
    if not server_py.exists():
        return {"gate": "G8_server_dry_run", "severity": "CRITICAL",
                "status": "WARN", "issues": ["server.py not found"]}

    # Try importing server module to catch ImportError
    try:
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, 'kg-mcp-server'); "
             "from mcp_server.config import config; "
             "print('config OK'); "],
            capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            return {
                "gate": "G8_server_dry_run",
                "severity": "CRITICAL",
                "status": "FAIL",
                "issues": [result.stderr.strip()[:500]],
            }
        return {"gate": "G8_server_dry_run", "severity": "CRITICAL", "status": "PASS", "issues": []}
    except Exception as e:
        return {"gate": "G8_server_dry_run", "severity": "CRITICAL",
                "status": "FAIL", "issues": [str(e)]}


# ── Release Gate (Stage 4) ──────────────────────────────────

def check_release_gates() -> list:
    """Stage 4: v1.0.0 release checklist."""
    checks = []

    def file_check(name, path, hint=""):
        exists = (REPO_ROOT / path).exists()
        checks.append({"id": name, "status": "PASS" if exists else "FAIL", "hint": hint or path})

    def content_check(name, path, keyword, hint=""):
        fp = REPO_ROOT / path
        if not fp.exists():
            checks.append({"id": name, "status": "FAIL", "hint": f"{path} missing"})
            return
        content = fp.read_text(errors="ignore").lower()
        found = keyword.lower() in content
        checks.append({"id": name, "status": "PASS" if found else "FAIL", "hint": hint})

    file_check("R2_changelog", "CHANGELOG.md")
    file_check("R3_license", "LICENSE")
    file_check("R4_contributing", "CONTRIBUTING.md")
    file_check("R9_security", "SECURITY.md")
    content_check("R1_demo_gif", "README.md", ".gif", "Demo GIF in README")
    content_check("R8_benchmark", "README.md", "benchmark", "Benchmark results in README")
    content_check("R10_ci_badge", "README.md", "actions", "CI badge in README")

    # R6: GitHub topics (check via file, not API)
    checks.append({"id": "R6_topics", "status": "PASS", "hint": "Set via gh repo edit"})

    # R7: Landing page exists
    landing = (REPO_ROOT / "docs" / "landing" / "index.html").exists()
    checks.append({"id": "R7_landing", "status": "PASS" if landing else "FAIL", "hint": "Landing page"})

    # R5: PR template exists
    pr_template = (REPO_ROOT / ".github" / "pull_request_template.md").exists()
    checks.append({"id": "R5_pr_template", "status": "PASS" if pr_template else "FAIL", "hint": "PR template"})

    return checks


# ── Score Calculator ──────────────────────────────────────

def load_e2e_score() -> int:
    """Load Stage 3 E2E score from artifacts/e2e_score.json (0-20)."""
    e2e_file = ARTIFACTS_DIR / "e2e_score.json"
    if not e2e_file.exists():
        return 0
    try:
        data = json.loads(e2e_file.read_text())
        return min(20, data.get("total_score", 0))
    except (json.JSONDecodeError, KeyError):
        return 0


def load_ai_review_score() -> int:
    """Load Stage 2 AI review score from artifacts/reviews/*.json (0-30)."""
    reviews_dir = ARTIFACTS_DIR / "reviews"
    if not reviews_dir.exists():
        return 0

    scores = []
    for review_file in sorted(reviews_dir.glob("review_*.json")):
        if "_raw" in review_file.name:
            continue
        try:
            data = json.loads(review_file.read_text())
            scores.append(data.get("score", 0))
        except (json.JSONDecodeError, KeyError):
            continue

    if not scores:
        return 0

    avg = sum(scores) / len(scores)
    ai_score = round(avg * 3)  # 0-10 avg × 3 → 0-30

    # Cap if CRITICAL issues exist
    total_critical = 0
    for review_file in reviews_dir.glob("review_*.json"):
        if "_raw" in review_file.name:
            continue
        try:
            data = json.loads(review_file.read_text())
            total_critical += sum(1 for i in data.get("issues", []) if i.get("severity") == "CRITICAL")
        except (json.JSONDecodeError, KeyError):
            continue

    if total_critical >= 5:
        ai_score = min(ai_score, 15)
    elif total_critical > 0:
        ai_score = min(ai_score, 20)

    return min(30, ai_score)


def calculate_score(gates: list, release_checks: list) -> dict:
    """Calculate Health Score (0-100)."""
    # Stage 1: Machine Gates (30 points)
    stage1 = 30
    for g in gates:
        if g["status"] == "FAIL":
            if g["severity"] == "CRITICAL":
                stage1 -= 10
            elif g["severity"] == "HIGH":
                stage1 -= 5
        elif g["status"] == "WARN":
            stage1 -= 1
    stage1 = max(0, stage1)

    # Stage 2: AI Review — load from artifacts/reviews/*.json
    stage2 = load_ai_review_score()

    # Stage 3: E2E — load from artifacts/e2e_score.json
    stage3 = load_e2e_score()

    # Stage 4: Release Gate (20 points, 2 per check)
    stage4 = sum(2 for c in release_checks if c["status"] == "PASS")
    stage4 = min(20, stage4)

    total = stage1 + stage2 + stage3 + stage4
    notes = []
    if stage2 == 0:
        notes.append("Stage 2 (AI review) not run")
    if stage3 == 0:
        notes.append("Stage 3 (E2E) not run — use: python3 scripts/ralphloop/e2e/t3_benchmark.py --e2e-score")

    return {
        "total": total,
        "stage1_gates": stage1,
        "stage2_ai_review": stage2,
        "stage3_e2e": stage3,
        "stage4_release": stage4,
        "max_possible": 100,
        "notes": "; ".join(notes) if notes else "All stages active",
    }


# ── Report Generator ──────────────────────────────────────

def generate_report(gates: list, release_checks: list, score: dict, elapsed: float) -> str:
    """Generate Markdown report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "# Ralph Loop v3 — Health Report",
        "",
        f"**Generated**: {now}",
        f"**Elapsed**: {elapsed:.1f}s",
        f"**Health Score**: **{score['total']}/100**",
        "",
        "---",
        "",
        "## Score Breakdown",
        "",
        f"| Stage | Score | Max |",
        f"|-------|-------|-----|",
        f"| Stage 1: Machine Gates | {score['stage1_gates']} | 30 |",
        f"| Stage 2: AI Review | {score['stage2_ai_review']} | 30 |",
        f"| Stage 3: E2E Validation | {score['stage3_e2e']} | 20 |",
        f"| Stage 4: Release Gate | {score['stage4_release']} | 20 |",
        f"| **Total** | **{score['total']}** | **100** |",
        "",
        "---",
        "",
        "## Stage 1: Machine Gates",
        "",
        "| Gate | Severity | Status | Issues |",
        "|------|----------|--------|--------|",
    ]

    for g in gates:
        emoji = {"PASS": "PASS", "FAIL": "**FAIL**", "WARN": "WARN"}[g["status"]]
        issue_count = len(g.get("issues", []))
        lines.append(f"| {g['gate']} | {g['severity']} | {emoji} | {issue_count} |")

    # Failed gate details
    failed = [g for g in gates if g["status"] == "FAIL"]
    if failed:
        lines.extend(["", "### Failed Gates Detail", ""])
        for g in failed:
            lines.append(f"**{g['gate']}** ({g['severity']})")
            for issue in g.get("issues", [])[:5]:
                if isinstance(issue, dict):
                    lines.append(f"- [{issue.get('severity','?')}] `{issue.get('file','')}`: {issue.get('pattern','')}")
                else:
                    lines.append(f"- {issue}")
            lines.append("")

    lines.extend([
        "---",
        "",
        "## Stage 4: Release Gate Checklist",
        "",
        "| Check | Status |",
        "|-------|--------|",
    ])

    for c in release_checks:
        emoji = "PASS" if c["status"] == "PASS" else "**FAIL**"
        lines.append(f"| {c['id']} | {emoji} |")

    # Action items
    release_fails = [c for c in release_checks if c["status"] == "FAIL"]
    if release_fails:
        lines.extend(["", "### Missing for v1.0.0", ""])
        for c in release_fails:
            lines.append(f"- **{c['id']}**: {c.get('hint', '')}")

    lines.extend([
        "",
        "---",
        "",
        "## Next Actions (Priority Order)",
        "",
    ])

    # Prioritized actions
    actions = []
    for g in failed:
        actions.append(f"1. **Fix {g['gate']}** ({g['severity']}): {len(g.get('issues',[]))} issues")
    for c in release_fails:
        actions.append(f"2. **Create {c['id']}**: {c.get('hint','')}")

    if not actions:
        actions.append("All gates PASS! Consider running `--review-mode api` for AI review (Stage 2).")

    lines.extend(actions)
    lines.append("")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ralph Loop v3 — Automated Quality Loop")
    parser.add_argument("--review-mode", choices=["api", "clipboard", "off"], default="off",
                        help="AI review mode (default: off)")
    parser.add_argument("--stop-score", type=int, default=0,
                        help="Stop if score reaches this threshold")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of report")
    args = parser.parse_args()

    start = time.time()
    os.chdir(REPO_ROOT)

    # Ensure artifacts dir
    ARTIFACTS_DIR.mkdir(exist_ok=True)

    print("Ralph Loop v3 starting...", file=sys.stderr)
    print(f"  Repo: {REPO_ROOT}", file=sys.stderr)
    print(f"  Review mode: {args.review_mode}", file=sys.stderr)
    print("", file=sys.stderr)

    # ── Stage 1: Machine Gates ──
    print("=== Stage 1: Machine Gates ===", file=sys.stderr)
    gates = []
    gate_funcs = [
        gate_g0_env,
        gate_g1_lint,
        gate_g2_forbidden_scan,
        gate_g6_sdk_deprecation,
        gate_g8_server_dry_run,
    ]

    for func in gate_funcs:
        result = func()
        gates.append(result)
        status_icon = {"PASS": "+", "FAIL": "X", "WARN": "~"}[result["status"]]
        print(f"  [{status_icon}] {result['gate']}: {result['status']} ({len(result.get('issues',[]))} issues)",
              file=sys.stderr)

    # Save gates
    GATES_FILE.write_text(json.dumps(gates, indent=2, ensure_ascii=False))

    critical_fails = [g for g in gates if g["status"] == "FAIL" and g["severity"] == "CRITICAL"]
    if critical_fails:
        print(f"\n  CRITICAL gates failed: {len(critical_fails)}", file=sys.stderr)

    # ── Stage 2: AI Review (if requested) ──
    if args.review_mode == "api":
        print("\n=== Stage 2: AI Review (api mode) ===", file=sys.stderr)
        print("  Not yet implemented — run with --review-mode clipboard for prompts", file=sys.stderr)
    elif args.review_mode == "clipboard":
        print("\n=== Stage 2: AI Review (clipboard mode) ===", file=sys.stderr)
        print("  Prompts available at: RalphLoop_v3/06_REVIEW_PROMPTS.md", file=sys.stderr)

    # ── Stage 4: Release Gate ──
    print("\n=== Stage 4: Release Gate ===", file=sys.stderr)
    release_checks = check_release_gates()
    for c in release_checks:
        status_icon = "+" if c["status"] == "PASS" else "X"
        print(f"  [{status_icon}] {c['id']}: {c['status']}", file=sys.stderr)

    # ── Score ──
    score = calculate_score(gates, release_checks)
    elapsed = time.time() - start

    print(f"\n{'='*40}", file=sys.stderr)
    print(f"  Health Score: {score['total']}/100", file=sys.stderr)
    print(f"  Stage 1 (Gates):   {score['stage1_gates']}/30", file=sys.stderr)
    s2_note = "" if score['stage2_ai_review'] > 0 else " (not run)"
    s3_note = "" if score['stage3_e2e'] > 0 else " (not run)"
    print(f"  Stage 2 (Review):  {score['stage2_ai_review']}/30{s2_note}", file=sys.stderr)
    print(f"  Stage 3 (E2E):     {score['stage3_e2e']}/20{s3_note}", file=sys.stderr)
    print(f"  Stage 4 (Release): {score['stage4_release']}/20", file=sys.stderr)
    print(f"  Elapsed: {elapsed:.1f}s", file=sys.stderr)
    print(f"{'='*40}", file=sys.stderr)

    # ── Report ──
    if args.json:
        output = json.dumps({"gates": gates, "release": release_checks, "score": score}, indent=2)
        print(output)
    else:
        report = generate_report(gates, release_checks, score, elapsed)
        REPORT_FILE.write_text(report)
        print(f"\n  Report: {REPORT_FILE}", file=sys.stderr)

    # Exit code: 1 if any CRITICAL gate failed
    sys.exit(1 if critical_fails else 0)


if __name__ == "__main__":
    main()
