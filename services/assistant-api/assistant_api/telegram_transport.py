"""Polling-first Telegram transport foundation for assistant-api."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from time import sleep
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .config import Settings
from .models import ReminderRecord, Surface
from .store import SQLiteAssistantStore, TelegramDeliveryTarget, TelegramLinkError

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TelegramInboundMessage:
    update_id: int
    chat_id: str
    chat_type: str
    sender_id: str | None
    text: str | None
    username: str | None
    display_name: str | None


@dataclass(frozen=True, slots=True)
class TelegramHandleResult:
    update_id: int | None
    consumed: bool
    action: str
    response_text: str | None = None


@dataclass(frozen=True, slots=True)
class TelegramReminderDeliveryResult:
    chat_id: str
    username: str | None
    display_name: str | None
    message_text: str


class TelegramApiError(RuntimeError):
    """Raised when the Telegram Bot API returns an error."""


class TelegramReminderDeliveryError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        audit_details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.audit_details = dict(audit_details or {})


class TelegramBotClient(Protocol):
    def get_updates(
        self,
        *,
        offset: int,
        timeout_seconds: int,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return inbound Telegram updates."""

    def send_message(self, *, chat_id: str, text: str) -> None:
        """Send a plain-text Telegram message."""


class TelegramBotApiClient:
    """Minimal Telegram Bot API client for self-host polling."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_base_url = settings.telegram_api_base_url.rstrip("/")
        self.bot_token = quote(settings.require_telegram_bot_token(), safe="")

    def get_updates(
        self,
        *,
        offset: int,
        timeout_seconds: int,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        payload = {
            "offset": offset,
            "timeout": timeout_seconds,
            "limit": limit,
            "allowed_updates": ["message"],
        }
        result = self._call_api("getUpdates", payload, timeout_seconds=timeout_seconds + 5)
        if not isinstance(result, list):
            raise TelegramApiError("telegram getUpdates returned a non-list result")
        updates: list[dict[str, Any]] = []
        for item in result:
            if isinstance(item, dict):
                updates.append(item)
        return updates

    def send_message(self, *, chat_id: str, text: str) -> None:
        self._call_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout_seconds=10,
        )

    def _call_api(
        self,
        method_name: str,
        payload: dict[str, object],
        *,
        timeout_seconds: int,
    ) -> Any:
        request = Request(
            url=f"{self.api_base_url}/bot{self.bot_token}/{method_name}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                raw_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:  # pragma: no cover - exercised through integration behavior
            raise TelegramApiError(f"telegram {method_name} failed with HTTP {exc.code}") from exc
        except URLError as exc:  # pragma: no cover - exercised through integration behavior
            raise TelegramApiError(f"telegram {method_name} failed: {exc.reason}") from exc

        if not isinstance(raw_payload, dict):
            raise TelegramApiError(f"telegram {method_name} returned an invalid response payload")
        if raw_payload.get("ok") is not True:
            description = raw_payload.get("description")
            raise TelegramApiError(
                f"telegram {method_name} failed: {description or 'unknown api error'}"
            )
        return raw_payload.get("result")


class TelegramTransport:
    """Process inbound Telegram updates without exposing Telegram secrets."""

    def __init__(
        self,
        settings: Settings,
        *,
        store: SQLiteAssistantStore,
        bot_client: TelegramBotClient,
    ) -> None:
        self.settings = settings
        self.store = store
        self.bot_client = bot_client

    def handle_update(self, update_payload: dict[str, Any]) -> TelegramHandleResult:
        message = _message_from_update(update_payload)
        if message is None:
            return TelegramHandleResult(
                update_id=_update_id_from_payload(update_payload),
                consumed=False,
                action="ignored_unsupported_update",
            )

        if message.chat_type != "private":
            return TelegramHandleResult(
                update_id=message.update_id,
                consumed=False,
                action="ignored_non_private_chat",
            )

        if message.text is None:
            return TelegramHandleResult(
                update_id=message.update_id,
                consumed=False,
                action="ignored_non_text_message",
            )

        sender_id = message.sender_id or message.chat_id
        command, argument = _parse_command(message.text)
        if command == "/start" and argument:
            try:
                self.store.complete_telegram_link_from_token(
                    link_token=argument,
                    telegram_user_id=sender_id,
                    telegram_chat_id=message.chat_id,
                    telegram_username=message.username,
                    telegram_display_name=message.display_name,
                )
            except TelegramLinkError as exc:
                response_text = _link_error_message(exc.code)
                self._safe_send_message(chat_id=message.chat_id, text=response_text)
                return TelegramHandleResult(
                    update_id=message.update_id,
                    consumed=True,
                    action=exc.code,
                    response_text=response_text,
                )

            response_text = "Telegram is linked to your assistant. Return to the web app to continue."
            self._safe_send_message(chat_id=message.chat_id, text=response_text)
            return TelegramHandleResult(
                update_id=message.update_id,
                consumed=True,
                action="link_completed",
                response_text=response_text,
            )

        if command == "/start":
            try:
                self.store.record_telegram_resume_handoff(
                    telegram_user_id=sender_id,
                    telegram_chat_id=message.chat_id,
                    telegram_username=message.username,
                    telegram_display_name=message.display_name,
                )
            except TelegramLinkError as exc:
                response_text = _resume_error_message(exc.code)
                self._safe_send_message(chat_id=message.chat_id, text=response_text)
                return TelegramHandleResult(
                    update_id=message.update_id,
                    consumed=True,
                    action=exc.code,
                    response_text=response_text,
                )

            response_text = "Resume is ready in the web app. Return there to continue."
            self._safe_send_message(chat_id=message.chat_id, text=response_text)
            return TelegramHandleResult(
                update_id=message.update_id,
                consumed=True,
                action="resume_link_ready",
                response_text=response_text,
            )

        if command is not None:
            response_text = (
                "Telegram supports quick capture and resume. "
                "Use plain text for a capture or /start after linking to refresh the resume handoff."
            )
            self._safe_send_message(chat_id=message.chat_id, text=response_text)
            return TelegramHandleResult(
                update_id=message.update_id,
                consumed=True,
                action="unsupported_command",
                response_text=response_text,
            )

        try:
            self.store.record_telegram_quick_capture(
                telegram_user_id=sender_id,
                telegram_chat_id=message.chat_id,
                text=message.text,
                telegram_username=message.username,
                telegram_display_name=message.display_name,
            )
        except TelegramLinkError as exc:
            response_text = _quick_capture_error_message(exc.code)
            self._safe_send_message(chat_id=message.chat_id, text=response_text)
            return TelegramHandleResult(
                update_id=message.update_id,
                consumed=True,
                action=exc.code,
                response_text=response_text,
            )

        response_text = "Captured this note for your assistant. Return to the web app to continue."
        self._safe_send_message(chat_id=message.chat_id, text=response_text)
        return TelegramHandleResult(
            update_id=message.update_id,
            consumed=True,
            action="quick_capture_recorded",
            response_text=response_text,
        )

    def _safe_send_message(self, *, chat_id: str, text: str) -> None:
        try:
            self.bot_client.send_message(chat_id=chat_id, text=text)
        except TelegramApiError:
            LOGGER.warning("telegram response delivery failed", exc_info=True, extra={"chat_id": chat_id})


class TelegramReminderDeliveryTransport:
    """Deliver outbound reminder notifications through the shared Telegram seam."""

    def __init__(
        self,
        settings: Settings,
        *,
        store: SQLiteAssistantStore,
        bot_client: TelegramBotClient,
    ) -> None:
        self.settings = settings
        self.store = store
        self.bot_client = bot_client

    def deliver_reminder(self, reminder: ReminderRecord) -> TelegramReminderDeliveryResult:
        if reminder.channel != Surface.TELEGRAM:
            raise TelegramReminderDeliveryError(
                "unsupported_reminder_channel",
                f"unsupported reminder channel: {reminder.channel.value}",
            )

        message_text = _render_reminder_message(reminder)
        try:
            target = self.store.get_linked_telegram_delivery_target(reminder.user_id)
        except TelegramLinkError as exc:
            raise TelegramReminderDeliveryError(exc.code, str(exc)) from exc

        try:
            self.bot_client.send_message(chat_id=target.chat_id, text=message_text)
        except TelegramApiError as exc:
            raise TelegramReminderDeliveryError(
                "telegram_delivery_failed",
                str(exc),
                audit_details=_telegram_delivery_target_audit(target),
            ) from exc

        return TelegramReminderDeliveryResult(
            chat_id=target.chat_id,
            username=target.username,
            display_name=target.display_name,
            message_text=message_text,
        )


class TelegramPollingRuntime:
    """Long-poll Telegram updates and hand them to the shared transport seam."""

    def __init__(
        self,
        settings: Settings,
        *,
        store: SQLiteAssistantStore | None = None,
        bot_client: TelegramBotClient | None = None,
        transport: TelegramTransport | None = None,
        cursor_name: str = "telegram_polling",
        idle_sleep_seconds: float = 0.0,
    ) -> None:
        self.settings = settings
        self.store = store or SQLiteAssistantStore(settings)
        if store is None:
            self.store.initialize()
        self.bot_client = bot_client or TelegramBotApiClient(settings)
        self.transport = transport or TelegramTransport(
            settings,
            store=self.store,
            bot_client=self.bot_client,
        )
        self.cursor_name = cursor_name
        self.idle_sleep_seconds = idle_sleep_seconds

    def run_once(self) -> int:
        next_update_id = self.store.get_telegram_transport_cursor(self.cursor_name)
        updates = self.bot_client.get_updates(
            offset=next_update_id,
            timeout_seconds=self.settings.telegram_poll_timeout_seconds,
        )
        processed_updates = 0
        advanced_cursor = next_update_id

        for update_payload in updates:
            update_id = _update_id_from_payload(update_payload)
            if update_id is None:
                LOGGER.warning("telegram update missing update_id; skipping payload")
                continue
            self.transport.handle_update(update_payload)
            processed_updates += 1
            advanced_cursor = max(advanced_cursor, update_id + 1)

        if advanced_cursor != next_update_id:
            self.store.advance_telegram_transport_cursor(
                cursor_name=self.cursor_name,
                next_update_id=advanced_cursor,
            )
        return processed_updates

    def run(self, *, once: bool = False, max_batches: int | None = None) -> int:
        processed_updates = 0
        completed_batches = 0
        while True:
            batch_count = self.run_once()
            processed_updates += batch_count
            completed_batches += 1

            if once:
                return processed_updates
            if max_batches is not None and completed_batches >= max_batches:
                return processed_updates
            if batch_count == 0 and self.idle_sleep_seconds > 0:
                sleep(self.idle_sleep_seconds)


def _update_id_from_payload(update_payload: dict[str, Any]) -> int | None:
    raw_update_id = update_payload.get("update_id")
    if isinstance(raw_update_id, int):
        return raw_update_id
    return None


def _message_from_update(update_payload: dict[str, Any]) -> TelegramInboundMessage | None:
    update_id = _update_id_from_payload(update_payload)
    if update_id is None:
        return None

    raw_message = update_payload.get("message")
    if not isinstance(raw_message, dict):
        return None
    raw_chat = raw_message.get("chat")
    if not isinstance(raw_chat, dict):
        return None

    raw_chat_id = raw_chat.get("id")
    raw_chat_type = raw_chat.get("type")
    if raw_chat_id is None or not isinstance(raw_chat_type, str):
        return None

    raw_sender = raw_message.get("from")
    sender_id: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    if isinstance(raw_sender, dict):
        raw_sender_id = raw_sender.get("id")
        sender_id = str(raw_sender_id) if raw_sender_id is not None else None
        username = raw_sender.get("username") if isinstance(raw_sender.get("username"), str) else None
        first_name = raw_sender.get("first_name") if isinstance(raw_sender.get("first_name"), str) else None
        last_name = raw_sender.get("last_name") if isinstance(raw_sender.get("last_name"), str) else None

    display_name_parts = [part for part in (first_name, last_name) if part]
    display_name = " ".join(display_name_parts).strip() or username
    raw_text = raw_message.get("text")
    return TelegramInboundMessage(
        update_id=update_id,
        chat_id=str(raw_chat_id),
        chat_type=raw_chat_type,
        sender_id=sender_id,
        text=raw_text if isinstance(raw_text, str) else None,
        username=username,
        display_name=display_name,
    )


def _parse_command(text: str) -> tuple[str | None, str | None]:
    stripped_text = text.strip()
    if not stripped_text.startswith("/"):
        return None, None
    command_parts = stripped_text.split(maxsplit=1)
    raw_command = command_parts[0].split("@", 1)[0].lower()
    argument = command_parts[1].strip() if len(command_parts) > 1 else None
    return raw_command, argument or None


def _link_error_message(error_code: str) -> str:
    if error_code == "telegram_account_conflict":
        return "This Telegram account is already linked to another assistant profile."
    return "This link is invalid or expired. Start again from the assistant web app."


def _resume_error_message(error_code: str) -> str:
    if error_code == "telegram_not_linked":
        return "Open the assistant web app, choose Link Telegram, and then reopen the bot link."
    return "Telegram resume is temporarily unavailable. Return to the web app and try again."


def _quick_capture_error_message(error_code: str) -> str:
    if error_code == "telegram_not_linked":
        return "Link Telegram from the assistant web app before sending quick captures here."
    if error_code == "quick_capture_empty":
        return "Send a short text note to capture it here."
    return "Quick capture is temporarily unavailable. Return to the web app and try again."


def _render_reminder_message(reminder: ReminderRecord) -> str:
    message = reminder.payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise TelegramReminderDeliveryError(
            "reminder_message_missing",
            "reminder payload is missing a delivery message",
        )
    return f"Reminder: {message.strip()}"


def _telegram_delivery_target_audit(target: TelegramDeliveryTarget) -> dict[str, object]:
    return {
        "telegram_chat_id": target.chat_id,
        "telegram_username": target.username,
        "telegram_display_name": target.display_name,
    }
