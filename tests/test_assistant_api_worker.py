"""assistant-api worker foundation tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).parent.parent
SERVICE_ROOT = REPO_ROOT / "services" / "assistant-api"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from assistant_api.app import create_app  # noqa: E402
from assistant_api.config import Settings  # noqa: E402
from assistant_api.models import (  # noqa: E402
    JobKind,
    JobStatus,
    ReminderFollowUpFailureAction,
    ReminderFollowUpPolicy,
    Surface,
)
from assistant_api.telegram_transport import TelegramApiError  # noqa: E402
from assistant_api.worker import RuntimeJobWorker  # noqa: E402


class RecordingTelegramBotClient:
    def __init__(self) -> None:
        self.sent_messages: list[dict[str, str]] = []

    def get_updates(
        self,
        *,
        offset: int,
        timeout_seconds: int,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        return []

    def send_message(self, *, chat_id: str, text: str) -> None:
        self.sent_messages.append({"chat_id": chat_id, "text": text})


class FailingTelegramBotClient(RecordingTelegramBotClient):
    def send_message(self, *, chat_id: str, text: str) -> None:
        raise TelegramApiError("telegram sendMessage failed: simulated delivery outage")


def make_settings(
    repo_root: Path,
    *,
    memory_delete_retention_seconds: int = 0,
) -> Settings:
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
        telegram_bot_deep_link_base_url="https://t.me/test_assistant_bot?start=",
        telegram_api_base_url="https://api.telegram.org",
        telegram_link_ttl_seconds=900,
        telegram_poll_timeout_seconds=30,
        memory_delete_retention_seconds=memory_delete_retention_seconds,
        worker_poll_interval_seconds=0.01,
        worker_job_lease_seconds=30,
        secure_cookies=False,
        session_ttl_seconds=3600,
    )


def request_path(target_url: str) -> str:
    parsed = urlsplit(target_url)
    return f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path


def bootstrap_client(
    tmp_path: Path,
    *,
    memory_delete_retention_seconds: int = 0,
) -> tuple[TestClient, dict[str, str]]:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "package.json").write_text(json.dumps({"version": "2.0.0"}), encoding="utf-8")

    app = create_app(make_settings(repo_root, memory_delete_retention_seconds=memory_delete_retention_seconds))
    client = TestClient(app)

    auth_start = client.post(
        "/v1/auth/openai/start",
        json={
            "redirect_uri": "https://assistant-web.local/callback",
            "device_label": "Worker Tests",
            "platform": "web",
        },
    )
    provider_redirect = client.get(request_path(auth_start.json()["authorization_url"]), follow_redirects=False)
    client.get(request_path(provider_redirect.headers["location"]), follow_redirects=False)
    session_payload = client.get("/v1/auth/session").json()
    return client, session_payload


def create_memory_and_checkpoint(client: TestClient, session_payload: dict[str, str], *, memory_id: str) -> None:
    created_at = "2026-03-10T12:00:00Z"
    created_memory = client.post(
        "/v1/memory/items",
        json={
            "id": memory_id,
            "user_id": session_payload["user_id"],
            "kind": "preference",
            "content": f"Remember {memory_id}.",
            "status": "active",
            "importance": 75,
            "source_type": "manual_input",
            "created_at": created_at,
            "updated_at": created_at,
            "last_used_at": None,
            "sources": [
                {
                    "memory_id": memory_id,
                    "conversation_id": "conv_worker",
                    "message_id": "msg_worker",
                    "note": "worker test seed",
                    "captured_at": created_at,
                }
            ],
        },
    )
    assert created_memory.status_code == 201

    checkpoint_response = client.put(
        "/v1/checkpoints/current",
        json={
            "user_id": session_payload["user_id"],
            "device_session_id": session_payload["device_session_id"],
            "conversation_id": "conv_worker",
            "last_message_id": "msg_worker",
            "draft_text": "checkpoint draft",
            "selected_memory_ids": [memory_id],
            "route": "/chat/conv_worker",
            "surface": "web",
            "handoff_kind": "none",
            "resume_token_ref": None,
            "last_surface_at": created_at,
            "updated_at": created_at,
            "version": 1,
            "base_version": None,
            "force": False,
        },
    )
    assert checkpoint_response.status_code == 200


def link_telegram_companion(
    client: TestClient,
    *,
    telegram_user_id: str = "tg_worker_01",
    telegram_chat_id: str = "chat_worker_01",
    telegram_username: str = "workerbot",
) -> None:
    link_response = client.post("/v1/surfaces/telegram/link")
    assert link_response.status_code == 200
    complete_response = client.post(
        "/v1/internal/test/telegram/link/complete",
        json={
            "link_code": link_response.json()["link_code"],
            "telegram_user_id": telegram_user_id,
            "telegram_chat_id": telegram_chat_id,
            "telegram_username": telegram_username,
            "telegram_display_name": "Worker Bot",
            "last_resume_token_ref": "resume_tg_worker",
        },
    )
    assert complete_response.status_code == 200


def test_runtime_worker_executes_due_memory_purge_and_updates_runtime_job(tmp_path):
    client, session_payload = bootstrap_client(tmp_path, memory_delete_retention_seconds=0)
    create_memory_and_checkpoint(client, session_payload, memory_id="memory_purge")

    delete_response = client.delete("/v1/memory/items/memory_purge")
    assert delete_response.status_code == 202
    job_id = delete_response.json()["job_id"]

    worker = RuntimeJobWorker(client.app.state.settings, store=client.app.state.store, worker_id="worker_s15")
    completed_job = worker.run_once()

    assert completed_job is not None
    assert completed_job.job_id == job_id
    assert completed_job.kind == JobKind.MEMORY_DELETE
    assert completed_job.status == JobStatus.SUCCEEDED
    assert completed_job.details["purge_result"] == "deleted"
    assert completed_job.details["checkpoint_updates"] == 1

    jobs_payload = client.get("/v1/jobs").json()
    assert jobs_payload["items"][0]["status"] == "succeeded"
    assert jobs_payload["items"][0]["details"]["purged_at"] is not None

    listed_memory = client.get("/v1/memory/items")
    assert listed_memory.status_code == 200
    assert listed_memory.json()["items"] == []

    checkpoint_payload = client.get("/v1/checkpoints/current").json()
    assert checkpoint_payload["selected_memory_ids"] == []

    with client.app.state.store._connect() as connection:  # noqa: SLF001
        delete_job_count = connection.execute("SELECT COUNT(*) AS count FROM memory_delete_job").fetchone()["count"]
        runtime_row = connection.execute(
            """
            SELECT lease_owner, lease_token, lease_expires_at, attempt_count
            FROM runtime_job
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

    assert delete_job_count == 0
    assert runtime_row["lease_owner"] is None
    assert runtime_row["lease_token"] is None
    assert runtime_row["lease_expires_at"] is None
    assert runtime_row["attempt_count"] == 1


def test_runtime_job_claim_lease_and_complete_lifecycle(tmp_path):
    client, session_payload = bootstrap_client(tmp_path, memory_delete_retention_seconds=0)
    create_memory_and_checkpoint(client, session_payload, memory_id="memory_lease")

    delete_response = client.delete("/v1/memory/items/memory_lease")
    assert delete_response.status_code == 202
    job_id = delete_response.json()["job_id"]

    store = client.app.state.store
    claimed_job = store.claim_next_runtime_job(
        worker_id="worker_lease",
        supported_kinds=(JobKind.MEMORY_DELETE,),
        lease_seconds=5,
    )

    assert claimed_job is not None
    assert claimed_job.job.job_id == job_id
    assert claimed_job.job.status == JobStatus.RUNNING

    running_jobs = client.get("/v1/jobs").json()
    assert running_jobs["items"][0]["status"] == "running"

    extended_lease = store.heartbeat_runtime_job(
        job_id=claimed_job.job.job_id,
        lease_token=claimed_job.lease_token,
        lease_seconds=15,
    )
    assert extended_lease is not None
    assert extended_lease > claimed_job.lease_expires_at

    failed_job = store.complete_runtime_job(
        job_id=claimed_job.job.job_id,
        lease_token=claimed_job.lease_token,
        status=JobStatus.FAILED,
        error_code="lease_test_failure",
        error_message="simulated failure",
        details={"failure_stage": "lease_update"},
    )

    assert failed_job.status == JobStatus.FAILED
    assert failed_job.error_code == "lease_test_failure"
    assert failed_job.details["failure_stage"] == "lease_update"

    with store._connect() as connection:  # noqa: SLF001
        runtime_row = connection.execute(
            """
            SELECT lease_owner, lease_token, lease_expires_at, last_heartbeat_at, attempt_count
            FROM runtime_job
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

    assert runtime_row["lease_owner"] is None
    assert runtime_row["lease_token"] is None
    assert runtime_row["lease_expires_at"] is None
    assert runtime_row["last_heartbeat_at"] is None
    assert runtime_row["attempt_count"] == 1


def test_schedule_reminder_delivery_persists_runtime_job_foundation(tmp_path):
    client, session_payload = bootstrap_client(tmp_path)
    link_telegram_companion(client)
    store = client.app.state.store

    reminder = store.schedule_reminder_delivery(
        session_payload["user_id"],
        session_payload["device_session_id"],
        scheduled_for="2099-03-11T09:00:00Z",
        payload={"message": "Ship S16 worker follow-up"},
        channel=Surface.TELEGRAM,
    )

    assert reminder.status.value == "scheduled"
    assert reminder.job_id == reminder.reminder_id

    stored_reminder = store.get_reminder_delivery(session_payload["user_id"], reminder.reminder_id)
    assert stored_reminder is not None
    assert stored_reminder.payload["message"] == "Ship S16 worker follow-up"

    jobs_response = client.get("/v1/jobs", params={"kind": "reminder_delivery"})
    assert jobs_response.status_code == 200
    jobs_payload = jobs_response.json()["items"]
    assert len(jobs_payload) == 1
    assert jobs_payload[0]["job_id"] == reminder.job_id
    assert jobs_payload[0]["status"] == "queued"
    assert jobs_payload[0]["details"]["scheduled_for"] == "2099-03-11T09:00:00Z"
    assert jobs_payload[0]["details"]["channel"] == "telegram"

    worker = RuntimeJobWorker(client.app.state.settings, store=store, worker_id="worker_s15")
    assert worker.run_once() is None

    with store._connect() as connection:  # noqa: SLF001
        runtime_row = connection.execute(
            "SELECT kind, status, available_at FROM runtime_job WHERE job_id = ?",
            (reminder.job_id,),
        ).fetchone()

    assert runtime_row["kind"] == JobKind.REMINDER_DELIVERY.value
    assert runtime_row["status"] == JobStatus.QUEUED.value
    assert runtime_row["available_at"] == "2099-03-11T09:00:00Z"


def test_runtime_worker_delivers_due_telegram_reminder_and_records_audit(tmp_path):
    client, session_payload = bootstrap_client(tmp_path)
    create_memory_and_checkpoint(client, session_payload, memory_id="memory_reminder_success")
    link_telegram_companion(
        client,
        telegram_user_id="tg_worker_success",
        telegram_chat_id="chat_worker_success",
        telegram_username="deliver_success",
    )
    store = client.app.state.store

    reminder = store.schedule_reminder_delivery(
        session_payload["user_id"],
        session_payload["device_session_id"],
        scheduled_for="2026-03-09T09:00:00Z",
        payload={"message": "Review the S18 delivery audit"},
        channel=Surface.TELEGRAM,
    )

    bot_client = RecordingTelegramBotClient()
    worker = RuntimeJobWorker(
        client.app.state.settings,
        store=store,
        worker_id="worker_s18_success",
        telegram_bot_client=bot_client,
    )
    completed_job = worker.run_once()

    assert completed_job is not None
    assert completed_job.job_id == reminder.job_id
    assert completed_job.kind == JobKind.REMINDER_DELIVERY
    assert completed_job.status == JobStatus.SUCCEEDED
    assert completed_job.details["delivery_status"] == "delivered"
    assert completed_job.details["telegram_chat_id"] == "chat_worker_success"
    assert completed_job.details["message_text"] == "Reminder: Review the S18 delivery audit"

    stored_reminder = store.get_reminder_delivery(session_payload["user_id"], reminder.reminder_id)
    assert stored_reminder is not None
    assert stored_reminder.status.value == "delivered"
    assert stored_reminder.delivered_at is not None
    assert stored_reminder.last_error_code is None

    jobs_payload = client.get("/v1/jobs", params={"kind": "reminder_delivery"}).json()["items"]
    assert jobs_payload[0]["status"] == "succeeded"
    assert jobs_payload[0]["audit"]["surface"] == "web"
    assert jobs_payload[0]["audit"]["conversation_id"] == "conv_worker"
    assert jobs_payload[0]["details"]["telegram_username"] == "deliver_success"

    assert bot_client.sent_messages == [
        {
            "chat_id": "chat_worker_success",
            "text": "Reminder: Review the S18 delivery audit",
        }
    ]


def test_runtime_worker_records_failed_telegram_reminder_delivery_in_audit(tmp_path):
    client, session_payload = bootstrap_client(tmp_path)
    create_memory_and_checkpoint(client, session_payload, memory_id="memory_reminder_failure")
    link_telegram_companion(
        client,
        telegram_user_id="tg_worker_failure",
        telegram_chat_id="chat_worker_failure",
        telegram_username="deliver_failure",
    )
    store = client.app.state.store

    reminder = store.schedule_reminder_delivery(
        session_payload["user_id"],
        session_payload["device_session_id"],
        scheduled_for="2026-03-09T09:00:00Z",
        payload={"message": "Review the failed delivery path"},
        channel=Surface.TELEGRAM,
    )

    worker = RuntimeJobWorker(
        client.app.state.settings,
        store=store,
        worker_id="worker_s18_failure",
        telegram_bot_client=FailingTelegramBotClient(),
    )
    completed_job = worker.run_once()

    assert completed_job is not None
    assert completed_job.job_id == reminder.job_id
    assert completed_job.kind == JobKind.REMINDER_DELIVERY
    assert completed_job.status == JobStatus.FAILED
    assert completed_job.error_code == "telegram_delivery_failed"
    assert completed_job.details["delivery_status"] == "failed"
    assert completed_job.details["telegram_chat_id"] == "chat_worker_failure"

    stored_reminder = store.get_reminder_delivery(session_payload["user_id"], reminder.reminder_id)
    assert stored_reminder is not None
    assert stored_reminder.status.value == "failed"
    assert stored_reminder.delivered_at is None
    assert stored_reminder.last_error_code == "telegram_delivery_failed"
    assert "simulated delivery outage" in stored_reminder.last_error_message

    jobs_payload = client.get("/v1/jobs", params={"kind": "reminder_delivery", "status": "failed"}).json()["items"]
    assert len(jobs_payload) == 1
    assert jobs_payload[0]["job_id"] == reminder.job_id
    assert jobs_payload[0]["error_code"] == "telegram_delivery_failed"
    assert jobs_payload[0]["details"]["failed_at"] is not None
    assert jobs_payload[0]["details"]["follow_up_status"] == "dead_letter"


def test_runtime_worker_requeues_failed_telegram_reminder_with_follow_up_retry_policy(tmp_path):
    client, session_payload = bootstrap_client(tmp_path)
    create_memory_and_checkpoint(client, session_payload, memory_id="memory_reminder_retry")
    link_telegram_companion(
        client,
        telegram_user_id="tg_worker_retry",
        telegram_chat_id="chat_worker_retry",
        telegram_username="deliver_retry",
    )
    store = client.app.state.store

    reminder = store.schedule_reminder_delivery(
        session_payload["user_id"],
        session_payload["device_session_id"],
        scheduled_for="2026-03-09T09:00:00Z",
        payload={"message": "Retry the reminder delivery"},
        channel=Surface.TELEGRAM,
        follow_up_policy=ReminderFollowUpPolicy(
            on_failure=ReminderFollowUpFailureAction.RETRY,
            max_attempts=2,
            retry_delay_seconds=0,
        ),
    )

    queued_job = RuntimeJobWorker(
        client.app.state.settings,
        store=store,
        worker_id="worker_s28_retry",
        telegram_bot_client=FailingTelegramBotClient(),
    ).run_once()

    assert queued_job is not None
    assert queued_job.job_id == reminder.job_id
    assert queued_job.status == JobStatus.QUEUED
    assert queued_job.error_code == "telegram_delivery_failed"
    assert queued_job.attempt_count == 1
    assert queued_job.available_at is not None
    assert queued_job.details["delivery_status"] == "retry_scheduled"
    assert queued_job.details["follow_up_status"] == "retry_scheduled"
    assert queued_job.details["attempt_count"] == 1
    assert queued_job.details["next_attempt_at"] == queued_job.available_at

    stored_reminder = store.get_reminder_delivery(session_payload["user_id"], reminder.reminder_id)
    assert stored_reminder is not None
    assert stored_reminder.status.value == "scheduled"
    assert stored_reminder.last_error_code == "telegram_delivery_failed"
    assert stored_reminder.follow_up_state.status.value == "retry_scheduled"
    assert stored_reminder.follow_up_state.attempt_count == 1
    assert stored_reminder.follow_up_state.next_attempt_at == queued_job.available_at

    jobs_payload = client.get("/v1/jobs", params={"kind": "reminder_delivery"}).json()["items"]
    assert len(jobs_payload) == 1
    assert jobs_payload[0]["status"] == "queued"
    assert jobs_payload[0]["attempt_count"] == 1
    assert jobs_payload[0]["available_at"] == queued_job.available_at
    assert jobs_payload[0]["details"]["delivery_status"] == "retry_scheduled"

    with store._connect() as connection:  # noqa: SLF001
        runtime_row = connection.execute(
            "SELECT status, available_at, attempt_count FROM runtime_job WHERE job_id = ?",
            (reminder.job_id,),
        ).fetchone()

    assert runtime_row["status"] == JobStatus.QUEUED.value
    assert runtime_row["available_at"] == queued_job.available_at
    assert runtime_row["attempt_count"] == 1


def test_runtime_worker_marks_retry_exhausted_reminder_as_dead_letter(tmp_path):
    client, session_payload = bootstrap_client(tmp_path)
    create_memory_and_checkpoint(client, session_payload, memory_id="memory_reminder_dead_letter")
    link_telegram_companion(
        client,
        telegram_user_id="tg_worker_dead_letter",
        telegram_chat_id="chat_worker_dead_letter",
        telegram_username="deliver_dead_letter",
    )
    store = client.app.state.store

    reminder = store.schedule_reminder_delivery(
        session_payload["user_id"],
        session_payload["device_session_id"],
        scheduled_for="2026-03-09T09:00:00Z",
        payload={"message": "Exhaust the retry budget"},
        channel=Surface.TELEGRAM,
        follow_up_policy=ReminderFollowUpPolicy(
            on_failure=ReminderFollowUpFailureAction.RETRY,
            max_attempts=2,
            retry_delay_seconds=0,
        ),
    )

    worker = RuntimeJobWorker(
        client.app.state.settings,
        store=store,
        worker_id="worker_s28_dead_letter",
        telegram_bot_client=FailingTelegramBotClient(),
    )
    first_attempt = worker.run_once()
    second_attempt = worker.run_once()

    assert first_attempt is not None
    assert first_attempt.status == JobStatus.QUEUED
    assert second_attempt is not None
    assert second_attempt.job_id == reminder.job_id
    assert second_attempt.status == JobStatus.FAILED
    assert second_attempt.error_code == "telegram_delivery_failed"
    assert second_attempt.attempt_count == 2
    assert second_attempt.details["follow_up_status"] == "dead_letter"
    assert second_attempt.details["attempt_count"] == 2

    stored_reminder = store.get_reminder_delivery(session_payload["user_id"], reminder.reminder_id)
    assert stored_reminder is not None
    assert stored_reminder.status.value == "failed"
    assert stored_reminder.last_error_code == "telegram_delivery_failed"
    assert stored_reminder.follow_up_state.status.value == "dead_letter"
    assert stored_reminder.follow_up_state.attempt_count == 2
    assert stored_reminder.follow_up_state.next_attempt_at is None
    assert stored_reminder.follow_up_state.last_transition_reason == "delivery_failed_dead_letter"

    jobs_payload = client.get("/v1/jobs", params={"kind": "reminder_delivery", "status": "failed"}).json()["items"]
    assert len(jobs_payload) == 1
    assert jobs_payload[0]["job_id"] == reminder.job_id
    assert jobs_payload[0]["attempt_count"] == 2
    assert jobs_payload[0]["details"]["follow_up_status"] == "dead_letter"


def test_store_reminder_follow_up_snooze_and_reschedule_updates_runtime_job(tmp_path):
    client, session_payload = bootstrap_client(tmp_path)
    link_telegram_companion(client)
    store = client.app.state.store

    reminder = store.schedule_reminder_delivery(
        session_payload["user_id"],
        session_payload["device_session_id"],
        scheduled_for="2026-03-11T09:00:00Z",
        payload={"message": "Adjust the follow-up window"},
        channel=Surface.TELEGRAM,
    )

    snoozed = store.snooze_reminder_delivery(
        session_payload["user_id"],
        reminder.reminder_id,
        snoozed_until="2026-03-11T09:15:00Z",
    )
    assert snoozed.status.value == "scheduled"
    assert snoozed.scheduled_for == "2026-03-11T09:00:00Z"
    assert snoozed.follow_up_state.status.value == "snoozed"
    assert snoozed.follow_up_state.next_attempt_at == "2026-03-11T09:15:00Z"

    rescheduled = store.reschedule_reminder_delivery(
        session_payload["user_id"],
        reminder.reminder_id,
        scheduled_for="2026-03-11T10:00:00Z",
    )
    assert rescheduled.status.value == "scheduled"
    assert rescheduled.scheduled_for == "2026-03-11T10:00:00Z"
    assert rescheduled.follow_up_state.status.value == "rescheduled"
    assert rescheduled.follow_up_state.next_attempt_at == "2026-03-11T10:00:00Z"

    jobs_payload = client.get("/v1/jobs", params={"kind": "reminder_delivery"}).json()["items"]
    assert len(jobs_payload) == 1
    assert jobs_payload[0]["status"] == "queued"
    assert jobs_payload[0]["available_at"] == "2026-03-11T10:00:00Z"
    assert jobs_payload[0]["details"]["delivery_status"] == "rescheduled"
    assert jobs_payload[0]["details"]["follow_up_status"] == "rescheduled"
