"""assistant-api Telegram transport foundation tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).parent.parent
SERVICE_ROOT = REPO_ROOT / "services" / "assistant-api"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from assistant_api.app import create_app  # noqa: E402
from assistant_api.config import Settings  # noqa: E402
from assistant_api.telegram_transport import TelegramPollingRuntime  # noqa: E402


class RecordingTelegramBotClient:
    def __init__(self, updates: list[dict[str, object]]):
        self._updates = list(updates)
        self.get_updates_calls: list[dict[str, int]] = []
        self.sent_messages: list[dict[str, str]] = []

    def get_updates(
        self,
        *,
        offset: int,
        timeout_seconds: int,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        self.get_updates_calls.append(
            {
                "offset": offset,
                "timeout_seconds": timeout_seconds,
                "limit": limit,
            }
        )
        matching_updates = [
            update
            for update in self._updates
            if isinstance(update.get("update_id"), int) and int(update["update_id"]) >= offset
        ]
        return matching_updates[:limit]

    def send_message(self, *, chat_id: str, text: str) -> None:
        self.sent_messages.append({"chat_id": chat_id, "text": text})


def make_settings(repo_root: Path) -> Settings:
    return Settings(
        repo_root=repo_root,
        artifacts_dir=repo_root / "artifacts",
        db_path=repo_root / "assistant_api.sqlite3",
        migration_path=SERVICE_ROOT / "migrations" / "0001_bootstrap.sql",
        app_version="2.0.0",
        release_channel="internal",
        cookie_name="assistant_session",
        assistant_api_public_base_url="http://testserver",
        web_allowed_origins=("http://127.0.0.1:4173",),
        provider_mode="mock",
        provider_client_id="assistant-bootstrap-client",
        provider_client_secret=None,
        provider_token_url=None,
        provider_userinfo_url=None,
        provider_scopes=("openid", "profile", "email", "offline_access"),
        provider_authorization_base_url="https://auth.openai.com/oauth/authorize",
        telegram_bot_token="test-bot-token",
        telegram_bot_username="test_assistant_bot",
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


def request_path(target_url: str) -> str:
    parsed = urlsplit(target_url)
    return f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path


def bootstrap_client(tmp_path: Path) -> TestClient:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "package.json").write_text(json.dumps({"version": "2.0.0"}), encoding="utf-8")

    app = create_app(make_settings(repo_root))
    client = TestClient(app)

    auth_start = client.post(
        "/v1/auth/openai/start",
        json={
            "redirect_uri": "https://assistant-web.local/callback",
            "device_label": "Telegram Tests",
            "platform": "web",
        },
    )
    provider_redirect = client.get(request_path(auth_start.json()["authorization_url"]), follow_redirects=False)
    client.get(request_path(provider_redirect.headers["location"]), follow_redirects=False)
    return client


def extract_start_token(bot_deep_link: str) -> str:
    query = parse_qs(urlsplit(bot_deep_link).query)
    return query["start"][0]


def seed_web_checkpoint(client: TestClient) -> None:
    session_payload = client.get("/v1/auth/session").json()
    created_memory = client.post(
        "/v1/memory/items",
        json={
            "id": "memory_tg_01",
            "user_id": session_payload["user_id"],
            "kind": "task",
            "content": "Follow up on the Telegram capture",
            "status": "active",
            "importance": 70,
            "source_type": "manual_input",
            "created_at": "2026-03-10T00:00:00Z",
            "updated_at": "2026-03-10T00:00:00Z",
            "last_used_at": None,
            "sources": [],
        },
    )
    assert created_memory.status_code == 201

    stored_checkpoint = client.put(
        "/v1/checkpoints/current",
        json={
            "user_id": session_payload["user_id"],
            "device_session_id": session_payload["device_session_id"],
            "conversation_id": "conv_telegram",
            "last_message_id": "msg_web_01",
            "draft_text": "Draft from web",
            "selected_memory_ids": ["memory_tg_01"],
            "route": "/chat/conv_telegram",
            "surface": "web",
            "handoff_kind": "none",
            "resume_token_ref": None,
            "last_surface_at": "2026-03-10T00:00:00Z",
            "updated_at": "2026-03-10T00:00:00Z",
            "version": 1,
            "base_version": None,
            "force": False,
        },
    )
    assert stored_checkpoint.status_code == 200


def test_telegram_polling_runtime_completes_pending_link_and_writes_resume_checkpoint(tmp_path):
    client = bootstrap_client(tmp_path)
    seed_web_checkpoint(client)
    link_payload = client.post("/v1/surfaces/telegram/link").json()
    assert link_payload["bot_deep_link"].startswith("https://t.me/test_assistant_bot?start=")
    link_token = extract_start_token(link_payload["bot_deep_link"])

    bot_client = RecordingTelegramBotClient(
        [
            {
                "update_id": 101,
                "message": {
                    "message_id": 1,
                    "text": f"/start {link_token}",
                    "chat": {"id": 9001, "type": "private"},
                    "from": {
                        "id": 7001,
                        "username": "powerpack",
                        "first_name": "Power",
                        "last_name": "Pack",
                    },
                },
            }
        ]
    )

    runtime = TelegramPollingRuntime(
        client.app.state.settings,
        store=client.app.state.store,
        bot_client=bot_client,
        cursor_name="test_transport_success",
    )

    assert runtime.run_once() == 1
    assert runtime.run_once() == 0

    link_state = client.get("/v1/surfaces/telegram/link").json()
    assert link_state["status"] == "linked"
    assert link_state["is_linked"] is True
    assert link_state["telegram_username"] == "powerpack"
    assert link_state["telegram_display_name"] == "Power Pack"
    assert link_state["last_resume_token_ref"].startswith("resume_tg_")

    checkpoint = client.get("/v1/checkpoints/current").json()
    assert checkpoint["conversation_id"] == "conv_telegram"
    assert checkpoint["route"] == "/chat/conv_telegram"
    assert checkpoint["draft_text"] == "Draft from web"
    assert checkpoint["selected_memory_ids"] == ["memory_tg_01"]
    assert checkpoint["surface"] == "telegram"
    assert checkpoint["handoff_kind"] == "resume_link"
    assert checkpoint["resume_token_ref"] == link_state["last_resume_token_ref"]
    assert checkpoint["version"] == 2

    assert bot_client.sent_messages == [
        {
            "chat_id": "9001",
            "text": "Telegram is linked to your assistant. Return to the web app to continue.",
        }
    ]
    assert bot_client.get_updates_calls[0]["offset"] == 0
    assert bot_client.get_updates_calls[1]["offset"] == 102
    assert client.app.state.store.get_telegram_transport_cursor("test_transport_success") == 102


def test_telegram_polling_runtime_start_without_token_refreshes_resume_handoff(tmp_path):
    client = bootstrap_client(tmp_path)
    seed_web_checkpoint(client)
    link_payload = client.post("/v1/surfaces/telegram/link").json()
    link_token = extract_start_token(link_payload["bot_deep_link"])

    link_runtime = TelegramPollingRuntime(
        client.app.state.settings,
        store=client.app.state.store,
        bot_client=RecordingTelegramBotClient(
            [
                {
                    "update_id": 201,
                    "message": {
                        "message_id": 1,
                        "text": f"/start {link_token}",
                        "chat": {"id": 9201, "type": "private"},
                        "from": {"id": 7201, "username": "resume_user", "first_name": "Resume"},
                    },
                }
            ]
        ),
        cursor_name="test_transport_resume_link",
    )
    assert link_runtime.run_once() == 1
    initial_link_state = client.get("/v1/surfaces/telegram/link").json()
    initial_resume_token = initial_link_state["last_resume_token_ref"]

    bot_client = RecordingTelegramBotClient(
        [
            {
                "update_id": 202,
                "message": {
                    "message_id": 2,
                    "text": "/start",
                    "chat": {"id": 9201, "type": "private"},
                    "from": {"id": 7201, "username": "resume_user", "first_name": "Resume"},
                },
            }
        ]
    )
    runtime = TelegramPollingRuntime(
        client.app.state.settings,
        store=client.app.state.store,
        bot_client=bot_client,
        cursor_name="test_transport_resume_link",
    )

    assert runtime.run_once() == 1

    link_state = client.get("/v1/surfaces/telegram/link").json()
    assert link_state["last_resume_token_ref"].startswith("resume_tg_")
    assert link_state["last_resume_token_ref"] != initial_resume_token

    checkpoint = client.get("/v1/checkpoints/current").json()
    assert checkpoint["handoff_kind"] == "resume_link"
    assert checkpoint["surface"] == "telegram"
    assert checkpoint["resume_token_ref"] == link_state["last_resume_token_ref"]
    assert checkpoint["draft_text"] == "Draft from web"
    assert checkpoint["version"] == 3

    assert bot_client.sent_messages == [
        {
            "chat_id": "9201",
            "text": "Resume is ready in the web app. Return there to continue.",
        }
    ]
    assert client.app.state.store.get_telegram_transport_cursor("test_transport_resume_link") == 203


def test_telegram_polling_runtime_records_quick_capture_for_linked_user(tmp_path):
    client = bootstrap_client(tmp_path)
    seed_web_checkpoint(client)
    link_payload = client.post("/v1/surfaces/telegram/link").json()
    link_token = extract_start_token(link_payload["bot_deep_link"])

    link_runtime = TelegramPollingRuntime(
        client.app.state.settings,
        store=client.app.state.store,
        bot_client=RecordingTelegramBotClient(
            [
                {
                    "update_id": 301,
                    "message": {
                        "message_id": 1,
                        "text": f"/start {link_token}",
                        "chat": {"id": 9301, "type": "private"},
                        "from": {"id": 7301, "username": "capture_user", "first_name": "Capture"},
                    },
                }
            ]
        ),
        cursor_name="test_transport_capture",
    )
    assert link_runtime.run_once() == 1
    initial_link_state = client.get("/v1/surfaces/telegram/link").json()
    initial_resume_token = initial_link_state["last_resume_token_ref"]

    bot_client = RecordingTelegramBotClient(
        [
            {
                "update_id": 302,
                "message": {
                    "message_id": 2,
                    "text": "Follow up with the design team tomorrow",
                    "chat": {"id": 9301, "type": "private"},
                    "from": {"id": 7301, "username": "capture_user", "first_name": "Capture"},
                },
            }
        ]
    )
    runtime = TelegramPollingRuntime(
        client.app.state.settings,
        store=client.app.state.store,
        bot_client=bot_client,
        cursor_name="test_transport_capture",
    )

    assert runtime.run_once() == 1

    link_state = client.get("/v1/surfaces/telegram/link").json()
    assert link_state["last_resume_token_ref"].startswith("resume_tg_")
    assert link_state["last_resume_token_ref"] != initial_resume_token

    checkpoint = client.get("/v1/checkpoints/current").json()
    assert checkpoint["conversation_id"] == "conv_telegram"
    assert checkpoint["route"] == "/chat/conv_telegram"
    assert checkpoint["draft_text"] == "Follow up with the design team tomorrow"
    assert checkpoint["selected_memory_ids"] == ["memory_tg_01"]
    assert checkpoint["surface"] == "telegram"
    assert checkpoint["handoff_kind"] == "quick_capture"
    assert checkpoint["resume_token_ref"] == link_state["last_resume_token_ref"]
    assert checkpoint["version"] == 3

    memory_items = client.get("/v1/memory/items").json()["items"]
    assert len(memory_items) == 1
    assert memory_items[0]["id"] == "memory_tg_01"
    assert memory_items[0]["content"] == "Follow up on the Telegram capture"
    assert bot_client.sent_messages == [
        {
            "chat_id": "9301",
            "text": "Captured this note for your assistant. Return to the web app to continue.",
        }
    ]
    assert client.app.state.store.get_telegram_transport_cursor("test_transport_capture") == 303


def test_telegram_polling_runtime_rejects_invalid_link_token(tmp_path):
    client = bootstrap_client(tmp_path)
    client.post("/v1/surfaces/telegram/link")

    bot_client = RecordingTelegramBotClient(
        [
            {
                "update_id": 11,
                "message": {
                    "message_id": 2,
                    "text": "/start invalid-link-token",
                    "chat": {"id": 9002, "type": "private"},
                    "from": {"id": 7002, "username": "invalid_user", "first_name": "Invalid"},
                },
            }
        ]
    )

    runtime = TelegramPollingRuntime(
        client.app.state.settings,
        store=client.app.state.store,
        bot_client=bot_client,
        cursor_name="test_transport_invalid",
    )

    assert runtime.run_once() == 1

    link_state = client.get("/v1/surfaces/telegram/link").json()
    assert link_state["status"] == "pending"
    assert link_state["is_linked"] is False
    assert bot_client.sent_messages == [
        {
            "chat_id": "9002",
            "text": "This link is invalid or expired. Start again from the assistant web app.",
        }
    ]
    assert client.app.state.store.get_telegram_transport_cursor("test_transport_invalid") == 12


def test_telegram_polling_runtime_ignores_non_private_chats(tmp_path):
    client = bootstrap_client(tmp_path)
    link_payload = client.post("/v1/surfaces/telegram/link").json()
    link_token = extract_start_token(link_payload["bot_deep_link"])

    bot_client = RecordingTelegramBotClient(
        [
            {
                "update_id": 31,
                "message": {
                    "message_id": 3,
                    "text": f"/start {link_token}",
                    "chat": {"id": -100123, "type": "group"},
                    "from": {"id": 7003, "username": "group_user", "first_name": "Group"},
                },
            }
        ]
    )

    runtime = TelegramPollingRuntime(
        client.app.state.settings,
        store=client.app.state.store,
        bot_client=bot_client,
        cursor_name="test_transport_group",
    )

    assert runtime.run_once() == 1

    link_state = client.get("/v1/surfaces/telegram/link").json()
    assert link_state["status"] == "pending"
    assert link_state["is_linked"] is False
    assert bot_client.sent_messages == []
    assert client.app.state.store.get_telegram_transport_cursor("test_transport_group") == 32
