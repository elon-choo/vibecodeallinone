#!/usr/bin/env python3
"""Repeatable Telegram mock smoke for assistant-api continuity flows."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import requests

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parents[1]
SERVICE_ROOT = REPO_ROOT / "services" / "assistant-api"
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from assistant_api.config import Settings  # noqa: E402
from assistant_api.telegram_transport import TelegramPollingRuntime  # noqa: E402
from smoke_support import (  # noqa: E402
    find_free_port,
    initialize_runtime_repo,
    start_assistant_api,
    utc_now_iso,
    write_json,
)


class RecordingTelegramBotClient:
    def __init__(self, updates: list[dict[str, object]]):
        self._updates = list(updates)
        self.sent_messages: list[dict[str, str]] = []

    def get_updates(
        self,
        *,
        offset: int,
        timeout_seconds: int,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        del timeout_seconds
        matching_updates = [
            update
            for update in self._updates
            if isinstance(update.get("update_id"), int) and int(update["update_id"]) >= offset
        ]
        return matching_updates[:limit]

    def send_message(self, *, chat_id: str, text: str) -> None:
        self.sent_messages.append({"chat_id": chat_id, "text": text})


def make_runtime_settings(runtime_repo_root: Path, *, api_port: int, web_port: int) -> Settings:
    return Settings(
        repo_root=runtime_repo_root,
        artifacts_dir=runtime_repo_root / "artifacts",
        db_path=runtime_repo_root / "assistant_api.sqlite3",
        migration_path=SERVICE_ROOT / "migrations" / "0001_bootstrap.sql",
        app_version="2.0.0",
        release_channel="internal",
        cookie_name="assistant_session",
        assistant_api_public_base_url=f"http://127.0.0.1:{api_port}",
        web_allowed_origins=(f"http://127.0.0.1:{web_port}",),
        provider_mode="mock",
        provider_client_id="assistant-bootstrap-client",
        provider_client_secret=None,
        provider_token_url=None,
        provider_userinfo_url=None,
        provider_scopes=("openid", "profile", "email", "offline_access"),
        provider_authorization_base_url="https://auth.openai.com/oauth/authorize",
        telegram_bot_token="smoke-bot-token",
        telegram_bot_username="smoke_assistant_bot",
        telegram_bot_deep_link_base_url=None,
        telegram_api_base_url="https://api.telegram.org",
        telegram_link_ttl_seconds=900,
        telegram_poll_timeout_seconds=5,
        memory_delete_retention_seconds=0,
        worker_poll_interval_seconds=0.01,
        worker_job_lease_seconds=30,
        secure_cookies=False,
        session_ttl_seconds=3600,
    )


def extract_start_token(bot_deep_link: str) -> str:
    query = parse_qs(urlsplit(bot_deep_link).query)
    return query["start"][0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="artifacts/telegram_smoke/assistant_api_telegram_mock_smoke.json",
        help="Where to write the Telegram mock smoke report JSON.",
    )
    return parser.parse_args()


def run_mock_telegram_smoke() -> dict[str, object]:
    api_port = find_free_port()
    web_port = find_free_port()

    with tempfile.TemporaryDirectory(prefix="assistant-telegram-smoke-") as temp_dir:
        runtime_seed = initialize_runtime_repo(Path(temp_dir) / "runtime-repo", stale_trust=False)
        with start_assistant_api(
            runtime_seed.repo_root,
            api_port=api_port,
            web_port=web_port,
            provider_mode="mock",
            telegram_bot_username="smoke_assistant_bot",
        ) as api_base:
            session = requests.Session()
            redirect_uri = f"http://127.0.0.1:{web_port}/callback"
            checks: list[dict[str, object]] = []

            auth_start = session.post(
                f"{api_base}/v1/auth/openai/start",
                json={
                    "redirect_uri": redirect_uri,
                    "device_label": "telegram smoke",
                    "platform": "web",
                },
                timeout=10,
            )
            auth_start.raise_for_status()
            provider_redirect = session.get(auth_start.json()["authorization_url"], allow_redirects=False, timeout=10)
            assert provider_redirect.status_code == 303
            callback_redirect = session.get(provider_redirect.headers["location"], allow_redirects=False, timeout=10)
            assert callback_redirect.status_code == 303
            auth_session = session.get(f"{api_base}/v1/auth/session", timeout=10)
            auth_session.raise_for_status()
            session_payload = auth_session.json()
            assert session_payload["auth_state"] == "active"
            checks.append(
                {
                    "check": "auth_round_trip",
                    "detail": f"mock auth round trip completed for {session_payload['device_session_id']}",
                }
            )

            initial_link_state = session.get(f"{api_base}/v1/surfaces/telegram/link", timeout=10)
            initial_link_state.raise_for_status()
            assert initial_link_state.json()["status"] == "not_linked"
            checks.append(
                {
                    "check": "telegram_unlinked_state",
                    "detail": "Telegram companion state starts as not_linked before a link code is issued.",
                }
            )

            link_start = session.post(f"{api_base}/v1/surfaces/telegram/link", timeout=10)
            link_start.raise_for_status()
            link_payload = link_start.json()
            assert link_payload["status"] == "pending"
            assert link_payload["link_code"]
            assert link_payload["bot_deep_link"]
            checks.append(
                {
                    "check": "telegram_link_start",
                    "detail": f"Telegram link entered pending state with link code {link_payload['link_code']}.",
                }
            )

            runtime_settings = make_runtime_settings(runtime_seed.repo_root, api_port=api_port, web_port=web_port)
            link_runtime_bot = RecordingTelegramBotClient(
                [
                    {
                        "update_id": 501,
                        "message": {
                            "message_id": 1,
                            "text": f"/start {extract_start_token(link_payload['bot_deep_link'])}",
                            "chat": {"id": 9901, "type": "private"},
                            "from": {
                                "id": 8801,
                                "username": "powerpack",
                                "first_name": "Power",
                                "last_name": "Pack",
                            },
                        },
                    }
                ]
            )
            link_runtime = TelegramPollingRuntime(
                runtime_settings,
                bot_client=link_runtime_bot,
                cursor_name="telegram_smoke_runtime",
            )
            assert link_runtime.run_once() == 1

            linked_state = session.get(f"{api_base}/v1/surfaces/telegram/link", timeout=10)
            linked_state.raise_for_status()
            linked_payload = linked_state.json()
            assert linked_payload["status"] == "linked"
            assert linked_payload["telegram_username"] == "powerpack"
            assert linked_payload["last_resume_token_ref"].startswith("resume_tg_")
            checks.append(
                {
                    "check": "telegram_link_complete",
                    "detail": "Polling runtime completed the Telegram link and generated live resume metadata.",
                }
            )

            checks.append(
                {
                    "check": "telegram_link_state_refresh",
                    "detail": "Telegram companion state remains linked when fetched through the public runtime route.",
                }
            )

            stored_resume_checkpoint = session.get(f"{api_base}/v1/checkpoints/current", timeout=10)
            stored_resume_checkpoint.raise_for_status()
            resume_payload = stored_resume_checkpoint.json()
            assert resume_payload["handoff_kind"] == "resume_link"
            assert resume_payload["surface"] == "telegram"
            assert resume_payload["resume_token_ref"] == linked_payload["last_resume_token_ref"]
            checks.append(
                {
                    "check": "resume_handoff_checkpoint",
                    "detail": "Telegram link completion created a real resume_link checkpoint through the runtime path.",
                }
            )

            capture_runtime_bot = RecordingTelegramBotClient(
                [
                    {
                        "update_id": 502,
                        "message": {
                            "message_id": 2,
                            "text": "Quick capture from Telegram",
                            "chat": {"id": 9901, "type": "private"},
                            "from": {
                                "id": 8801,
                                "username": "powerpack",
                                "first_name": "Power",
                                "last_name": "Pack",
                            },
                        },
                    }
                ]
            )
            capture_runtime = TelegramPollingRuntime(
                runtime_settings,
                bot_client=capture_runtime_bot,
                cursor_name="telegram_smoke_runtime",
            )
            assert capture_runtime.run_once() == 1
            checks.append(
                {
                    "check": "quick_capture_checkpoint",
                    "detail": "A Telegram quick capture advanced the continuity record through the polling runtime.",
                }
            )

            current_checkpoint = session.get(f"{api_base}/v1/checkpoints/current", timeout=10)
            current_checkpoint.raise_for_status()
            current_payload = current_checkpoint.json()
            assert current_payload["surface"] == "telegram"
            assert current_payload["handoff_kind"] == "quick_capture"
            assert current_payload["draft_text"] == "Quick capture from Telegram"
            assert current_payload["resume_token_ref"].startswith("resume_tg_")
            checks.append(
                {
                    "check": "continuity_restore_state",
                    "detail": "Public checkpoint readback preserved Telegram surface metadata for resume and quick-capture continuity.",
                }
            )

            return {
                "status": "pass",
                "api_base": api_base,
                "app_version": runtime_seed.app_version,
                "bundle_id": runtime_seed.bundle_id,
                "checks": checks,
            }


def main() -> int:
    args = parse_args()
    report = {
        "timestamp": utc_now_iso(),
        "mock_telegram_smoke": run_mock_telegram_smoke(),
    }
    output_path = Path(args.output)
    write_json(output_path, report)

    smoke_report = report["mock_telegram_smoke"]
    print(f"wrote Telegram mock smoke report to {output_path}")
    print(f"mock smoke status: {smoke_report['status']} ({len(smoke_report['checks'])} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
