#!/usr/bin/env python3
"""Attempt live Telegram operator validation against the configured assistant runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from smoke_support import (  # noqa: E402
    artifact_safe_payload,
    build_live_provider_preflight,
    build_live_telegram_preflight,
    run_live_telegram_validation,
    utc_now_iso,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="artifacts/telegram_smoke/assistant_api_telegram_live_validation.json",
        help="Where to write the live Telegram validation JSON report.",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=0.0,
        help="How long to wait for the manual Telegram deep-link step before recording manual-step-required.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=2.0,
        help="Polling interval used while waiting for live Telegram link completion.",
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=15.0,
        help="HTTP timeout for live Telegram validation requests.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    provider_preflight = build_live_provider_preflight()
    telegram_preflight = build_live_telegram_preflight()
    telegram_validation = run_live_telegram_validation(
        wait_seconds=args.wait_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        request_timeout_seconds=args.request_timeout_seconds,
    )

    report = {
        "timestamp": utc_now_iso(),
        "live_provider_preflight": provider_preflight,
        "live_telegram_preflight": telegram_preflight,
        "live_telegram_validation": telegram_validation,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact_safe_payload(report), indent=2) + "\n", encoding="utf-8")

    print(f"wrote live Telegram validation report to {output_path}")
    print(f"live telegram eligible: {telegram_preflight['eligible_for_live_validation']}")
    for blocker in telegram_preflight["blockers"]:
        print(f"telegram blocker: {blocker}")
    for warning in telegram_preflight["warnings"]:
        print(f"telegram warning: {warning}")
    print(f"live telegram validation status: {telegram_validation['status']}")
    if telegram_validation.get("_operator_bot_deep_link"):
        print(f"telegram deep link: {telegram_validation['_operator_bot_deep_link']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
