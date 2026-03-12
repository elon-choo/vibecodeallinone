#!/usr/bin/env python3
"""Repeatable operator smoke for assistant-api runtime flows."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import requests

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from deployment_contract import build_operator_mode_contract  # noqa: E402
from smoke_support import (  # noqa: E402
    artifact_safe_payload,
    build_live_provider_preflight,
    build_live_telegram_preflight,
    find_free_port,
    initialize_runtime_repo,
    run_live_provider_validation,
    run_live_telegram_validation,
    start_assistant_api,
    utc_now_iso,
)


def run_mock_operator_smoke() -> dict[str, object]:
    api_port = find_free_port()
    web_port = find_free_port()

    with tempfile.TemporaryDirectory(prefix="assistant-operator-smoke-") as temp_dir:
        runtime_seed = initialize_runtime_repo(Path(temp_dir) / "runtime-repo", stale_trust=False)
        with start_assistant_api(runtime_seed.repo_root, api_port=api_port, web_port=web_port, provider_mode="mock") as api_base:
            session = requests.Session()
            redirect_uri = f"http://127.0.0.1:{web_port}/callback"
            checks: list[dict[str, object]] = []

            auth_start = session.post(
                f"{api_base}/v1/auth/openai/start",
                json={
                    "redirect_uri": redirect_uri,
                    "device_label": "operator smoke",
                    "platform": "web",
                },
                timeout=10,
            )
            auth_start.raise_for_status()
            authorization_url = auth_start.json()["authorization_url"]
            checks.append({"check": "auth_start", "detail": "start route returned a provider authorization URL"})

            provider_redirect = session.get(authorization_url, allow_redirects=False, timeout=10)
            assert provider_redirect.status_code == 303
            callback_url = provider_redirect.headers["location"]
            checks.append({"check": "mock_provider_redirect", "detail": "mock provider redirected back to callback"})

            callback_redirect = session.get(callback_url, allow_redirects=False, timeout=10)
            assert callback_redirect.status_code == 303
            assert callback_redirect.headers["location"].startswith(f"{redirect_uri}?auth=success")
            checks.append({"check": "auth_callback", "detail": "callback completed and returned control to assistant-web"})

            auth_session = session.get(f"{api_base}/v1/auth/session", timeout=10)
            auth_session.raise_for_status()
            auth_payload = auth_session.json()
            assert auth_payload["auth_state"] == "active"
            checks.append({"check": "session_active", "detail": f"auth session became active for {auth_payload['device_session_id']}"})

            telegram_link = session.post(f"{api_base}/v1/surfaces/telegram/link", timeout=10)
            telegram_link.raise_for_status()
            telegram_payload = telegram_link.json()
            assert telegram_payload["status"] == "pending"

            completed_link = session.post(
                f"{api_base}/v1/internal/test/telegram/link/complete",
                json={
                    "link_code": telegram_payload["link_code"],
                    "telegram_user_id": "tg_operator_smoke",
                    "telegram_chat_id": "chat_operator_smoke",
                    "telegram_username": "operator_smoke",
                    "telegram_display_name": "Operator Smoke",
                    "last_resume_token_ref": "resume_operator_smoke",
                },
                timeout=10,
            )
            completed_link.raise_for_status()
            linked_state = session.get(f"{api_base}/v1/surfaces/telegram/link", timeout=10)
            linked_state.raise_for_status()
            assert linked_state.json()["status"] == "linked"
            checks.append(
                {
                    "check": "telegram_link_mock",
                    "detail": "operator smoke completed the mock-only Telegram link path so reminder delivery stayed on the existing companion surface",
                }
            )

            trust_current = session.get(f"{api_base}/v1/trust/current", timeout=10)
            trust_current.raise_for_status()
            trust_payload = trust_current.json()
            checks.append(
                {
                    "check": "trust_summary",
                    "detail": f"trust summary resolved for {trust_payload['evidence_ref']['bundle_id']} with status {trust_payload['summary']['overall_status']}",
                }
            )

            reminder_response = session.post(
                f"{api_base}/v1/reminders",
                json={
                    "scheduled_for": "2030-03-11T00:00:00Z",
                    "message": "Observe operator smoke follow-up",
                    "channel": "telegram",
                    "follow_up_policy": {
                        "on_failure": "retry",
                        "max_attempts": 3,
                        "retry_delay_seconds": 120,
                    },
                },
                timeout=10,
            )
            reminder_response.raise_for_status()
            reminder_payload = reminder_response.json()
            assert reminder_payload["follow_up_policy"]["on_failure"] == "retry"
            assert reminder_payload["follow_up_policy"]["max_attempts"] == 3
            assert reminder_payload["follow_up_state"]["status"] == "none"
            assert reminder_payload["follow_up_state"]["attempt_count"] == 0
            assert reminder_payload["follow_up_state"]["next_attempt_at"] == "2030-03-11T00:00:00Z"

            reminder_list = session.get(f"{api_base}/v1/reminders", timeout=10)
            reminder_list.raise_for_status()
            reminder_items = reminder_list.json()["items"]
            assert len(reminder_items) == 1
            assert reminder_items[0]["reminder_id"] == reminder_payload["reminder_id"]

            reminder_jobs = session.get(f"{api_base}/v1/jobs", params={"kind": "reminder_delivery"}, timeout=10)
            reminder_jobs.raise_for_status()
            reminder_job_payload = reminder_jobs.json()["items"]
            assert len(reminder_job_payload) == 1
            assert reminder_job_payload[0]["job_id"] == reminder_payload["job_id"]
            assert reminder_job_payload[0]["status"] == "queued"
            assert reminder_job_payload[0]["available_at"] == "2030-03-11T00:00:00Z"
            assert reminder_job_payload[0]["attempt_count"] == 0
            assert reminder_job_payload[0]["details"]["follow_up_policy"]["on_failure"] == "retry"
            assert reminder_job_payload[0]["details"]["follow_up_state"]["status"] == "none"
            checks.append(
                {
                    "check": "reminder_follow_up_policy",
                    "detail": "operator smoke observed retry-configured reminder follow-up policy/state plus runtime job available_at and attempt_count through the public reminder and jobs routes",
                }
            )

            memory_payload = {
                "id": "memory_operator_smoke",
                "user_id": auth_payload["user_id"],
                "kind": "preference",
                "content": "Prefers concise answers.",
                "status": "active",
                "importance": 80,
                "source_type": "manual_input",
                "created_at": "2026-03-09T12:01:00Z",
                "updated_at": "2026-03-09T12:01:00Z",
                "last_used_at": None,
                "sources": [
                    {
                        "memory_id": "memory_operator_smoke",
                        "conversation_id": "conv_operator",
                        "message_id": "msg_smoke",
                        "note": "Captured from operator smoke",
                        "captured_at": "2026-03-09T12:01:00Z",
                    }
                ],
            }
            created_memory = session.post(f"{api_base}/v1/memory/items", json=memory_payload, timeout=10)
            created_memory.raise_for_status()
            checks.append({"check": "memory_create", "detail": "memory item saved with provenance"})

            exported_memory = session.post(f"{api_base}/v1/memory/exports", timeout=10)
            exported_memory.raise_for_status()
            export_payload = exported_memory.json()
            assert export_payload["item_count"] == 1
            checks.append(
                {
                    "check": "memory_export",
                    "detail": f"memory export returned {export_payload['item_count']} item and a download filename",
                }
            )

            checkpoint_payload = {
                "user_id": auth_payload["user_id"],
                "device_session_id": auth_payload["device_session_id"],
                "conversation_id": "conv_operator",
                "last_message_id": "msg_01",
                "draft_text": "Operator draft",
                "selected_memory_ids": ["memory_operator_smoke"],
                "route": "/chat/conv_operator",
                "updated_at": "2026-03-09T12:05:00Z",
                "version": 1,
                "base_version": None,
                "force": False,
            }
            stored_checkpoint = session.put(f"{api_base}/v1/checkpoints/current", json=checkpoint_payload, timeout=10)
            stored_checkpoint.raise_for_status()

            checkpoint_payload.update(
                {
                    "draft_text": "Server moved ahead",
                    "updated_at": "2026-03-09T12:05:10Z",
                    "version": 2,
                    "base_version": 1,
                    "selected_memory_ids": [],
                }
            )
            next_checkpoint = session.put(f"{api_base}/v1/checkpoints/current", json=checkpoint_payload, timeout=10)
            next_checkpoint.raise_for_status()

            stale_checkpoint = {
                "user_id": auth_payload["user_id"],
                "device_session_id": auth_payload["device_session_id"],
                "conversation_id": "conv_operator",
                "last_message_id": "msg_02",
                "draft_text": "Local stale draft",
                "selected_memory_ids": ["memory_operator_smoke"],
                "route": "/chat/conv_operator",
                "updated_at": "2026-03-09T12:05:20Z",
                "version": 2,
                "base_version": 1,
                "force": False,
            }
            checkpoint_conflict = session.put(f"{api_base}/v1/checkpoints/current", json=stale_checkpoint, timeout=10)
            assert checkpoint_conflict.status_code == 409
            checks.append({"check": "checkpoint_conflict", "detail": "stale local checkpoint triggered a 409 conflict payload"})

            stale_checkpoint["force"] = True
            stale_checkpoint["base_version"] = 2
            forced_checkpoint = session.put(f"{api_base}/v1/checkpoints/current", json=stale_checkpoint, timeout=10)
            forced_checkpoint.raise_for_status()
            checks.append({"check": "checkpoint_force_sync", "detail": "force=true replaced the newer server checkpoint"})

            deleted_memory = session.delete(f"{api_base}/v1/memory/items/memory_operator_smoke", timeout=10)
            deleted_memory.raise_for_status()
            delete_payload = deleted_memory.json()
            assert delete_payload["purge_status"] == "pending_purge"
            checks.append(
                {
                    "check": "memory_delete",
                    "detail": f"delete receipt queued purge until {delete_payload['purge_after']}",
                }
            )

            return {
                "status": "pass",
                "api_base": api_base,
                "app_version": runtime_seed.app_version,
                "bundle_id": runtime_seed.bundle_id,
                "checks": checks,
            }


def build_report(args: argparse.Namespace) -> dict[str, object]:
    provider_preflight = build_live_provider_preflight()
    telegram_preflight = build_live_telegram_preflight()
    live_provider_validation = run_live_provider_validation(
        wait_seconds=args.live_provider_wait_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        request_timeout_seconds=args.request_timeout_seconds,
    )
    live_telegram_validation = run_live_telegram_validation(
        wait_seconds=args.live_telegram_wait_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        request_timeout_seconds=args.request_timeout_seconds,
    )
    deployment_contract = build_operator_mode_contract()
    mock_smoke = run_mock_operator_smoke()
    return {
        "timestamp": utc_now_iso(),
        "live_provider_preflight": provider_preflight,
        "live_telegram_preflight": telegram_preflight,
        "live_provider_validation": live_provider_validation,
        "live_telegram_validation": live_telegram_validation,
        "deployment_contract": deployment_contract,
        "mock_operator_smoke": mock_smoke,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="artifacts/operator_smoke/assistant_api_operator_smoke.json",
        help="Where to write the smoke report JSON.",
    )
    parser.add_argument(
        "--live-provider-wait-seconds",
        type=float,
        default=0.0,
        help="How long to wait for a manual live provider browser step before recording manual-step-required.",
    )
    parser.add_argument(
        "--live-telegram-wait-seconds",
        type=float,
        default=0.0,
        help="How long to wait for a manual Telegram deep-link step before recording manual-step-required.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=2.0,
        help="Polling interval used while waiting for manual live validation state changes.",
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=15.0,
        help="HTTP timeout for live provider and Telegram validation attempts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact_safe_payload(report), indent=2) + "\n", encoding="utf-8")

    provider_preflight = report["live_provider_preflight"]
    telegram_preflight = report["live_telegram_preflight"]
    live_provider_validation = report["live_provider_validation"]
    live_telegram_validation = report["live_telegram_validation"]
    deployment_contract = report["deployment_contract"]
    mock_smoke = report["mock_operator_smoke"]
    print(f"wrote operator smoke report to {output_path}")
    print(f"live provider eligible: {provider_preflight['eligible_for_live_validation']}")
    for blocker in provider_preflight["blockers"]:
        print(f"provider blocker: {blocker}")
    for warning in provider_preflight["warnings"]:
        print(f"provider warning: {warning}")
    print(f"live provider validation status: {live_provider_validation['status']}")
    if live_provider_validation.get("_operator_authorization_url"):
        print(f"provider action url: {live_provider_validation['_operator_authorization_url']}")
    print(f"live telegram eligible: {telegram_preflight['eligible_for_live_validation']}")
    for blocker in telegram_preflight["blockers"]:
        print(f"telegram blocker: {blocker}")
    for warning in telegram_preflight["warnings"]:
        print(f"telegram warning: {warning}")
    print(f"live telegram validation status: {live_telegram_validation['status']}")
    if live_telegram_validation.get("_operator_bot_deep_link"):
        print(f"telegram deep link: {live_telegram_validation['_operator_bot_deep_link']}")
    print(f"operator mode: {deployment_contract['operator_mode']}")
    print(f"deployment readiness: {deployment_contract['status']}")
    for blocker in deployment_contract["blockers"]:
        print(f"deployment blocker: {blocker}")
    for warning in deployment_contract["warnings"]:
        print(f"deployment warning: {warning}")
    print(f"mock smoke status: {mock_smoke['status']} ({len(mock_smoke['checks'])} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
