#!/usr/bin/env python3
"""Structured install smoke wrapper for release evidence."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from smoke_support import REPO_ROOT, utc_now_iso, write_json  # noqa: E402


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="artifacts/install_smoke/assistant_runtime_install_smoke.json",
        help="Where to write the install smoke report JSON.",
    )
    return parser.parse_args()


def _build_checks(stdout_lines: list[str]) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    for line in stdout_lines:
        if line == "PASS: All 12 skills installed with SKILL.md":
            checks.append(
                {
                    "check": "developer_toolkit_install",
                    "detail": "Tier 1 developer toolkit install created all 12 skills with SKILL.md.",
                }
            )
        elif line == "PASS: Assistant runtime bootstrap scaffold created":
            checks.append(
                {
                    "check": "assistant_runtime_bootstrap",
                    "detail": "Assistant runtime bootstrap scaffold created the expected env file, launchers, and directories.",
                }
            )
        elif line == "PASS: Managed quickstart operator bootstrap scaffold created":
            checks.append(
                {
                    "check": "managed_quickstart_operator_bootstrap",
                    "detail": "Managed quickstart operator bootstrap created a workspace with the shared controller, placeholder env contract, and readiness/status surface.",
                }
            )
        elif line == "PASS: Assistant reference stack start/stop works":
            checks.append(
                {
                    "check": "assistant_reference_stack",
                    "detail": "Bootstrapped runtime workspace started and stopped the API, web, and worker stack with one command while reporting Telegram status plus operator-mode readiness.",
                }
            )
    return checks


def _clean_lines(raw_output: str) -> list[str]:
    return [ANSI_ESCAPE_RE.sub("", line) for line in raw_output.splitlines()]


def main() -> int:
    args = parse_args()
    command = ["bash", "tests/test_install_smoke.sh"]
    started_at = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    stdout_lines = _clean_lines(result.stdout)
    stderr_lines = _clean_lines(result.stderr)
    checks = _build_checks(stdout_lines)

    report = {
        "timestamp": utc_now_iso(),
        "status": "pass" if result.returncode == 0 else "fail",
        "command": " ".join(command),
        "exit_code": result.returncode,
        "duration_ms": duration_ms,
        "checks": checks,
        "stdout_tail": stdout_lines[-20:],
        "stderr_tail": stderr_lines[-20:],
    }

    output_path = Path(args.output)
    write_json(output_path, report)
    print(f"wrote install smoke report to {output_path}")

    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return result.returncode

    print(f"install smoke status: {report['status']} ({len(checks)} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
