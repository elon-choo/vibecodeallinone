#!/usr/bin/env python3
"""
Ralph Loop v5 — Self Review Framework
=======================================
Claude Code가 직접 코드를 읽고 체크리스트를 채워 리뷰하는 프레임워크.
각 perspective별 체크리스트(JSON schema)를 제공하고,
결과를 artifacts/reviews/에 저장.

Usage:
  python3 scripts/ralphloop/self_review.py --perspective testing
  python3 scripts/ralphloop/self_review.py --perspective all
  python3 scripts/ralphloop/self_review.py --list
"""

import argparse
import importlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

RALPH_LOOP_DIR = Path(__file__).parent
if str(RALPH_LOOP_DIR) not in sys.path:
    sys.path.insert(0, str(RALPH_LOOP_DIR))

artifact_io = importlib.import_module("artifact_io")
SCHEMA_VERSION = artifact_io.SCHEMA_VERSION
atomic_write_json = artifact_io.atomic_write_json
git_commit = artifact_io.git_commit
git_tree_state = artifact_io.git_tree_state
hash_inputs = artifact_io.hash_inputs
hash_json_payload = artifact_io.hash_json_payload

REPO_ROOT = Path(__file__).parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
REVIEWS_DIR = ARTIFACTS_DIR / "reviews"
KG_MCP_DIR = REPO_ROOT / "kg-mcp-server"
MCP_SERVER_DIR = KG_MCP_DIR / "mcp_server"

# ── Perspective Checklists ──────────────────────────────────

PERSPECTIVES = {
    "code_quality": {
        "name": "Code Quality",
        "description": "Error handling, type safety, edge cases, resource cleanup",
        "scan_paths": [MCP_SERVER_DIR],
        "checklist": [
            {
                "id": "CQ1",
                "check": "All public functions have proper error handling (try/except or explicit error returns)",
                "severity": "HIGH",
                "how_to_verify": "Grep for 'def ' in mcp_server/*.py, check each has error handling",
            },
            {
                "id": "CQ2",
                "check": "No unbounded data structures (caches, lists, dicts) that grow without limit",
                "severity": "CRITICAL",
                "how_to_verify": "Search for dict/list assignments that append without eviction",
            },
            {
                "id": "CQ3",
                "check": "Resources (files, connections, sessions) are properly closed/released",
                "severity": "HIGH",
                "how_to_verify": "Search for open(), aiohttp.ClientSession, neo4j.Session without context manager",
            },
            {
                "id": "CQ4",
                "check": "No threading.Lock used in async code (should use asyncio.Lock)",
                "severity": "MEDIUM",
                "how_to_verify": "Grep for 'threading.Lock' in async files",
            },
            {
                "id": "CQ5",
                "check": "Type hints on all public function signatures",
                "severity": "LOW",
                "how_to_verify": "Check public functions for -> return type and parameter annotations",
            },
            {
                "id": "CQ6",
                "check": "No duplicate code blocks (>10 lines identical)",
                "severity": "MEDIUM",
                "how_to_verify": "Look for repeated patterns across files",
            },
        ],
    },
    "security": {
        "name": "Security",
        "description": "Authentication, injection, secrets, access control",
        "scan_paths": [MCP_SERVER_DIR],
        "checklist": [
            {
                "id": "SEC1",
                "check": "No hardcoded secrets, API keys, or passwords in source code",
                "severity": "CRITICAL",
                "how_to_verify": "Grep for patterns: api_key=, password=, token=, secret=",
            },
            {
                "id": "SEC2",
                "check": "All user/external input is sanitized before use in queries (Cypher, SQL)",
                "severity": "CRITICAL",
                "how_to_verify": "Find all neo4j query executions, check for parameterized queries",
            },
            {
                "id": "SEC3",
                "check": "HTTP endpoints have authentication/authorization checks",
                "severity": "HIGH",
                "how_to_verify": "Find route definitions, check for auth middleware or decorators",
            },
            {
                "id": "SEC4",
                "check": "Error messages don't leak internal paths, stack traces, or config details",
                "severity": "MEDIUM",
                "how_to_verify": "Check exception handlers for str(e) or traceback in HTTP responses",
            },
            {
                "id": "SEC5",
                "check": "File access is scoped to project directory (no path traversal)",
                "severity": "HIGH",
                "how_to_verify": "Find file read/write operations, check for path validation",
            },
            {
                "id": "SEC6",
                "check": "No eval(), exec(), or subprocess with shell=True on user input",
                "severity": "CRITICAL",
                "how_to_verify": "Grep for eval(, exec(, shell=True",
            },
        ],
    },
    "testing": {
        "name": "Testing",
        "description": "Test coverage, CI pipeline, test quality",
        "scan_paths": [KG_MCP_DIR / "tests", REPO_ROOT / ".github"],
        "checklist": [
            {
                "id": "T1",
                "check": "Test files exist for all major modules (server, search, config, tools)",
                "severity": "CRITICAL",
                "how_to_verify": "List mcp_server/*.py, check corresponding tests/test_*.py exists",
            },
            {
                "id": "T2",
                "check": "CI enforces coverage threshold (--cov-fail-under)",
                "severity": "CRITICAL",
                "how_to_verify": "Read .github/workflows/ci.yml, find pytest-cov configuration",
            },
            {
                "id": "T3",
                "check": "No excessive pytest.skip() that silently bypasses tests",
                "severity": "HIGH",
                "how_to_verify": "Grep for pytest.skip in test files, count occurrences",
            },
            {
                "id": "T4",
                "check": "Tests verify behavior, not just existence (assertions on return values)",
                "severity": "HIGH",
                "how_to_verify": "Read test files, check assert statements test actual functionality",
            },
            {
                "id": "T5",
                "check": "Integration tests for key workflows (config→server→tool dispatch)",
                "severity": "MEDIUM",
                "how_to_verify": "Look for tests that span multiple modules",
            },
            {
                "id": "T6",
                "check": "CI runs on multiple Python versions or platforms",
                "severity": "LOW",
                "how_to_verify": "Check CI workflow for matrix strategy",
            },
        ],
    },
    "architecture": {
        "name": "Architecture",
        "description": "Module separation, extensibility, pipeline design",
        "scan_paths": [MCP_SERVER_DIR],
        "checklist": [
            {
                "id": "A1",
                "check": "Clear module boundaries — no circular imports",
                "severity": "HIGH",
                "how_to_verify": "Check import chains between modules",
            },
            {
                "id": "A2",
                "check": "Tool dispatch uses registry pattern (not long if/elif chains)",
                "severity": "MEDIUM",
                "how_to_verify": "Read server.py call_tool/list_tools implementation",
            },
            {
                "id": "A3",
                "check": "Config is centralized — no scattered os.getenv() calls",
                "severity": "MEDIUM",
                "how_to_verify": "Grep for os.getenv outside of config.py",
            },
            {
                "id": "A4",
                "check": "Pipeline stages are composable and independently testable",
                "severity": "HIGH",
                "how_to_verify": "Check if search pipeline stages can be instantiated/tested alone",
            },
            {
                "id": "A5",
                "check": "Error boundaries exist between pipeline stages",
                "severity": "MEDIUM",
                "how_to_verify": "Check if stage failures are caught and don't crash the pipeline",
            },
        ],
    },
    "documentation": {
        "name": "Documentation",
        "description": "README, API docs, inline docs, contribution guide",
        "scan_paths": [REPO_ROOT],
        "checklist": [
            {
                "id": "D1",
                "check": "README.md has quickstart, installation, and usage sections",
                "severity": "HIGH",
                "how_to_verify": "Read README.md, check for ## Installation, ## Usage sections",
            },
            {
                "id": "D2",
                "check": "All MCP tools have docstrings with parameter descriptions",
                "severity": "HIGH",
                "how_to_verify": "Read tool functions in server.py, check docstrings",
            },
            {
                "id": "D3",
                "check": "Configuration options are documented with defaults and examples",
                "severity": "MEDIUM",
                "how_to_verify": "Check if README or docs/ explain config options",
            },
            {
                "id": "D4",
                "check": "CHANGELOG.md is maintained with recent changes",
                "severity": "MEDIUM",
                "how_to_verify": "Read CHANGELOG.md, check for recent dates",
            },
            {
                "id": "D5",
                "check": "CONTRIBUTING.md has development setup and PR process",
                "severity": "LOW",
                "how_to_verify": "Read CONTRIBUTING.md for dev setup instructions",
            },
        ],
    },
    "packaging": {
        "name": "Packaging",
        "description": "Dependencies, install scripts, version management",
        "scan_paths": [KG_MCP_DIR, REPO_ROOT],
        "checklist": [
            {
                "id": "P1",
                "check": "Dependencies pinned with version ranges (not exact, not unbounded)",
                "severity": "HIGH",
                "how_to_verify": "Read requirements.txt, check for >= and < bounds",
            },
            {
                "id": "P2",
                "check": "install.sh has --help flag and error handling",
                "severity": "MEDIUM",
                "how_to_verify": "Read install.sh, check for help and set -e",
            },
            {
                "id": "P3",
                "check": "No deprecated dependencies (google-generativeai → google-genai)",
                "severity": "CRITICAL",
                "how_to_verify": "Check requirements.txt for known deprecated packages",
            },
            {
                "id": "P4",
                "check": "pyproject.toml or setup.py exists with proper metadata",
                "severity": "MEDIUM",
                "how_to_verify": "Check for pyproject.toml existence and content",
            },
            {
                "id": "P5",
                "check": "License file matches license in package metadata",
                "severity": "LOW",
                "how_to_verify": "Compare LICENSE file with pyproject.toml license field",
            },
        ],
    },
    "ux": {
        "name": "User Experience",
        "description": "CLI experience, error messages, onboarding",
        "scan_paths": [KG_MCP_DIR, REPO_ROOT],
        "checklist": [
            {
                "id": "UX1",
                "check": "First-run experience is smooth (install → configure → run)",
                "severity": "HIGH",
                "how_to_verify": "Follow README quickstart as a new user",
            },
            {
                "id": "UX2",
                "check": "Error messages include actionable suggestions",
                "severity": "MEDIUM",
                "how_to_verify": "Check error handlers for 'try this' or 'check that' messages",
            },
            {
                "id": "UX3",
                "check": "CLI has consistent --help output for all commands",
                "severity": "MEDIUM",
                "how_to_verify": "Run install.sh --help, check other entry points",
            },
            {
                "id": "UX4",
                "check": "Skill discovery is clear (users can find available tools)",
                "severity": "HIGH",
                "how_to_verify": "Check if tool listing is documented or discoverable",
            },
            {
                "id": "UX5",
                "check": "Progress indicators for long-running operations",
                "severity": "LOW",
                "how_to_verify": "Check if sync/search operations show progress",
            },
        ],
    },
}


def generate_review_template(perspective_id: str) -> dict:
    """Generate a review template for Claude Code to fill in."""
    if perspective_id not in PERSPECTIVES:
        print(f"Error: Unknown perspective '{perspective_id}'", file=sys.stderr)
        print(f"Available: {', '.join(PERSPECTIVES.keys())}", file=sys.stderr)
        sys.exit(1)

    p = PERSPECTIVES[perspective_id]
    return {
        "perspective": perspective_id,
        "name": p["name"],
        "description": p["description"],
        "scan_paths": [str(sp) for sp in p["scan_paths"]],
        "checklist": [
            {
                "id": item["id"],
                "check": item["check"],
                "severity": item["severity"],
                "how_to_verify": item["how_to_verify"],
                "status": "PENDING",  # Claude Code fills: PASS / FAIL / PARTIAL
                "finding": "",  # Claude Code fills with specific findings
                "files_checked": [],  # Claude Code lists files examined
            }
            for item in p["checklist"]
        ],
        "instructions": (
            "Fill in each checklist item:\n"
            "1. Read the files listed in scan_paths\n"
            "2. For each check, follow how_to_verify\n"
            "3. Set status to PASS, FAIL, or PARTIAL\n"
            "4. Write specific findings (file:line references)\n"
            "5. List files you examined in files_checked\n"
            "6. Do not add a top-level score field; save_review computes computed_score from checklist status"
        ),
    }


def compute_checklist_score(checklist: list[dict]) -> int:
    """Compute the canonical 0-10 review score from checklist states."""
    total_items = len(checklist)
    if total_items == 0:
        return 0

    passed = sum(1 for item in checklist if item.get("status") == "PASS")
    partial = sum(1 for item in checklist if item.get("status") == "PARTIAL")
    return round((passed + partial * 0.5) / total_items * 10)


def determine_review_status(checklist: list[dict], issues: list[dict], blockers: list[str]) -> str:
    """Translate checklist results into the S03 stage status enum."""
    if blockers:
        return "invalid"

    if any(issue.get("severity") == "CRITICAL" for issue in issues):
        return "fail"

    if any(item.get("status") == "FAIL" for item in checklist):
        return "warn"

    if any(item.get("status") == "PARTIAL" for item in checklist):
        return "warn"

    return "pass"


def save_review(perspective_id: str, review_data: dict):
    """Save completed review to artifacts/reviews/."""
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REVIEWS_DIR / f"review_{perspective_id}.json"
    reviewed_at = datetime.now(UTC)
    reviewed_at_iso = reviewed_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    artifact_suffix = reviewed_at.strftime("%Y%m%dT%H%M%SZ")

    # Convert to standard format compatible with orchestrator
    issues = []
    for item in review_data.get("checklist", []):
        if item.get("status") in ("FAIL", "PARTIAL"):
            issues.append({
                "severity": item["severity"],
                "file": ", ".join(item.get("files_checked", [])) or "N/A",
                "description": item.get("finding", item["check"]),
            })

    checklist = review_data.get("checklist", [])
    computed_score = compute_checklist_score(checklist)
    blockers = []
    manual_score_input = review_data.get("score")
    if manual_score_input is not None:
        blockers.append("manual_score_override_ignored")

    output_body = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "quality_review_perspective",
        "artifact_id": f"review_{perspective_id}_{artifact_suffix}",
        "run_id": f"review_{artifact_suffix}",
        "stage_id": "quality_review",
        "perspective": perspective_id,
        "status": determine_review_status(checklist, issues, blockers),
        "computed_score": computed_score,
        "max_score": 10,
        "judge_mode": "self_checklist",
        "issues": issues,
        "summary": review_data.get("summary", ""),
        "narrative": review_data.get("summary", ""),
        "checklist_detail": checklist,
        "reviewed_at": reviewed_at_iso,
        "reviewer": "claude-code-self-review",
        "manual_score_input": manual_score_input,
        "warnings": [],
        "blockers": blockers,
        "git_commit": git_commit(REPO_ROOT),
        "git_tree_state": git_tree_state(REPO_ROOT),
        "inputs_hash": hash_inputs(
            {
                "perspective": perspective_id,
                "checklist": checklist,
                "summary": review_data.get("summary", ""),
            }
        ),
    }
    output = {**output_body, "content_hash": hash_json_payload(output_body)}

    atomic_write_json(output_path, output)
    print(f"  Review saved: {output_path}", file=sys.stderr)
    return output


def list_perspectives():
    """List all available review perspectives."""
    print("\nAvailable Review Perspectives:", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    for pid, p in PERSPECTIVES.items():
        items = len(p["checklist"])
        print(f"  {pid:20s} — {p['name']} ({items} checks)", file=sys.stderr)
        print(f"  {'':20s}   {p['description']}", file=sys.stderr)
    print(f"\nUse: --perspective <name> or --perspective all", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Ralph Loop v5 — Self Review Framework")
    parser.add_argument("--perspective", type=str, help="Review perspective (or 'all')")
    parser.add_argument("--list", action="store_true", help="List available perspectives")
    parser.add_argument("--template", action="store_true",
                        help="Output review template JSON (for Claude Code to fill)")
    parser.add_argument("--save", type=str, help="Path to completed review JSON to save")
    args = parser.parse_args()

    if args.list:
        list_perspectives()
        return

    if not args.perspective:
        parser.print_help()
        return

    if args.perspective == "all":
        perspectives = list(PERSPECTIVES.keys())
    else:
        perspectives = [args.perspective]

    for pid in perspectives:
        if pid not in PERSPECTIVES:
            print(f"Error: Unknown perspective '{pid}'", file=sys.stderr)
            continue

        if args.template:
            template = generate_review_template(pid)
            print(json.dumps(template, indent=2, ensure_ascii=False))
        elif args.save:
            # Load completed review from file
            review_data = json.loads(Path(args.save).read_text())
            save_review(pid, review_data)
        else:
            # Default: output template for Claude Code to use
            template = generate_review_template(pid)
            print(json.dumps(template, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
