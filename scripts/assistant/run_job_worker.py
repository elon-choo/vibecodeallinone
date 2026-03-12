#!/usr/bin/env python3
"""Run the assistant-api background worker."""

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
from assistant_api.worker import RuntimeJobWorker  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the assistant-api runtime job worker.")
    parser.add_argument("--once", action="store_true", help="claim and execute at most one runnable job")
    parser.add_argument("--max-jobs", type=int, default=None, help="stop after executing this many jobs")
    parser.add_argument("--worker-id", default=None, help="override the generated worker identifier")
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
    worker = RuntimeJobWorker(settings, worker_id=args.worker_id)
    processed_jobs = worker.run(once=args.once, max_jobs=args.max_jobs)
    print(f"processed_jobs={processed_jobs} worker_id={worker.worker_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
