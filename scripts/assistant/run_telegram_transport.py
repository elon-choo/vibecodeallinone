#!/usr/bin/env python3
"""Run the assistant-api Telegram polling transport."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE_ROOT = REPO_ROOT / "services" / "assistant-api"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from assistant_api.config import Settings  # noqa: E402
from assistant_api.telegram_transport import TelegramPollingRuntime  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the assistant-api Telegram polling transport.")
    parser.add_argument("--once", action="store_true", help="perform a single getUpdates polling pass")
    parser.add_argument("--max-batches", type=int, default=None, help="stop after this many polling batches")
    parser.add_argument(
        "--cursor-name",
        default="telegram_polling",
        help="cursor key used to persist the Telegram polling offset",
    )
    parser.add_argument(
        "--idle-sleep-seconds",
        type=float,
        default=0.0,
        help="optional sleep between empty polling batches",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="standard library logging level",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(name)s %(message)s")

    settings = Settings.from_env()
    runtime = TelegramPollingRuntime(
        settings,
        cursor_name=args.cursor_name,
        idle_sleep_seconds=args.idle_sleep_seconds,
    )
    processed_updates = runtime.run(once=args.once, max_batches=args.max_batches)
    print(f"processed_updates={processed_updates} cursor_name={args.cursor_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
