"""Runtime worker for executable assistant-api background jobs."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from .config import Settings
from .models import JobKind, JobStatus, ReminderFollowUpFailureAction, ReminderStatus, RuntimeJobRecord
from .store import ClaimedRuntimeJob, SQLiteAssistantStore
from .telegram_transport import (
    TelegramBotApiClient,
    TelegramBotClient,
    TelegramReminderDeliveryError,
    TelegramReminderDeliveryTransport,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RuntimeJobExecutionResult:
    status: JobStatus
    details: dict[str, object] | None = None
    error_code: str | None = None
    error_message: str | None = None
    job: RuntimeJobRecord | None = None


class RuntimeJobWorker:
    """Polls runnable jobs and executes the handlers this process supports."""

    def __init__(
        self,
        settings: Settings,
        *,
        store: SQLiteAssistantStore | None = None,
        worker_id: str | None = None,
        telegram_bot_client: TelegramBotClient | None = None,
    ) -> None:
        self.settings = settings
        self.store = store or SQLiteAssistantStore(settings)
        self.worker_id = worker_id or f"worker_{uuid4().hex[:12]}"
        self._telegram_bot_client = telegram_bot_client
        self._telegram_delivery_transport: TelegramReminderDeliveryTransport | None = None
        self._handlers = {
            JobKind.MEMORY_DELETE: self._handle_memory_delete,
            JobKind.REMINDER_DELIVERY: self._handle_reminder_delivery,
        }

    @property
    def supported_kinds(self) -> tuple[JobKind, ...]:
        return tuple(self._handlers)

    def run_once(self) -> RuntimeJobRecord | None:
        claimed = self.store.claim_next_runtime_job(
            worker_id=self.worker_id,
            supported_kinds=self.supported_kinds,
            lease_seconds=self.settings.worker_job_lease_seconds,
        )
        if claimed is None:
            return None

        LOGGER.info("claimed runtime job", extra={"job_id": claimed.job.job_id, "kind": claimed.job.kind.value})
        try:
            result = self._execute_job(claimed)
        except Exception as exc:
            LOGGER.exception("runtime job failed", extra={"job_id": claimed.job.job_id})
            result = RuntimeJobExecutionResult(
                status=JobStatus.FAILED,
                error_code="job_execution_failed",
                error_message=str(exc),
            )

        if result.job is not None:
            return result.job

        return self.store.complete_runtime_job(
            job_id=claimed.job.job_id,
            lease_token=claimed.lease_token,
            status=result.status,
            error_code=result.error_code,
            error_message=result.error_message,
            details=result.details,
        )

    def run(self, *, once: bool = False, max_jobs: int | None = None) -> int:
        processed_jobs = 0
        while True:
            completed_job = self.run_once()
            if completed_job is None:
                if once:
                    return processed_jobs
                time.sleep(self.settings.worker_poll_interval_seconds)
                continue

            processed_jobs += 1
            if once:
                return processed_jobs
            if max_jobs is not None and processed_jobs >= max_jobs:
                return processed_jobs

    def _execute_job(self, claimed: ClaimedRuntimeJob) -> RuntimeJobExecutionResult:
        handler = self._handlers.get(claimed.job.kind)
        if handler is None:
            raise ValueError(f"unsupported runtime job kind: {claimed.job.kind.value}")
        return handler(claimed)

    def _handle_memory_delete(self, claimed: ClaimedRuntimeJob) -> RuntimeJobExecutionResult:
        return RuntimeJobExecutionResult(
            status=JobStatus.SUCCEEDED,
            details=self.store.purge_memory_delete_job(claimed.job),
        )

    def _handle_reminder_delivery(self, claimed: ClaimedRuntimeJob) -> RuntimeJobExecutionResult:
        job = claimed.job
        reminder_id = str(job.details.get("reminder_id") or job.resource_id or job.job_id)
        reminder = self.store.get_reminder_delivery(job.user_id, reminder_id)
        if reminder is None:
            raise ValueError("reminder_delivery job is missing reminder state")
        if reminder.status == ReminderStatus.CANCELED:
            return RuntimeJobExecutionResult(
                status=JobStatus.CANCELED,
                details={
                    "reminder_id": reminder.reminder_id,
                    "delivery_status": "canceled",
                    "canceled_at": reminder.canceled_at,
                    "follow_up_status": reminder.follow_up_state.status.value,
                    "attempt_count": reminder.follow_up_state.attempt_count,
                },
            )
        if reminder.status != ReminderStatus.SCHEDULED:
            raise ValueError(f"reminder_delivery job is not runnable from status {reminder.status.value}")

        try:
            delivery = self._get_telegram_delivery_transport().deliver_reminder(reminder)
        except TelegramReminderDeliveryError as exc:
            attempt_count = max(job.attempt_count, 1)
            if (
                reminder.follow_up_policy.on_failure == ReminderFollowUpFailureAction.RETRY
                and attempt_count < reminder.follow_up_policy.max_attempts
            ):
                next_attempt_at = (
                    datetime.now(UTC) + timedelta(seconds=reminder.follow_up_policy.retry_delay_seconds)
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
                queued_job = self.store.requeue_reminder_delivery_after_failure(
                    job_id=job.job_id,
                    lease_token=claimed.lease_token,
                    user_id=job.user_id,
                    reminder_id=reminder.reminder_id,
                    error_code=exc.code,
                    error_message=str(exc),
                    attempt_count=attempt_count,
                    next_attempt_at=next_attempt_at,
                )
                return RuntimeJobExecutionResult(
                    status=JobStatus.QUEUED,
                    job=queued_job,
                )

            failed_reminder = self.store.mark_reminder_failed(
                job.user_id,
                reminder.reminder_id,
                error_code=exc.code,
                error_message=str(exc),
                attempt_count=attempt_count,
            )
            failure_details = {
                "reminder_id": reminder.reminder_id,
                "scheduled_for": reminder.scheduled_for,
                "channel": reminder.channel.value,
                "delivery_status": "failed",
                "failed_at": failed_reminder.updated_at,
                "follow_up_status": failed_reminder.follow_up_state.status.value,
                "attempt_count": failed_reminder.follow_up_state.attempt_count,
                "next_attempt_at": failed_reminder.follow_up_state.next_attempt_at,
                "last_transition_reason": failed_reminder.follow_up_state.last_transition_reason,
            }
            failure_details.update(exc.audit_details)
            return RuntimeJobExecutionResult(
                status=JobStatus.FAILED,
                error_code=exc.code,
                error_message=str(exc),
                details=failure_details,
            )

        delivered_reminder = self.store.mark_reminder_delivered(
            job.user_id,
            reminder.reminder_id,
            attempt_count=max(job.attempt_count, 1),
        )
        return RuntimeJobExecutionResult(
            status=JobStatus.SUCCEEDED,
            details={
                "reminder_id": reminder.reminder_id,
                "scheduled_for": reminder.scheduled_for,
                "channel": reminder.channel.value,
                "delivery_status": "delivered",
                "delivered_at": delivered_reminder.delivered_at,
                "follow_up_status": delivered_reminder.follow_up_state.status.value,
                "attempt_count": delivered_reminder.follow_up_state.attempt_count,
                "next_attempt_at": delivered_reminder.follow_up_state.next_attempt_at,
                "last_transition_reason": delivered_reminder.follow_up_state.last_transition_reason,
                "telegram_chat_id": delivery.chat_id,
                "telegram_username": delivery.username,
                "telegram_display_name": delivery.display_name,
                "message_text": delivery.message_text,
            },
        )

    def _get_telegram_delivery_transport(self) -> TelegramReminderDeliveryTransport:
        if self._telegram_delivery_transport is None:
            bot_client = self._telegram_bot_client or TelegramBotApiClient(self.settings)
            self._telegram_delivery_transport = TelegramReminderDeliveryTransport(
                self.settings,
                store=self.store,
                bot_client=bot_client,
            )
        return self._telegram_delivery_transport
