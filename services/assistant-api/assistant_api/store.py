"""SQLite-backed bootstrap storage for assistant-api."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from .config import Settings
from .memory_broker import (
    MemoryBrokerBackend,
    MemoryBrokerSearchContext,
    create_memory_broker_backend,
)
from .models import (
    AuthSession,
    AuthState,
    CheckpointConflictResponse,
    CheckpointUpsertRequest,
    EvidenceRef,
    HandoffKind,
    JobKind,
    JobStatus,
    MemoryBrokerAuditAction,
    MemoryBrokerAuditRecord,
    MemoryBrokerAuditStatus,
    MemoryBrokerConsent,
    MemoryBrokerOptInStatus,
    MemoryBrokerProvider,
    MemoryBrokerProviderStatus,
    MemoryBrokerQueryRequest,
    MemoryBrokerQueryResponse,
    MemoryBrokerResult,
    MemoryBrokerScope,
    MemoryBrokerWorkspaceListResponse,
    MemoryBrokerWorkspaceState,
    MemoryBrokerWorkspaceUpsertRequest,
    MemoryControls,
    MemoryCreateRequest,
    MemoryDeleteReceipt,
    MemoryDeleteStatus,
    MemoryExportFormat,
    MemoryExportRecord,
    MemoryExportResponse,
    MemoryExportStatus,
    MemoryItemPatchRequest,
    MemoryItemsResponse,
    MemoryRecord,
    MemoryRevision,
    MemorySource,
    MemoryStatus,
    OpenAiStartRequest,
    ProviderMetadata,
    ReminderFollowUpPolicy,
    ReminderFollowUpState,
    ReminderFollowUpStatus,
    ReminderListResponse,
    ReminderRecord,
    ReminderStatus,
    RuntimeJobAudit,
    RuntimeJobRecord,
    RuntimeJobsResponse,
    SessionCheckpoint,
    SessionMetadata,
    Surface,
    TelegramLinkState,
    TelegramLinkStatus,
)
from .provider import ProviderIdentity, ProviderTokenBundle, generate_pkce_pair


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json_object(raw_value: str | None) -> dict[str, object]:
    try:
        parsed = json.loads(raw_value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _reminder_follow_up_policy_from_json(raw_value: str | None) -> ReminderFollowUpPolicy:
    return ReminderFollowUpPolicy.model_validate(_json_object(raw_value))


def _reminder_follow_up_state_from_json(raw_value: str | None) -> ReminderFollowUpState:
    return ReminderFollowUpState.model_validate(_json_object(raw_value))


def _reminder_runtime_details(
    *,
    reminder_id: str,
    scheduled_for: str,
    channel: Surface,
    payload: dict[str, object],
    delivery_status: str,
    follow_up_policy: ReminderFollowUpPolicy,
    follow_up_state: ReminderFollowUpState,
) -> dict[str, object]:
    return {
        "reminder_id": reminder_id,
        "scheduled_for": scheduled_for,
        "channel": channel.value,
        "payload": payload,
        "delivery_status": delivery_status,
        "follow_up_status": follow_up_state.status.value,
        "attempt_count": follow_up_state.attempt_count,
        "next_attempt_at": follow_up_state.next_attempt_at,
        "last_transition_reason": follow_up_state.last_transition_reason,
        "follow_up_policy": follow_up_policy.model_dump(mode="json"),
        "follow_up_state": follow_up_state.model_dump(mode="json"),
    }


@dataclass(frozen=True, slots=True)
class PendingAuthFlow:
    oauth_state: str
    user_id: str
    device_session_id: str
    session_id: str
    redirect_uri: str
    code_verifier: str
    code_challenge: str
    expires_at: str


@dataclass(frozen=True, slots=True)
class ClaimedRuntimeJob:
    lease_owner: str
    lease_token: str
    lease_expires_at: str
    job: RuntimeJobRecord


@dataclass(frozen=True, slots=True)
class TelegramDeliveryTarget:
    user_id: str
    chat_id: str
    username: str | None
    display_name: str | None


class CheckpointConflictError(ValueError):
    def __init__(self, response: CheckpointConflictResponse):
        super().__init__(response.message)
        self.response = response


class TelegramLinkError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class SQLiteAssistantStore:
    """Minimal SQLite store for auth, memory, checkpoint, and evidence refs."""

    def __init__(self, settings: Settings, *, memory_broker: MemoryBrokerBackend | None = None):
        self.settings = settings
        self.memory_broker = memory_broker or create_memory_broker_backend()

    def initialize(self) -> None:
        self.settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        migration_sql = self.settings.migration_path.read_text(encoding="utf-8")
        with self._connect() as connection:
            connection.executescript(migration_sql)
            self._ensure_bootstrap_compatibility(connection)

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.settings.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _ensure_bootstrap_compatibility(self, connection: sqlite3.Connection) -> None:
        self._ensure_table_columns(
            connection,
            "session_checkpoint",
            {
                "surface": "TEXT NOT NULL DEFAULT 'web'",
                "handoff_kind": "TEXT NOT NULL DEFAULT 'none'",
                "resume_token_ref": "TEXT",
                "last_surface_at": "TEXT",
            },
        )
        self._ensure_table_columns(
            connection,
            "runtime_job",
            {
                "available_at": "TEXT",
                "lease_owner": "TEXT",
                "lease_token": "TEXT",
                "lease_expires_at": "TEXT",
                "last_heartbeat_at": "TEXT",
                "attempt_count": "INTEGER NOT NULL DEFAULT 0",
            },
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_job_status_available_at
            ON runtime_job(status, available_at, requested_at)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reminder_delivery (
                reminder_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL,
                device_session_id TEXT NOT NULL,
                status TEXT NOT NULL,
                channel TEXT NOT NULL,
                scheduled_for TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                delivered_at TEXT,
                canceled_at TEXT,
                last_error_code TEXT,
                last_error_message TEXT,
                follow_up_policy_json TEXT NOT NULL DEFAULT '{}',
                follow_up_state_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (job_id) REFERENCES runtime_job(job_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
                FOREIGN KEY (device_session_id) REFERENCES device_session(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_reminder_delivery_user_scheduled_for
            ON reminder_delivery(user_id, scheduled_for)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_reminder_delivery_status
            ON reminder_delivery(status)
            """
        )
        self._ensure_table_columns(
            connection,
            "reminder_delivery",
            {
                "follow_up_policy_json": "TEXT NOT NULL DEFAULT '{}'",
                "follow_up_state_json": "TEXT NOT NULL DEFAULT '{}'",
            },
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_broker_workspace (
                user_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                status TEXT NOT NULL,
                provider TEXT NOT NULL,
                project_ids_json TEXT NOT NULL,
                source_surface TEXT,
                granted_at TEXT,
                revoked_at TEXT,
                updated_at TEXT,
                last_brokered_at TEXT,
                last_audit_id TEXT,
                last_audit_at TEXT,
                last_error_code TEXT,
                last_error_message TEXT,
                PRIMARY KEY (user_id, workspace_id),
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memory_broker_workspace_user_status
            ON memory_broker_workspace(user_id, status)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_broker_audit (
                audit_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                project_id TEXT,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                source_surface TEXT NOT NULL,
                conversation_id TEXT,
                query_text TEXT,
                result_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                details_json TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memory_broker_audit_user_created_at
            ON memory_broker_audit(user_id, created_at DESC)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_transport_cursor (
                cursor_name TEXT PRIMARY KEY,
                next_update_id INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute("UPDATE runtime_job SET attempt_count = 0 WHERE attempt_count IS NULL")
        connection.execute(
            """
            UPDATE runtime_job
            SET available_at = requested_at
            WHERE available_at IS NULL
              AND kind != ?
            """,
            (JobKind.MEMORY_DELETE.value,),
        )
        connection.execute(
            """
            UPDATE runtime_job
            SET available_at = COALESCE(
                (
                    SELECT purge_after
                    FROM memory_delete_job
                    WHERE delete_id = runtime_job.job_id
                ),
                requested_at
            )
            WHERE available_at IS NULL
              AND kind = ?
            """,
            (JobKind.MEMORY_DELETE.value,),
        )

    @staticmethod
    def _ensure_table_columns(
        connection: sqlite3.Connection,
        table_name: str,
        column_definitions: dict[str, str],
    ) -> None:
        existing_columns = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column_name, column_definition in column_definitions.items():
            if column_name not in existing_columns:
                connection.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
                )

    def start_auth_session(self, payload: OpenAiStartRequest) -> tuple[PendingAuthFlow, AuthSession]:
        now = datetime.now(UTC)
        now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        expires_at = (now + timedelta(seconds=self.settings.session_ttl_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
        user_id = f"user_{uuid4().hex[:12]}"
        device_session_id = f"device_{uuid4().hex[:12]}"
        session_id = f"session_{uuid4().hex[:16]}"
        state = secrets.token_urlsafe(24)
        provider_subject = f"pending:{state[:12]}"
        scopes = list(self.settings.provider_scopes)
        code_verifier, code_challenge = generate_pkce_pair()

        with self._connect() as connection:
            connection.execute(
                "INSERT INTO user (id, status, display_name, created_at) VALUES (?, ?, ?, ?)",
                (user_id, "active", payload.device_label, now_iso),
            )
            connection.execute(
                """
                INSERT INTO auth_account (
                    user_id, provider, provider_subject, scope_json, token_ref, connected_at, last_refresh_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, "openai", provider_subject, json.dumps(scopes), None, now_iso, now_iso),
            )
            connection.execute(
                """
                INSERT INTO device_session (
                    id, user_id, device_label, platform, session_id, auth_state,
                    provider_subject, scopes_json, connected_at, expires_at, last_seen_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    device_session_id,
                    user_id,
                    payload.device_label,
                    payload.platform.value,
                    session_id,
                    "pending_consent",
                    provider_subject,
                    json.dumps(scopes),
                    now_iso,
                    expires_at,
                    now_iso,
                    now_iso,
                ),
            )
            connection.execute(
                """
                INSERT INTO auth_flow (
                    oauth_state, device_session_id, redirect_uri, code_verifier,
                    code_challenge, consumed_at, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state,
                    device_session_id,
                    payload.redirect_uri,
                    code_verifier,
                    code_challenge,
                    None,
                    now_iso,
                    expires_at,
                ),
            )

        pending_flow = PendingAuthFlow(
            oauth_state=state,
            user_id=user_id,
            device_session_id=device_session_id,
            session_id=session_id,
            redirect_uri=payload.redirect_uri,
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            expires_at=expires_at,
        )
        auth_session = self.get_auth_session(session_id)
        if auth_session is None:
            raise ValueError("failed to resolve newly created auth session")
        return pending_flow, auth_session

    def get_pending_auth_flow(self, oauth_state: str) -> PendingAuthFlow | None:
        now_iso = _utc_now_iso()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    auth_flow.oauth_state,
                    device_session.user_id,
                    auth_flow.device_session_id,
                    device_session.session_id,
                    auth_flow.redirect_uri,
                    auth_flow.code_verifier,
                    auth_flow.code_challenge,
                    auth_flow.expires_at
                FROM auth_flow
                INNER JOIN device_session ON device_session.id = auth_flow.device_session_id
                WHERE auth_flow.oauth_state = ?
                  AND auth_flow.consumed_at IS NULL
                  AND auth_flow.expires_at >= ?
                """,
                (oauth_state, now_iso),
            ).fetchone()
        if row is None:
            return None
        return PendingAuthFlow(
            oauth_state=row["oauth_state"],
            user_id=row["user_id"],
            device_session_id=row["device_session_id"],
            session_id=row["session_id"],
            redirect_uri=row["redirect_uri"],
            code_verifier=row["code_verifier"],
            code_challenge=row["code_challenge"],
            expires_at=row["expires_at"],
        )

    def complete_auth_flow(
        self,
        oauth_state: str,
        identity: ProviderIdentity,
        token_bundle: ProviderTokenBundle,
    ) -> tuple[AuthSession | None, str | None]:
        pending_flow = self.get_pending_auth_flow(oauth_state)
        if pending_flow is None:
            return None, None

        connected_at = _utc_now_iso()
        scopes_json = json.dumps(list(identity.scopes))

        with self._connect() as connection:
            existing_auth = connection.execute(
                """
                SELECT user_id
                FROM auth_account
                WHERE provider = ? AND provider_subject = ?
                """,
                ("openai", identity.provider_subject),
            ).fetchone()
            canonical_user_id = existing_auth["user_id"] if existing_auth is not None else pending_flow.user_id

            if canonical_user_id != pending_flow.user_id:
                connection.execute(
                    "UPDATE memory_item SET user_id = ? WHERE user_id = ?",
                    (canonical_user_id, pending_flow.user_id),
                )
                connection.execute(
                    "UPDATE session_checkpoint SET user_id = ? WHERE user_id = ?",
                    (canonical_user_id, pending_flow.user_id),
                )
                connection.execute(
                    "UPDATE memory_export_job SET user_id = ? WHERE user_id = ?",
                    (canonical_user_id, pending_flow.user_id),
                )
                connection.execute(
                    "UPDATE memory_delete_job SET user_id = ? WHERE user_id = ?",
                    (canonical_user_id, pending_flow.user_id),
                )
                connection.execute(
                    "UPDATE device_session SET user_id = ? WHERE id = ?",
                    (canonical_user_id, pending_flow.device_session_id),
                )
                connection.execute(
                    "DELETE FROM auth_account WHERE user_id = ? AND provider = ?",
                    (pending_flow.user_id, "openai"),
                )
                connection.execute("DELETE FROM user WHERE id = ?", (pending_flow.user_id,))

            connection.execute(
                """
                INSERT INTO auth_account (
                    user_id, provider, provider_subject, scope_json, token_ref, connected_at, last_refresh_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, provider) DO UPDATE SET
                    provider_subject = excluded.provider_subject,
                    scope_json = excluded.scope_json,
                    token_ref = excluded.token_ref,
                    connected_at = excluded.connected_at,
                    last_refresh_at = excluded.last_refresh_at
                """,
                (
                    canonical_user_id,
                    "openai",
                    identity.provider_subject,
                    scopes_json,
                    token_bundle.to_token_ref(),
                    connected_at,
                    connected_at,
                ),
            )
            connection.execute(
                """
                UPDATE device_session
                SET auth_state = ?, provider_subject = ?, scopes_json = ?, connected_at = ?
                WHERE id = ?
                """,
                ("active", identity.provider_subject, scopes_json, connected_at, pending_flow.device_session_id),
            )
            if identity.display_name:
                connection.execute(
                    "UPDATE user SET display_name = ? WHERE id = ?",
                    (identity.display_name, canonical_user_id),
                )
            connection.execute(
                "UPDATE auth_flow SET consumed_at = ? WHERE oauth_state = ?",
                (connected_at, oauth_state),
            )

        return self.get_auth_session(pending_flow.session_id), pending_flow.redirect_uri

    def fail_auth_flow(self, oauth_state: str) -> str | None:
        pending_flow = self.get_pending_auth_flow(oauth_state)
        if pending_flow is None:
            return None

        failed_at = _utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                "UPDATE device_session SET auth_state = ? WHERE id = ?",
                ("reauth_required", pending_flow.device_session_id),
            )
            connection.execute(
                "UPDATE auth_flow SET consumed_at = ? WHERE oauth_state = ?",
                (failed_at, oauth_state),
            )
        return pending_flow.redirect_uri

    def get_auth_session(self, session_id: str) -> AuthSession | None:
        now_iso = _utc_now_iso()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    user_id,
                    id AS device_session_id,
                    auth_state,
                    provider_subject,
                    scopes_json,
                    connected_at,
                    session_id,
                    expires_at,
                    last_seen_at
                FROM device_session
                WHERE session_id = ? AND expires_at >= ?
                """,
                (session_id, now_iso),
            ).fetchone()

        if row is None:
            return None
        return self._auth_session_from_row(row)

    def touch_session(self, session_id: str) -> AuthSession | None:
        last_seen_at = _utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                "UPDATE device_session SET last_seen_at = ? WHERE session_id = ?",
                (last_seen_at, session_id),
            )
        return self.get_auth_session(session_id)

    def get_telegram_transport_cursor(self, cursor_name: str = "polling") -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT next_update_id
                FROM telegram_transport_cursor
                WHERE cursor_name = ?
                """,
                (cursor_name,),
            ).fetchone()
        return int(row["next_update_id"]) if row is not None else 0

    def advance_telegram_transport_cursor(
        self,
        *,
        cursor_name: str,
        next_update_id: int,
    ) -> int:
        if next_update_id < 0:
            raise ValueError("telegram transport cursor must be non-negative")

        updated_at = _utc_now_iso()
        with self._connect() as connection:
            current_row = connection.execute(
                """
                SELECT next_update_id
                FROM telegram_transport_cursor
                WHERE cursor_name = ?
                """,
                (cursor_name,),
            ).fetchone()
            stored_next_update_id = max(next_update_id, int(current_row["next_update_id"])) if current_row else next_update_id
            connection.execute(
                """
                INSERT INTO telegram_transport_cursor (cursor_name, next_update_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cursor_name) DO UPDATE SET
                    next_update_id = excluded.next_update_id,
                    updated_at = excluded.updated_at
                """,
                (cursor_name, stored_next_update_id, updated_at),
            )
        return stored_next_update_id

    def get_telegram_link_state(self, user_id: str) -> TelegramLinkState:
        with self._connect() as connection:
            row = self._get_telegram_link_row(connection, user_id)
        if row is None:
            return TelegramLinkState(
                status=TelegramLinkStatus.NOT_LINKED,
                is_linked=False,
            )
        return self._telegram_link_state_from_row(row)

    def start_telegram_link(self, user_id: str) -> TelegramLinkState:
        requested_at = _utc_now_iso()
        expires_at = (datetime.now(UTC) + timedelta(seconds=self.settings.telegram_link_ttl_seconds)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        link_code = secrets.token_hex(3).upper()
        link_token = secrets.token_urlsafe(24)
        link_token_hash = hashlib.sha256(link_token.encode("utf-8")).hexdigest()
        bot_deep_link = self._build_telegram_bot_deep_link(link_token)

        with self._connect() as connection:
            existing_row = self._get_telegram_link_row(connection, user_id)
            if existing_row is not None and existing_row["status"] == TelegramLinkStatus.LINKED.value:
                return self._telegram_link_state_from_row(existing_row)

            connection.execute(
                """
                INSERT INTO telegram_link_state (
                    user_id, status, link_code, link_token_hash, expires_at,
                    telegram_user_id, telegram_username, telegram_display_name, telegram_chat_id,
                    linked_at, last_event_at, last_error_code, last_error_message, last_resume_token_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    status = excluded.status,
                    link_code = excluded.link_code,
                    link_token_hash = excluded.link_token_hash,
                    expires_at = excluded.expires_at,
                    last_event_at = excluded.last_event_at,
                    last_error_code = excluded.last_error_code,
                    last_error_message = excluded.last_error_message
                """,
                (
                    user_id,
                    TelegramLinkStatus.PENDING.value,
                    link_code,
                    link_token_hash,
                    expires_at,
                    None,
                    None,
                    None,
                    None,
                    None,
                    requested_at,
                    None,
                    None,
                    None,
                ),
            )
            stored_row = self._get_telegram_link_row(connection, user_id)
        if stored_row is None:
            raise ValueError("failed to store telegram link state")
        return self._telegram_link_state_from_row(stored_row, bot_deep_link=bot_deep_link)

    def complete_telegram_link_from_token(
        self,
        *,
        link_token: str,
        telegram_user_id: str,
        telegram_chat_id: str,
        telegram_username: str | None = None,
        telegram_display_name: str | None = None,
    ) -> TelegramLinkState:
        normalized_token = link_token.strip()
        if not normalized_token:
            raise TelegramLinkError("link_token_missing", "telegram link token is required")

        link_token_hash = hashlib.sha256(normalized_token.encode("utf-8")).hexdigest()
        linked_at = _utc_now_iso()
        with self._connect() as connection:
            row = self._get_telegram_link_row_by_token_hash(connection, link_token_hash)
            if row is None:
                raise TelegramLinkError("link_token_invalid", "telegram link token invalid or expired")
            if row["status"] != TelegramLinkStatus.PENDING.value:
                raise TelegramLinkError("pending_link_missing", "pending telegram link not found")
            if row["expires_at"] is not None and row["expires_at"] < linked_at:
                self._mark_telegram_link_error(
                    connection,
                    user_id=row["user_id"],
                    error_code="link_expired",
                    error_message="Telegram linking code expired.",
                )
                raise TelegramLinkError("link_token_invalid", "telegram link token invalid or expired")

            self._complete_telegram_link_row(
                connection,
                user_id=row["user_id"],
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
                telegram_username=telegram_username,
                telegram_display_name=telegram_display_name,
                linked_at=linked_at,
                last_resume_token_ref=row["last_resume_token_ref"],
            )
            self._record_telegram_handoff(
                connection,
                user_id=row["user_id"],
                handoff_kind=HandoffKind.RESUME_LINK,
                occurred_at=linked_at,
                draft_text=None,
                telegram_chat_id=telegram_chat_id,
                telegram_username=telegram_username,
                telegram_display_name=telegram_display_name,
            )
            stored_row = self._get_telegram_link_row(connection, row["user_id"])
        if stored_row is None:
            raise TelegramLinkError("link_state_missing", "failed to resolve linked telegram state")
        return self._telegram_link_state_from_row(stored_row)

    def complete_mock_telegram_link(
        self,
        user_id: str,
        *,
        link_code: str,
        telegram_user_id: str,
        telegram_chat_id: str,
        telegram_username: str | None = None,
        telegram_display_name: str | None = None,
        last_resume_token_ref: str | None = None,
    ) -> TelegramLinkState:
        linked_at = _utc_now_iso()
        with self._connect() as connection:
            row = self._get_telegram_link_row(connection, user_id)
            if row is None or row["status"] != TelegramLinkStatus.PENDING.value:
                raise TelegramLinkError("pending_link_missing", "pending telegram link not found")
            if row["link_code"] != link_code:
                raise TelegramLinkError("link_code_invalid", "telegram link code invalid or expired")

            stored_row = self._complete_telegram_link_row(
                connection,
                user_id=user_id,
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
                telegram_username=telegram_username,
                telegram_display_name=telegram_display_name,
                linked_at=linked_at,
                last_resume_token_ref=last_resume_token_ref,
            )
        return self._telegram_link_state_from_row(stored_row)

    def record_telegram_resume_handoff(
        self,
        *,
        telegram_user_id: str,
        telegram_chat_id: str,
        telegram_username: str | None = None,
        telegram_display_name: str | None = None,
    ) -> SessionCheckpoint:
        occurred_at = _utc_now_iso()
        with self._connect() as connection:
            link_row = self._get_linked_telegram_row(
                connection,
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
            )
            return self._record_telegram_handoff(
                connection,
                user_id=link_row["user_id"],
                handoff_kind=HandoffKind.RESUME_LINK,
                occurred_at=occurred_at,
                draft_text=None,
                telegram_chat_id=telegram_chat_id,
                telegram_username=telegram_username,
                telegram_display_name=telegram_display_name,
            )

    def record_telegram_quick_capture(
        self,
        *,
        telegram_user_id: str,
        telegram_chat_id: str,
        text: str,
        telegram_username: str | None = None,
        telegram_display_name: str | None = None,
    ) -> SessionCheckpoint:
        captured_text = text.strip()
        if not captured_text:
            raise TelegramLinkError("quick_capture_empty", "telegram quick capture text is required")

        occurred_at = _utc_now_iso()
        with self._connect() as connection:
            link_row = self._get_linked_telegram_row(
                connection,
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
            )
            return self._record_telegram_handoff(
                connection,
                user_id=link_row["user_id"],
                handoff_kind=HandoffKind.QUICK_CAPTURE,
                occurred_at=occurred_at,
                draft_text=captured_text,
                telegram_chat_id=telegram_chat_id,
                telegram_username=telegram_username,
                telegram_display_name=telegram_display_name,
            )

    def list_runtime_jobs(
        self,
        user_id: str,
        *,
        kind: JobKind | None = None,
        status: JobStatus | None = None,
        limit: int = 20,
    ) -> RuntimeJobsResponse:
        query = """
            SELECT
                job_id, user_id, device_session_id, kind, status, requested_at,
                available_at, started_at, completed_at, error_code, error_message, resource_id,
                attempt_count,
                audit_surface, audit_conversation_id, details_json
            FROM runtime_job
            WHERE user_id = ?
        """
        params: list[Any] = [user_id]
        if kind is not None:
            query += " AND kind = ?"
            params.append(kind.value)
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY requested_at DESC, rowid DESC LIMIT ?"
        params.append(limit)

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return RuntimeJobsResponse(items=[self._runtime_job_from_row(row) for row in rows])

    def list_memory_broker_workspaces(self, user_id: str) -> MemoryBrokerWorkspaceListResponse:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    user_id, workspace_id, status, provider, project_ids_json, source_surface,
                    granted_at, revoked_at, updated_at, last_brokered_at, last_audit_id,
                    last_audit_at, last_error_code, last_error_message
                FROM memory_broker_workspace
                WHERE user_id = ?
                ORDER BY COALESCE(updated_at, granted_at, revoked_at) DESC, workspace_id ASC
                """,
                (user_id,),
            ).fetchall()
        return MemoryBrokerWorkspaceListResponse(
            items=[self._memory_broker_workspace_state_from_row(row) for row in rows]
        )

    def get_memory_broker_workspace(
        self,
        user_id: str,
        workspace_id: str,
    ) -> MemoryBrokerWorkspaceState:
        normalized_workspace_id = workspace_id.strip()
        if not normalized_workspace_id:
            raise ValueError("workspace_id is required")

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    user_id, workspace_id, status, provider, project_ids_json, source_surface,
                    granted_at, revoked_at, updated_at, last_brokered_at, last_audit_id,
                    last_audit_at, last_error_code, last_error_message
                FROM memory_broker_workspace
                WHERE user_id = ? AND workspace_id = ?
                """,
                (user_id, normalized_workspace_id),
            ).fetchone()
        return self._memory_broker_workspace_state_from_row(row, workspace_id=normalized_workspace_id)

    def upsert_memory_broker_workspace(
        self,
        user_id: str,
        workspace_id: str,
        payload: MemoryBrokerWorkspaceUpsertRequest,
    ) -> MemoryBrokerWorkspaceState:
        normalized_workspace_id = workspace_id.strip()
        if not normalized_workspace_id:
            raise ValueError("workspace_id is required")
        if payload.source_surface == Surface.TELEGRAM:
            raise ValueError("telegram surface cannot administer workspace memory broker opt-in")

        updated_at = _utc_now_iso()
        provider = self._memory_broker_provider()
        provider_status = self.memory_broker.provider_status()
        scope_project_ids = list(payload.project_ids)
        next_status = (
            MemoryBrokerOptInStatus.ENABLED if payload.enabled else MemoryBrokerOptInStatus.DISABLED
        )

        with self._connect() as connection:
            existing_row = connection.execute(
                """
                SELECT status, granted_at
                FROM memory_broker_workspace
                WHERE user_id = ? AND workspace_id = ?
                """,
                (user_id, normalized_workspace_id),
            ).fetchone()
            granted_at = existing_row["granted_at"] if existing_row is not None else None
            if payload.enabled and granted_at is None:
                granted_at = updated_at
            revoked_at = updated_at if not payload.enabled else None
            audit = self._record_memory_broker_audit(
                connection,
                user_id=user_id,
                workspace_id=normalized_workspace_id,
                project_id=None,
                action=MemoryBrokerAuditAction.OPT_IN_UPDATED,
                status=MemoryBrokerAuditStatus.SUCCEEDED,
                source_surface=payload.source_surface,
                conversation_id=None,
                query=None,
                result_count=0,
                details={
                    "enabled": payload.enabled,
                    "project_ids": scope_project_ids,
                    "provider_status": provider_status.value,
                },
            )
            connection.execute(
                """
                INSERT INTO memory_broker_workspace (
                    user_id, workspace_id, status, provider, project_ids_json, source_surface,
                    granted_at, revoked_at, updated_at, last_brokered_at, last_audit_id,
                    last_audit_at, last_error_code, last_error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, workspace_id) DO UPDATE SET
                    status = excluded.status,
                    provider = excluded.provider,
                    project_ids_json = excluded.project_ids_json,
                    source_surface = excluded.source_surface,
                    granted_at = excluded.granted_at,
                    revoked_at = excluded.revoked_at,
                    updated_at = excluded.updated_at,
                    last_audit_id = excluded.last_audit_id,
                    last_audit_at = excluded.last_audit_at,
                    last_error_code = excluded.last_error_code,
                    last_error_message = excluded.last_error_message
                """,
                (
                    user_id,
                    normalized_workspace_id,
                    next_status.value,
                    provider.value,
                    json.dumps(scope_project_ids),
                    payload.source_surface.value,
                    granted_at,
                    revoked_at,
                    updated_at,
                    None,
                    audit.audit_id,
                    audit.created_at,
                    None,
                    None,
                ),
            )
            stored_row = connection.execute(
                """
                SELECT
                    user_id, workspace_id, status, provider, project_ids_json, source_surface,
                    granted_at, revoked_at, updated_at, last_brokered_at, last_audit_id,
                    last_audit_at, last_error_code, last_error_message
                FROM memory_broker_workspace
                WHERE user_id = ? AND workspace_id = ?
                """,
                (user_id, normalized_workspace_id),
            ).fetchone()
        if stored_row is None:
            raise ValueError("failed to store workspace memory broker state")
        return self._memory_broker_workspace_state_from_row(stored_row)

    def query_memory_broker_workspace(
        self,
        user_id: str,
        device_session_id: str,
        workspace_id: str,
        payload: MemoryBrokerQueryRequest,
    ) -> MemoryBrokerQueryResponse:
        normalized_workspace_id = workspace_id.strip()
        if not normalized_workspace_id:
            raise ValueError("workspace_id is required")
        if payload.source_surface == Surface.TELEGRAM:
            raise ValueError("telegram surface cannot request raw workspace memory broker retrieval")

        provider = self._memory_broker_provider()
        queried_at = _utc_now_iso()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    user_id, workspace_id, status, provider, project_ids_json, source_surface,
                    granted_at, revoked_at, updated_at, last_brokered_at, last_audit_id,
                    last_audit_at, last_error_code, last_error_message
                FROM memory_broker_workspace
                WHERE user_id = ? AND workspace_id = ?
                """,
                (user_id, normalized_workspace_id),
            ).fetchone()
            if row is None or row["status"] != MemoryBrokerOptInStatus.ENABLED.value:
                raise ValueError("workspace memory broker is not enabled for this workspace")

            allowed_project_ids = self._load_memory_broker_project_ids(row["project_ids_json"])
            if payload.project_id is not None and allowed_project_ids and payload.project_id not in allowed_project_ids:
                raise ValueError("project_id is outside the opted-in workspace scope")

            provider_status = self.memory_broker.provider_status()
            provider_message = self.memory_broker.provider_message()
            results: list[MemoryBrokerResult] = []
            audit_status = MemoryBrokerAuditStatus.SUCCEEDED
            last_error_code: str | None = None
            last_error_message: str | None = None

            if provider_status == MemoryBrokerProviderStatus.READY:
                backend_results = self.memory_broker.search(
                    MemoryBrokerSearchContext(
                        user_id=user_id,
                        workspace_id=normalized_workspace_id,
                        project_id=payload.project_id,
                        allowed_project_ids=tuple(allowed_project_ids),
                        query=payload.query,
                        limit=payload.limit,
                    )
                )
                results = self._filter_memory_broker_results(
                    backend_results,
                    workspace_id=normalized_workspace_id,
                    project_id=payload.project_id,
                    allowed_project_ids=allowed_project_ids,
                    limit=payload.limit,
                )
            else:
                audit_status = MemoryBrokerAuditStatus.UNAVAILABLE
                last_error_code = "provider_unavailable"
                last_error_message = provider_message or "KG memory broker is unavailable."

            audit = self._record_memory_broker_audit(
                connection,
                user_id=user_id,
                workspace_id=normalized_workspace_id,
                project_id=payload.project_id,
                action=MemoryBrokerAuditAction.READ,
                status=audit_status,
                source_surface=payload.source_surface,
                conversation_id=self._conversation_for_device_session(connection, user_id, device_session_id),
                query=payload.query,
                result_count=len(results),
                details={
                    "provider_status": provider_status.value,
                    "scope_project_ids": allowed_project_ids,
                },
            )
            connection.execute(
                """
                UPDATE memory_broker_workspace
                SET provider = ?, last_brokered_at = ?, last_audit_id = ?, last_audit_at = ?,
                    last_error_code = ?, last_error_message = ?
                WHERE user_id = ? AND workspace_id = ?
                """,
                (
                    provider.value,
                    queried_at,
                    audit.audit_id,
                    audit.created_at,
                    last_error_code,
                    last_error_message,
                    user_id,
                    normalized_workspace_id,
                ),
            )

        return MemoryBrokerQueryResponse(
            workspace_id=normalized_workspace_id,
            project_id=payload.project_id,
            query=payload.query,
            provider=provider,
            provider_status=self.memory_broker.provider_status(),
            scope=MemoryBrokerScope(
                workspace_id=normalized_workspace_id,
                project_ids=allowed_project_ids,
            ),
            results=results,
            audit=audit,
        )

    def list_memory_items(self, user_id: str, status: str | None, limit: int) -> MemoryItemsResponse:
        query = """
            SELECT id, user_id, kind, content, status, importance, source_type, created_at, updated_at, last_used_at
            FROM memory_item
            WHERE user_id = ?
        """
        params: list[Any] = [user_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
            memory_ids = [row["id"] for row in rows]
            sources_by_memory_id = self._list_memory_sources(connection, memory_ids)
        return MemoryItemsResponse(
            items=[
                self._memory_record_from_row(row, sources_by_memory_id.get(row["id"], []))
                for row in rows
            ]
        )

    def create_memory_item(self, user_id: str, item: MemoryCreateRequest) -> MemoryRecord:
        if item.user_id != user_id:
            raise ValueError("memory_item.user_id must match the authenticated user")
        for source in item.sources:
            if source.memory_id != item.id:
                raise ValueError("memory_source.memory_id must match memory_item.id")

        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO memory_item (
                        id, user_id, kind, content, status, importance,
                        source_type, created_at, updated_at, last_used_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.id,
                        item.user_id,
                        item.kind.value,
                        item.content,
                        item.status.value,
                        item.importance,
                        item.source_type.value,
                        item.created_at,
                        item.updated_at,
                        item.last_used_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"memory_item insert failed: {exc}") from exc
            self._replace_memory_sources(connection, item.id, item.sources)

            self._insert_memory_revision(
                connection,
                memory_id=item.id,
                action="created",
                diff={"content": item.content, "status": item.status.value},
            )
            stored_item = connection.execute(
                """
                SELECT id, user_id, kind, content, status, importance, source_type, created_at, updated_at, last_used_at
                FROM memory_item
                WHERE id = ? AND user_id = ?
                """,
                (item.id, user_id),
            ).fetchone()
            if stored_item is None:
                raise ValueError("memory_item insert failed: stored item missing")
            sources = self._list_memory_sources(connection, [item.id]).get(item.id, [])
        return self._memory_record_from_row(stored_item, sources)

    def patch_memory_item(self, user_id: str, memory_id: str, patch: MemoryItemPatchRequest) -> MemoryRecord | None:
        with self._connect() as connection:
            existing_row = connection.execute(
                """
                SELECT id, user_id, kind, content, status, importance, source_type, created_at, updated_at, last_used_at
                FROM memory_item
                WHERE id = ? AND user_id = ?
                """,
                (memory_id, user_id),
            ).fetchone()
            if existing_row is None:
                return None

            existing = self._memory_record_from_row(
                existing_row,
                self._list_memory_sources(connection, [memory_id]).get(memory_id, []),
            )
            updates = patch.model_dump(exclude_none=True)
            if not updates:
                return existing

            diff: dict[str, Any] = {}
            params: list[Any] = []
            assignments: list[str] = []
            for field_name, value in updates.items():
                db_value = value.value if hasattr(value, "value") else value
                assignments.append(f"{field_name} = ?")
                params.append(db_value)
                diff[field_name] = db_value

            updated_at = _utc_now_iso()
            assignments.append("updated_at = ?")
            params.append(updated_at)
            params.extend([memory_id, user_id])

            connection.execute(
                f"UPDATE memory_item SET {', '.join(assignments)} WHERE id = ? AND user_id = ?",
                params,
            )

            action = "updated"
            if updates.get("status") == MemoryStatus.DELETED:
                action = "deleted"
            elif updates.get("status") == MemoryStatus.ARCHIVED:
                action = "archived"

            self._insert_memory_revision(connection, memory_id=memory_id, action=action, diff=diff)

            refreshed_row = connection.execute(
                """
                SELECT id, user_id, kind, content, status, importance, source_type, created_at, updated_at, last_used_at
                FROM memory_item
                WHERE id = ? AND user_id = ?
                """,
                (memory_id, user_id),
            ).fetchone()
            sources = self._list_memory_sources(connection, [memory_id]).get(memory_id, [])

        return self._memory_record_from_row(refreshed_row, sources) if refreshed_row is not None else None

    def delete_memory_item(
        self,
        user_id: str,
        device_session_id: str,
        memory_id: str,
    ) -> MemoryDeleteReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM memory_item WHERE id = ? AND user_id = ?",
                (memory_id, user_id),
            ).fetchone()
            if row is None:
                return None

            existing_job = connection.execute(
                """
                SELECT delete_id, requested_at, purge_after
                FROM memory_delete_job
                WHERE memory_id = ? AND user_id = ?
                ORDER BY requested_at DESC
                LIMIT 1
                """,
                (memory_id, user_id),
            ).fetchone()
            if row["status"] == MemoryStatus.DELETED.value and existing_job is not None:
                self._record_runtime_job(
                    connection,
                    job_id=existing_job["delete_id"],
                    user_id=user_id,
                    device_session_id=device_session_id,
                    kind=JobKind.MEMORY_DELETE,
                    status=JobStatus.QUEUED,
                    requested_at=existing_job["requested_at"],
                    available_at=existing_job["purge_after"],
                    started_at=None,
                    completed_at=None,
                    error_code=None,
                    error_message=None,
                    resource_id=memory_id,
                    details={
                        "memory_id": memory_id,
                        "purge_after": existing_job["purge_after"],
                    },
                )
                return MemoryDeleteReceipt(
                    delete_id=existing_job["delete_id"],
                    job_id=existing_job["delete_id"],
                    memory_id=memory_id,
                    status=MemoryStatus.DELETED,
                    purge_status=MemoryDeleteStatus.PENDING_PURGE,
                    requested_at=existing_job["requested_at"],
                    purge_after=existing_job["purge_after"],
                )

            requested_at = _utc_now_iso()
            purge_after = (
                datetime.now(UTC) + timedelta(seconds=self.settings.memory_delete_retention_seconds)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            delete_id = f"delete_{uuid4().hex[:12]}"
            connection.execute(
                "UPDATE memory_item SET status = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                (MemoryStatus.DELETED.value, requested_at, memory_id, user_id),
            )
            connection.execute(
                """
                INSERT INTO memory_delete_job (delete_id, user_id, memory_id, status, requested_at, purge_after)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    delete_id,
                    user_id,
                    memory_id,
                    MemoryDeleteStatus.PENDING_PURGE.value,
                    requested_at,
                    purge_after,
                ),
            )
            self._insert_memory_revision(
                connection,
                memory_id=memory_id,
                action="deleted",
                diff={"status": MemoryStatus.DELETED.value},
            )
            self._record_runtime_job(
                connection,
                job_id=delete_id,
                user_id=user_id,
                device_session_id=device_session_id,
                kind=JobKind.MEMORY_DELETE,
                status=JobStatus.QUEUED,
                requested_at=requested_at,
                available_at=purge_after,
                started_at=None,
                completed_at=None,
                error_code=None,
                error_message=None,
                resource_id=memory_id,
                details={
                    "memory_id": memory_id,
                    "purge_after": purge_after,
                },
            )
        return MemoryDeleteReceipt(
            delete_id=delete_id,
            job_id=delete_id,
            memory_id=memory_id,
            status=MemoryStatus.DELETED,
            purge_status=MemoryDeleteStatus.PENDING_PURGE,
            requested_at=requested_at,
            purge_after=purge_after,
        )

    def create_memory_export(
        self,
        user_id: str,
        device_session_id: str,
        export_format: MemoryExportFormat = MemoryExportFormat.JSON,
    ) -> MemoryExportResponse:
        requested_at = _utc_now_iso()
        expires_at = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        export_id = f"memexp_{uuid4().hex[:12]}"
        suggested_filename = f"assistant-memory-{requested_at[:10]}-{export_id}.json"

        with self._connect() as connection:
            item_rows = connection.execute(
                """
                SELECT id, user_id, kind, content, status, importance, source_type, created_at, updated_at, last_used_at
                FROM memory_item
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
            memory_ids = [row["id"] for row in item_rows]
            sources_by_memory_id = self._list_memory_sources(connection, memory_ids)
            revisions_by_memory_id = self._list_memory_revisions(connection, memory_ids)
            export_records = [
                MemoryExportRecord(
                    item=self._memory_record_from_row(row, sources_by_memory_id.get(row["id"], [])),
                    revisions=revisions_by_memory_id.get(row["id"], []),
                )
                for row in item_rows
            ]
            export_response = MemoryExportResponse(
                export_id=export_id,
                job_id=export_id,
                status=MemoryExportStatus.READY,
                format=export_format,
                requested_at=requested_at,
                expires_at=expires_at,
                suggested_filename=suggested_filename,
                item_count=len(export_records),
                items=export_records,
            )

            artifact_dir = self.settings.artifacts_dir / "memory_exports"
            artifact_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = artifact_dir / f"{export_id}.json"
            artifact_reference = self._artifact_reference(artifact_path)
            artifact_path.write_text(
                json.dumps(export_response.model_dump(mode="json"), indent=2),
                encoding="utf-8",
            )
            connection.execute(
                """
                INSERT INTO memory_export_job (
                    export_id, user_id, status, format, artifact_path, item_count, requested_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    export_id,
                    user_id,
                    MemoryExportStatus.READY.value,
                    export_format.value,
                    artifact_reference,
                    export_response.item_count,
                    requested_at,
                    expires_at,
                ),
            )
            self._record_runtime_job(
                connection,
                job_id=export_id,
                user_id=user_id,
                device_session_id=device_session_id,
                kind=JobKind.MEMORY_EXPORT,
                status=JobStatus.SUCCEEDED,
                requested_at=requested_at,
                available_at=requested_at,
                started_at=requested_at,
                completed_at=requested_at,
                error_code=None,
                error_message=None,
                resource_id=export_id,
                details={
                    "artifact_path": artifact_reference,
                    "format": export_format.value,
                    "item_count": export_response.item_count,
                },
            )
        return export_response

    def schedule_reminder_delivery(
        self,
        user_id: str,
        device_session_id: str,
        *,
        scheduled_for: str,
        payload: dict[str, object] | None = None,
        channel: Surface = Surface.TELEGRAM,
        follow_up_policy: ReminderFollowUpPolicy | None = None,
    ) -> ReminderRecord:
        if channel != Surface.TELEGRAM:
            raise ValueError("only telegram reminder delivery is currently supported")

        created_at = _utc_now_iso()
        reminder_id = f"reminder_{uuid4().hex[:12]}"
        reminder_payload = dict(payload or {})
        reminder_follow_up_policy = follow_up_policy or ReminderFollowUpPolicy()
        message = reminder_payload.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("reminder payload.message is required")
        reminder_payload["message"] = message.strip()
        scheduled_time = scheduled_for.strip()
        if not scheduled_time:
            raise ValueError("scheduled_for is required")
        follow_up_state = ReminderFollowUpState(
            next_attempt_at=scheduled_time,
            last_transition_at=created_at,
            last_transition_reason="scheduled",
        )

        with self._connect() as connection:
            link_row = self._get_telegram_link_row(connection, user_id)
            if link_row is None or link_row["status"] != TelegramLinkStatus.LINKED.value:
                raise ValueError("linked Telegram companion is required before scheduling telegram reminders")
            if link_row["telegram_chat_id"] is None:
                raise ValueError("linked Telegram companion is missing a delivery chat")
            self._record_runtime_job(
                connection,
                job_id=reminder_id,
                user_id=user_id,
                device_session_id=device_session_id,
                kind=JobKind.REMINDER_DELIVERY,
                status=JobStatus.QUEUED,
                requested_at=created_at,
                available_at=scheduled_time,
                started_at=None,
                completed_at=None,
                error_code=None,
                error_message=None,
                resource_id=reminder_id,
                details=_reminder_runtime_details(
                    reminder_id=reminder_id,
                    scheduled_for=scheduled_time,
                    channel=channel,
                    payload=reminder_payload,
                    delivery_status="scheduled",
                    follow_up_policy=reminder_follow_up_policy,
                    follow_up_state=follow_up_state,
                ),
            )
            connection.execute(
                """
                INSERT INTO reminder_delivery (
                    reminder_id, job_id, user_id, device_session_id, status, channel,
                    scheduled_for, payload_json, created_at, updated_at,
                    delivered_at, canceled_at, last_error_code, last_error_message,
                    follow_up_policy_json, follow_up_state_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reminder_id,
                    reminder_id,
                    user_id,
                    device_session_id,
                    ReminderStatus.SCHEDULED.value,
                    channel.value,
                    scheduled_time,
                    json.dumps(reminder_payload),
                    created_at,
                    created_at,
                    None,
                    None,
                    None,
                    None,
                    json.dumps(reminder_follow_up_policy.model_dump(mode="json")),
                    json.dumps(follow_up_state.model_dump(mode="json")),
                ),
            )
        return ReminderRecord(
            reminder_id=reminder_id,
            job_id=reminder_id,
            user_id=user_id,
            device_session_id=device_session_id,
            status=ReminderStatus.SCHEDULED,
            channel=channel,
            scheduled_for=scheduled_time,
            payload=reminder_payload,
            created_at=created_at,
            updated_at=created_at,
            delivered_at=None,
            canceled_at=None,
            last_error_code=None,
            last_error_message=None,
            follow_up_policy=reminder_follow_up_policy,
            follow_up_state=follow_up_state,
        )

    def get_reminder_delivery(
        self,
        user_id: str,
        reminder_id: str,
    ) -> ReminderRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    reminder_id, job_id, user_id, device_session_id, status, channel,
                    scheduled_for, payload_json, created_at, updated_at,
                    delivered_at, canceled_at, last_error_code, last_error_message,
                    follow_up_policy_json, follow_up_state_json
                FROM reminder_delivery
                WHERE user_id = ? AND reminder_id = ?
                """,
                (user_id, reminder_id),
            ).fetchone()
        if row is None:
            return None
        return self._reminder_record_from_row(row)

    def list_reminder_deliveries(
        self,
        user_id: str,
        *,
        status: ReminderStatus | None = None,
        limit: int = 20,
    ) -> ReminderListResponse:
        query = """
            SELECT
                reminder_id, job_id, user_id, device_session_id, status, channel,
                scheduled_for, payload_json, created_at, updated_at,
                delivered_at, canceled_at, last_error_code, last_error_message,
                follow_up_policy_json, follow_up_state_json
            FROM reminder_delivery
            WHERE user_id = ?
        """
        params: list[Any] = [user_id]
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY scheduled_for DESC, created_at DESC, rowid DESC LIMIT ?"
        params.append(limit)

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return ReminderListResponse(items=[self._reminder_record_from_row(row) for row in rows])

    @staticmethod
    def _get_reminder_with_runtime_job_row(
        connection: sqlite3.Connection,
        user_id: str,
        reminder_id: str,
    ) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT
                reminder_delivery.reminder_id, reminder_delivery.job_id, reminder_delivery.user_id,
                reminder_delivery.device_session_id, reminder_delivery.status, reminder_delivery.channel,
                reminder_delivery.scheduled_for, reminder_delivery.payload_json, reminder_delivery.created_at,
                reminder_delivery.updated_at, reminder_delivery.delivered_at, reminder_delivery.canceled_at,
                reminder_delivery.last_error_code, reminder_delivery.last_error_message,
                reminder_delivery.follow_up_policy_json, reminder_delivery.follow_up_state_json,
                runtime_job.status AS job_status, runtime_job.details_json
            FROM reminder_delivery
            INNER JOIN runtime_job ON runtime_job.job_id = reminder_delivery.job_id
            WHERE reminder_delivery.user_id = ? AND reminder_delivery.reminder_id = ?
            """,
            (user_id, reminder_id),
        ).fetchone()

    def cancel_reminder_delivery(
        self,
        user_id: str,
        reminder_id: str,
    ) -> ReminderRecord | None:
        canceled_at = _utc_now_iso()
        with self._connect() as connection:
            row = self._get_reminder_with_runtime_job_row(connection, user_id, reminder_id)
            if row is None:
                return None
            if row["status"] == ReminderStatus.CANCELED.value:
                return self._reminder_record_from_row(row)
            if row["status"] != ReminderStatus.SCHEDULED.value:
                raise ValueError("only scheduled reminders can be canceled")
            if row["job_status"] not in {JobStatus.QUEUED.value, JobStatus.CANCELED.value}:
                raise ValueError("reminder delivery is already running or completed")

            follow_up_policy = _reminder_follow_up_policy_from_json(row["follow_up_policy_json"])
            current_follow_up_state = _reminder_follow_up_state_from_json(row["follow_up_state_json"])
            updated_follow_up_state = current_follow_up_state.model_copy(
                update={
                    "status": ReminderFollowUpStatus.NONE,
                    "next_attempt_at": None,
                    "last_transition_at": canceled_at,
                    "last_transition_reason": (
                        "canceled_after_follow_up"
                        if current_follow_up_state.attempt_count > 0
                        or current_follow_up_state.status != ReminderFollowUpStatus.NONE
                        else "canceled"
                    ),
                }
            )
            merged_details = _reminder_runtime_details(
                reminder_id=row["reminder_id"],
                scheduled_for=row["scheduled_for"],
                channel=Surface(row["channel"]),
                payload=_json_object(row["payload_json"]),
                delivery_status="canceled",
                follow_up_policy=follow_up_policy,
                follow_up_state=updated_follow_up_state,
            )
            merged_details["canceled_at"] = canceled_at
            connection.execute(
                """
                UPDATE reminder_delivery
                SET status = ?, updated_at = ?, canceled_at = ?,
                    follow_up_state_json = ?
                WHERE user_id = ? AND reminder_id = ?
                """,
                (
                    ReminderStatus.CANCELED.value,
                    canceled_at,
                    canceled_at,
                    json.dumps(updated_follow_up_state.model_dump(mode="json")),
                    user_id,
                    reminder_id,
                ),
            )
            connection.execute(
                """
                UPDATE runtime_job
                SET status = ?, completed_at = ?,
                    details_json = ?, lease_owner = NULL, lease_token = NULL,
                    lease_expires_at = NULL, last_heartbeat_at = NULL
                WHERE job_id = ?
                """,
                (
                    JobStatus.CANCELED.value,
                    canceled_at,
                    json.dumps(merged_details),
                    row["job_id"],
                ),
            )

        stored_reminder = self.get_reminder_delivery(user_id, reminder_id)
        if stored_reminder is None:
            raise ValueError("failed to resolve canceled reminder")
        return stored_reminder

    def _update_reminder_follow_up_schedule(
        self,
        user_id: str,
        reminder_id: str,
        *,
        next_attempt_at: str,
        follow_up_status: ReminderFollowUpStatus,
        delivery_status: str,
        transition_reason: str,
        update_scheduled_for: bool,
    ) -> ReminderRecord:
        validated_state = ReminderFollowUpState(next_attempt_at=next_attempt_at)
        if validated_state.next_attempt_at is None:
            raise ValueError("next_attempt_at is required")
        next_attempt_at = validated_state.next_attempt_at
        updated_at = _utc_now_iso()
        with self._connect() as connection:
            row = self._get_reminder_with_runtime_job_row(connection, user_id, reminder_id)
            if row is None:
                raise ValueError("reminder delivery not found")
            if row["status"] == ReminderStatus.CANCELED.value:
                raise ValueError("canceled reminders cannot be rescheduled")
            if row["status"] == ReminderStatus.DELIVERED.value:
                raise ValueError("delivered reminders cannot be rescheduled")
            if row["job_status"] == JobStatus.RUNNING.value:
                raise ValueError("running reminder delivery cannot be rescheduled")

            follow_up_policy = _reminder_follow_up_policy_from_json(row["follow_up_policy_json"])
            current_follow_up_state = _reminder_follow_up_state_from_json(row["follow_up_state_json"])
            scheduled_for = next_attempt_at if update_scheduled_for else row["scheduled_for"]
            updated_follow_up_state = current_follow_up_state.model_copy(
                update={
                    "status": follow_up_status,
                    "next_attempt_at": next_attempt_at,
                    "last_transition_at": updated_at,
                    "last_transition_reason": transition_reason,
                }
            )
            details = _reminder_runtime_details(
                reminder_id=row["reminder_id"],
                scheduled_for=scheduled_for,
                channel=Surface(row["channel"]),
                payload=_json_object(row["payload_json"]),
                delivery_status=delivery_status,
                follow_up_policy=follow_up_policy,
                follow_up_state=updated_follow_up_state,
            )
            connection.execute(
                """
                UPDATE reminder_delivery
                SET status = ?, scheduled_for = ?, updated_at = ?,
                    delivered_at = NULL, canceled_at = NULL,
                    follow_up_state_json = ?
                WHERE user_id = ? AND reminder_id = ?
                """,
                (
                    ReminderStatus.SCHEDULED.value,
                    scheduled_for,
                    updated_at,
                    json.dumps(updated_follow_up_state.model_dump(mode="json")),
                    user_id,
                    reminder_id,
                ),
            )
            connection.execute(
                """
                UPDATE runtime_job
                SET status = ?, available_at = ?, completed_at = NULL,
                    details_json = ?, lease_owner = NULL, lease_token = NULL,
                    lease_expires_at = NULL, last_heartbeat_at = NULL
                WHERE job_id = ?
                """,
                (
                    JobStatus.QUEUED.value,
                    next_attempt_at,
                    json.dumps(details),
                    row["job_id"],
                ),
            )

        stored_reminder = self.get_reminder_delivery(user_id, reminder_id)
        if stored_reminder is None:
            raise ValueError("failed to resolve updated reminder")
        return stored_reminder

    def snooze_reminder_delivery(
        self,
        user_id: str,
        reminder_id: str,
        *,
        snoozed_until: str,
    ) -> ReminderRecord:
        return self._update_reminder_follow_up_schedule(
            user_id,
            reminder_id,
            next_attempt_at=snoozed_until,
            follow_up_status=ReminderFollowUpStatus.SNOOZED,
            delivery_status="snoozed",
            transition_reason="snoozed",
            update_scheduled_for=False,
        )

    def reschedule_reminder_delivery(
        self,
        user_id: str,
        reminder_id: str,
        *,
        scheduled_for: str,
    ) -> ReminderRecord:
        return self._update_reminder_follow_up_schedule(
            user_id,
            reminder_id,
            next_attempt_at=scheduled_for,
            follow_up_status=ReminderFollowUpStatus.RESCHEDULED,
            delivery_status="rescheduled",
            transition_reason="rescheduled",
            update_scheduled_for=True,
        )

    def get_linked_telegram_delivery_target(self, user_id: str) -> TelegramDeliveryTarget:
        with self._connect() as connection:
            row = self._get_telegram_link_row(connection, user_id)
        if row is None or row["status"] != TelegramLinkStatus.LINKED.value:
            raise TelegramLinkError(
                "telegram_not_linked",
                "telegram companion account must be linked before delivering reminders",
            )
        chat_id = row["telegram_chat_id"]
        if not isinstance(chat_id, str) or not chat_id.strip():
            raise TelegramLinkError(
                "telegram_chat_missing",
                "linked telegram companion is missing a delivery chat",
            )
        return TelegramDeliveryTarget(
            user_id=user_id,
            chat_id=chat_id,
            username=row["telegram_username"],
            display_name=row["telegram_display_name"],
        )

    def mark_reminder_delivered(
        self,
        user_id: str,
        reminder_id: str,
        *,
        attempt_count: int | None = None,
    ) -> ReminderRecord:
        delivered_at = _utc_now_iso()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    reminder_id, channel, scheduled_for, payload_json,
                    follow_up_policy_json, follow_up_state_json
                FROM reminder_delivery
                WHERE user_id = ? AND reminder_id = ?
                """,
                (user_id, reminder_id),
            ).fetchone()
            if row is None:
                raise ValueError("reminder delivery not found")
            follow_up_state = _reminder_follow_up_state_from_json(row["follow_up_state_json"])
            resolved_attempt_count = attempt_count if attempt_count is not None else follow_up_state.attempt_count
            updated_follow_up_state = follow_up_state.model_copy(
                update={
                    "status": ReminderFollowUpStatus.NONE,
                    "attempt_count": resolved_attempt_count,
                    "last_attempt_at": delivered_at,
                    "next_attempt_at": None,
                    "last_transition_at": delivered_at,
                    "last_transition_reason": "delivered_after_retry" if resolved_attempt_count > 1 else "delivered",
                }
            )
            connection.execute(
                """
                UPDATE reminder_delivery
                SET status = ?, updated_at = ?, delivered_at = ?, canceled_at = NULL,
                    last_error_code = NULL, last_error_message = NULL,
                    follow_up_state_json = ?
                WHERE user_id = ? AND reminder_id = ?
                """,
                (
                    ReminderStatus.DELIVERED.value,
                    delivered_at,
                    delivered_at,
                    json.dumps(updated_follow_up_state.model_dump(mode="json")),
                    user_id,
                    reminder_id,
                ),
            )

        stored_reminder = self.get_reminder_delivery(user_id, reminder_id)
        if stored_reminder is None:
            raise ValueError("failed to resolve delivered reminder")
        return stored_reminder

    def mark_reminder_failed(
        self,
        user_id: str,
        reminder_id: str,
        *,
        error_code: str,
        error_message: str,
        attempt_count: int | None = None,
    ) -> ReminderRecord:
        failed_at = _utc_now_iso()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT follow_up_state_json
                FROM reminder_delivery
                WHERE user_id = ? AND reminder_id = ?
                """,
                (user_id, reminder_id),
            ).fetchone()
            if row is None:
                raise ValueError("reminder delivery not found")
            follow_up_state = _reminder_follow_up_state_from_json(row["follow_up_state_json"])
            resolved_attempt_count = attempt_count if attempt_count is not None else follow_up_state.attempt_count
            updated_follow_up_state = follow_up_state.model_copy(
                update={
                    "status": ReminderFollowUpStatus.DEAD_LETTER,
                    "attempt_count": resolved_attempt_count,
                    "last_attempt_at": failed_at,
                    "next_attempt_at": None,
                    "last_transition_at": failed_at,
                    "last_transition_reason": "delivery_failed_dead_letter",
                }
            )
            connection.execute(
                """
                UPDATE reminder_delivery
                SET status = ?, updated_at = ?, delivered_at = NULL, canceled_at = NULL,
                    last_error_code = ?, last_error_message = ?,
                    follow_up_state_json = ?
                WHERE user_id = ? AND reminder_id = ?
                """,
                (
                    ReminderStatus.FAILED.value,
                    failed_at,
                    error_code,
                    error_message,
                    json.dumps(updated_follow_up_state.model_dump(mode="json")),
                    user_id,
                    reminder_id,
                ),
            )

        stored_reminder = self.get_reminder_delivery(user_id, reminder_id)
        if stored_reminder is None:
            raise ValueError("failed to resolve failed reminder")
        return stored_reminder

    def requeue_reminder_delivery_after_failure(
        self,
        *,
        job_id: str,
        lease_token: str,
        user_id: str,
        reminder_id: str,
        error_code: str,
        error_message: str,
        attempt_count: int,
        next_attempt_at: str,
    ) -> RuntimeJobRecord:
        retry_scheduled_at = _utc_now_iso()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    reminder_delivery.reminder_id, reminder_delivery.job_id, reminder_delivery.user_id,
                    reminder_delivery.device_session_id, reminder_delivery.channel, reminder_delivery.scheduled_for,
                    reminder_delivery.payload_json, reminder_delivery.follow_up_policy_json,
                    reminder_delivery.follow_up_state_json
                FROM reminder_delivery
                INNER JOIN runtime_job ON runtime_job.job_id = reminder_delivery.job_id
                WHERE reminder_delivery.user_id = ?
                  AND reminder_delivery.reminder_id = ?
                  AND runtime_job.job_id = ?
                  AND runtime_job.lease_token = ?
                """,
                (user_id, reminder_id, job_id, lease_token),
            ).fetchone()
            if row is None:
                raise ValueError("runtime job lease is missing or expired")

            follow_up_policy = _reminder_follow_up_policy_from_json(row["follow_up_policy_json"])
            follow_up_state = _reminder_follow_up_state_from_json(row["follow_up_state_json"])
            updated_follow_up_state = follow_up_state.model_copy(
                update={
                    "status": ReminderFollowUpStatus.RETRY_SCHEDULED,
                    "attempt_count": attempt_count,
                    "last_attempt_at": retry_scheduled_at,
                    "next_attempt_at": next_attempt_at,
                    "last_transition_at": retry_scheduled_at,
                    "last_transition_reason": "delivery_failed_retry_scheduled",
                }
            )
            details = _reminder_runtime_details(
                reminder_id=row["reminder_id"],
                scheduled_for=row["scheduled_for"],
                channel=Surface(row["channel"]),
                payload=_json_object(row["payload_json"]),
                delivery_status="retry_scheduled",
                follow_up_policy=follow_up_policy,
                follow_up_state=updated_follow_up_state,
            )
            details["retry_scheduled_at"] = retry_scheduled_at
            details["last_error_code"] = error_code
            details["last_error_message"] = error_message

            connection.execute(
                """
                UPDATE reminder_delivery
                SET status = ?, updated_at = ?, delivered_at = NULL, canceled_at = NULL,
                    last_error_code = ?, last_error_message = ?, follow_up_state_json = ?
                WHERE user_id = ? AND reminder_id = ?
                """,
                (
                    ReminderStatus.SCHEDULED.value,
                    retry_scheduled_at,
                    error_code,
                    error_message,
                    json.dumps(updated_follow_up_state.model_dump(mode="json")),
                    user_id,
                    reminder_id,
                ),
            )
            connection.execute(
                """
                UPDATE runtime_job
                SET status = ?, available_at = ?, completed_at = NULL,
                    error_code = ?, error_message = ?, details_json = ?,
                    lease_owner = NULL, lease_token = NULL, lease_expires_at = NULL,
                    last_heartbeat_at = NULL
                WHERE job_id = ? AND lease_token = ?
                """,
                (
                    JobStatus.QUEUED.value,
                    next_attempt_at,
                    error_code,
                    error_message,
                    json.dumps(details),
                    job_id,
                    lease_token,
                ),
            )
            queued_row = connection.execute(
                """
                SELECT
                    job_id, user_id, device_session_id, kind, status, requested_at, available_at,
                    started_at, completed_at, error_code, error_message, resource_id,
                    attempt_count, audit_surface, audit_conversation_id, details_json
                FROM runtime_job
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        if queued_row is None:
            raise ValueError("runtime job row disappeared during retry scheduling")
        return self._runtime_job_from_row(queued_row)

    def claim_next_runtime_job(
        self,
        *,
        worker_id: str,
        supported_kinds: tuple[JobKind, ...],
        lease_seconds: int,
    ) -> ClaimedRuntimeJob | None:
        if not supported_kinds:
            return None

        now = datetime.now(UTC)
        now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        lease_expires_at = (now + timedelta(seconds=lease_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
        kind_values = [kind.value for kind in supported_kinds]
        placeholders = ", ".join("?" for _ in kind_values)

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                f"""
                SELECT
                    job_id, user_id, device_session_id, kind, status, requested_at, available_at,
                    started_at, completed_at, error_code, error_message, resource_id,
                    lease_expires_at, attempt_count, audit_surface, audit_conversation_id, details_json
                FROM runtime_job
                WHERE kind IN ({placeholders})
                  AND (
                    (status = ? AND COALESCE(available_at, requested_at) <= ?)
                    OR (status = ? AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?)
                  )
                ORDER BY COALESCE(available_at, requested_at) ASC, requested_at ASC, rowid ASC
                LIMIT 1
                """,
                [
                    *kind_values,
                    JobStatus.QUEUED.value,
                    now_iso,
                    JobStatus.RUNNING.value,
                    now_iso,
                ],
            ).fetchone()
            if row is None:
                return None

            lease_token = f"lease_{uuid4().hex[:16]}"
            started_at = row["started_at"] or now_iso
            connection.execute(
                """
                UPDATE runtime_job
                SET status = ?, started_at = ?, completed_at = NULL,
                    error_code = NULL, error_message = NULL,
                    lease_owner = ?, lease_token = ?, lease_expires_at = ?,
                    last_heartbeat_at = ?, attempt_count = ?
                WHERE job_id = ?
                """,
                (
                    JobStatus.RUNNING.value,
                    started_at,
                    worker_id,
                    lease_token,
                    lease_expires_at,
                    now_iso,
                    int(row["attempt_count"] or 0) + 1,
                    row["job_id"],
                ),
            )
            claimed_row = connection.execute(
                """
                SELECT
                    job_id, user_id, device_session_id, kind, status, requested_at,
                    available_at, started_at, completed_at, error_code, error_message, resource_id,
                    attempt_count,
                    audit_surface, audit_conversation_id, details_json
                FROM runtime_job
                WHERE job_id = ?
                """,
                (row["job_id"],),
            ).fetchone()
        if claimed_row is None:
            return None
        return ClaimedRuntimeJob(
            lease_owner=worker_id,
            lease_token=lease_token,
            lease_expires_at=lease_expires_at,
            job=self._runtime_job_from_row(claimed_row),
        )

    def heartbeat_runtime_job(
        self,
        *,
        job_id: str,
        lease_token: str,
        lease_seconds: int,
    ) -> str | None:
        now = datetime.now(UTC)
        now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        lease_expires_at = (now + timedelta(seconds=lease_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._connect() as connection:
            result = connection.execute(
                """
                UPDATE runtime_job
                SET lease_expires_at = ?, last_heartbeat_at = ?
                WHERE job_id = ? AND lease_token = ? AND status = ?
                """,
                (
                    lease_expires_at,
                    now_iso,
                    job_id,
                    lease_token,
                    JobStatus.RUNNING.value,
                ),
            )
        if result.rowcount == 0:
            return None
        return lease_expires_at

    def complete_runtime_job(
        self,
        *,
        job_id: str,
        lease_token: str,
        status: JobStatus,
        error_code: str | None = None,
        error_message: str | None = None,
        details: dict[str, object] | None = None,
    ) -> RuntimeJobRecord:
        if status not in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}:
            raise ValueError("runtime job completion requires a terminal status")

        completed_at = _utc_now_iso()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    job_id, user_id, device_session_id, kind, status, requested_at,
                    available_at, started_at, completed_at, error_code, error_message, resource_id,
                    attempt_count,
                    audit_surface, audit_conversation_id, details_json
                FROM runtime_job
                WHERE job_id = ? AND lease_token = ?
                """,
                (job_id, lease_token),
            ).fetchone()
            if row is None:
                raise ValueError("runtime job lease is missing or expired")

            merged_details = json.loads(row["details_json"] or "{}")
            if details:
                merged_details.update(details)
            connection.execute(
                """
                UPDATE runtime_job
                SET status = ?, completed_at = ?, error_code = ?, error_message = ?,
                    details_json = ?, lease_owner = NULL, lease_token = NULL,
                    lease_expires_at = NULL, last_heartbeat_at = NULL
                WHERE job_id = ?
                """,
                (
                    status.value,
                    completed_at,
                    error_code,
                    error_message,
                    json.dumps(merged_details),
                    job_id,
                ),
            )
            completed_row = connection.execute(
                """
                SELECT
                    job_id, user_id, device_session_id, kind, status, requested_at,
                    available_at, started_at, completed_at, error_code, error_message, resource_id,
                    attempt_count,
                    audit_surface, audit_conversation_id, details_json
                FROM runtime_job
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        if completed_row is None:
            raise ValueError("runtime job row disappeared during completion")
        return self._runtime_job_from_row(completed_row)

    def purge_memory_delete_job(self, job: RuntimeJobRecord) -> dict[str, object]:
        memory_id = str(job.details.get("memory_id") or job.resource_id or "")
        if not memory_id:
            raise ValueError("memory_delete job is missing memory_id")

        purged_at = _utc_now_iso()
        with self._connect() as connection:
            checkpoint_rows = connection.execute(
                """
                SELECT device_session_id, selected_memory_ids_json
                FROM session_checkpoint
                WHERE user_id = ?
                """,
                (job.user_id,),
            ).fetchall()
            checkpoint_updates = 0
            for checkpoint_row in checkpoint_rows:
                selected_memory_ids = json.loads(checkpoint_row["selected_memory_ids_json"] or "[]")
                filtered_memory_ids = [selected_id for selected_id in selected_memory_ids if selected_id != memory_id]
                if filtered_memory_ids == selected_memory_ids:
                    continue
                connection.execute(
                    """
                    UPDATE session_checkpoint
                    SET selected_memory_ids_json = ?, updated_at = ?
                    WHERE user_id = ? AND device_session_id = ?
                    """,
                    (
                        json.dumps(filtered_memory_ids),
                        purged_at,
                        job.user_id,
                        checkpoint_row["device_session_id"],
                    ),
                )
                checkpoint_updates += 1
            delete_row = connection.execute(
                """
                SELECT delete_id
                FROM memory_delete_job
                WHERE delete_id = ? AND user_id = ?
                """,
                (job.job_id, job.user_id),
            ).fetchone()
            deleted_rows = connection.execute(
                "DELETE FROM memory_item WHERE id = ? AND user_id = ?",
                (memory_id, job.user_id),
            ).rowcount
            if delete_row is not None and deleted_rows == 0:
                connection.execute(
                    "DELETE FROM memory_delete_job WHERE delete_id = ? AND user_id = ?",
                    (job.job_id, job.user_id),
                )

        return {
            "memory_id": memory_id,
            "purged_at": purged_at,
            "checkpoint_updates": checkpoint_updates,
            "purge_result": "deleted" if deleted_rows else "already_missing",
        }

    def get_checkpoint(self, user_id: str, device_session_id: str) -> SessionCheckpoint | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT user_id, device_session_id, conversation_id, last_message_id,
                       draft_text, selected_memory_ids_json, route, surface, handoff_kind,
                       resume_token_ref, last_surface_at, updated_at, version
                FROM session_checkpoint
                WHERE user_id = ? AND device_session_id = ?
                """,
                (user_id, device_session_id),
            ).fetchone()
        if row is None:
            return None
        return self._checkpoint_from_row(row)

    def _write_checkpoint_record(
        self,
        connection: sqlite3.Connection,
        *,
        user_id: str,
        device_session_id: str,
        conversation_id: str,
        last_message_id: str | None,
        draft_text: str,
        selected_memory_ids: list[str],
        route: str,
        surface: Surface,
        handoff_kind: HandoffKind,
        resume_token_ref: str | None,
        last_surface_at: str | None,
        updated_at: str,
        version: int,
    ) -> SessionCheckpoint:
        stored_checkpoint = SessionCheckpoint(
            user_id=user_id,
            device_session_id=device_session_id,
            conversation_id=conversation_id,
            last_message_id=last_message_id,
            draft_text=draft_text,
            selected_memory_ids=self._filter_active_memory_ids(connection, user_id, selected_memory_ids),
            route=route,
            surface=surface,
            handoff_kind=handoff_kind,
            resume_token_ref=resume_token_ref,
            last_surface_at=last_surface_at or updated_at,
            updated_at=updated_at,
            version=version,
        )
        connection.execute(
            """
            INSERT INTO session_checkpoint (
                user_id, device_session_id, conversation_id, last_message_id,
                draft_text, selected_memory_ids_json, route, surface, handoff_kind,
                resume_token_ref, last_surface_at, updated_at, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, device_session_id) DO UPDATE SET
                conversation_id = excluded.conversation_id,
                last_message_id = excluded.last_message_id,
                draft_text = excluded.draft_text,
                selected_memory_ids_json = excluded.selected_memory_ids_json,
                route = excluded.route,
                surface = excluded.surface,
                handoff_kind = excluded.handoff_kind,
                resume_token_ref = excluded.resume_token_ref,
                last_surface_at = excluded.last_surface_at,
                updated_at = excluded.updated_at,
                version = excluded.version
            """,
            (
                stored_checkpoint.user_id,
                stored_checkpoint.device_session_id,
                stored_checkpoint.conversation_id,
                stored_checkpoint.last_message_id,
                stored_checkpoint.draft_text,
                json.dumps(stored_checkpoint.selected_memory_ids),
                stored_checkpoint.route,
                stored_checkpoint.surface.value,
                stored_checkpoint.handoff_kind.value,
                stored_checkpoint.resume_token_ref,
                stored_checkpoint.last_surface_at,
                stored_checkpoint.updated_at,
                stored_checkpoint.version,
            ),
        )
        return stored_checkpoint

    def upsert_checkpoint(
        self,
        user_id: str,
        device_session_id: str,
        checkpoint: CheckpointUpsertRequest,
    ) -> SessionCheckpoint:
        if checkpoint.user_id != user_id or checkpoint.device_session_id != device_session_id:
            raise ValueError("checkpoint ownership must match the authenticated session")

        with self._connect() as connection:
            existing_row = connection.execute(
                """
                SELECT user_id, device_session_id, conversation_id, last_message_id,
                       draft_text, selected_memory_ids_json, route, surface, handoff_kind,
                       resume_token_ref, last_surface_at, updated_at, version
                FROM session_checkpoint
                WHERE user_id = ? AND device_session_id = ?
                """,
                (user_id, device_session_id),
            ).fetchone()
            existing_checkpoint = self._checkpoint_from_row(existing_row) if existing_row is not None else None
            base_version = checkpoint.base_version if checkpoint.base_version is not None else checkpoint.version - 1
            if existing_checkpoint is not None and not checkpoint.force and base_version != existing_checkpoint.version:
                raise CheckpointConflictError(
                    CheckpointConflictResponse(
                        message="A newer checkpoint is already stored for this device.",
                        server_checkpoint=existing_checkpoint,
                        client_checkpoint=SessionCheckpoint(
                            user_id=checkpoint.user_id,
                            device_session_id=checkpoint.device_session_id,
                            conversation_id=checkpoint.conversation_id,
                            last_message_id=checkpoint.last_message_id,
                            draft_text=checkpoint.draft_text,
                            selected_memory_ids=checkpoint.selected_memory_ids,
                            route=checkpoint.route,
                            surface=checkpoint.surface,
                            handoff_kind=checkpoint.handoff_kind,
                            resume_token_ref=checkpoint.resume_token_ref,
                            last_surface_at=checkpoint.last_surface_at,
                            updated_at=checkpoint.updated_at,
                            version=checkpoint.version,
                        ),
                    )
                )

            next_version = 1
            if existing_checkpoint is not None:
                next_version = max(existing_checkpoint.version + 1, checkpoint.version)
            else:
                next_version = max(1, checkpoint.version)
            return self._write_checkpoint_record(
                connection,
                user_id=checkpoint.user_id,
                device_session_id=checkpoint.device_session_id,
                conversation_id=checkpoint.conversation_id,
                last_message_id=checkpoint.last_message_id,
                draft_text=checkpoint.draft_text,
                selected_memory_ids=checkpoint.selected_memory_ids,
                route=checkpoint.route,
                surface=checkpoint.surface,
                handoff_kind=checkpoint.handoff_kind,
                resume_token_ref=checkpoint.resume_token_ref,
                last_surface_at=checkpoint.last_surface_at,
                updated_at=checkpoint.updated_at,
                version=next_version,
            )

    def get_evidence_ref(self, app_version: str) -> EvidenceRef | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT app_version, bundle_id, summary_ref, overall_status, generated_at
                FROM evidence_ref
                WHERE app_version = ?
                """,
                (app_version,),
            ).fetchone()
        if row is None:
            return None
        return EvidenceRef(
            app_version=row["app_version"],
            bundle_id=row["bundle_id"],
            summary_ref=row["summary_ref"],
            overall_status=row["overall_status"],
            generated_at=row["generated_at"],
        )

    def upsert_evidence_ref(self, evidence_ref: EvidenceRef) -> EvidenceRef:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO evidence_ref (app_version, bundle_id, summary_ref, overall_status, generated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(app_version) DO UPDATE SET
                    bundle_id = excluded.bundle_id,
                    summary_ref = excluded.summary_ref,
                    overall_status = excluded.overall_status,
                    generated_at = excluded.generated_at
                """,
                (
                    evidence_ref.app_version,
                    evidence_ref.bundle_id,
                    evidence_ref.summary_ref,
                    evidence_ref.overall_status.value,
                    evidence_ref.generated_at,
                ),
            )
        return evidence_ref

    def _insert_memory_revision(self, connection: sqlite3.Connection, *, memory_id: str, action: str, diff: dict[str, Any]) -> None:
        next_version_row = connection.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 AS next_version FROM memory_revision WHERE memory_id = ?",
            (memory_id,),
        ).fetchone()
        next_version = int(next_version_row["next_version"])
        connection.execute(
            """
            INSERT INTO memory_revision (memory_id, version, action, diff_json, actor, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (memory_id, next_version, action, json.dumps(diff), "user", _utc_now_iso()),
        )

    def _replace_memory_sources(
        self,
        connection: sqlite3.Connection,
        memory_id: str,
        sources: list[MemorySource],
    ) -> None:
        connection.execute("DELETE FROM memory_source WHERE memory_id = ?", (memory_id,))
        for source in sources:
            connection.execute(
                """
                INSERT INTO memory_source (memory_id, conversation_id, message_id, note, captured_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    source.memory_id,
                    source.conversation_id,
                    source.message_id,
                    source.note,
                    source.captured_at,
                ),
            )

    def _list_memory_sources(
        self,
        connection: sqlite3.Connection,
        memory_ids: list[str],
    ) -> dict[str, list[MemorySource]]:
        if not memory_ids:
            return {}
        placeholders = ", ".join("?" for _ in memory_ids)
        rows = connection.execute(
            f"""
            SELECT memory_id, conversation_id, message_id, note, captured_at
            FROM memory_source
            WHERE memory_id IN ({placeholders})
            ORDER BY captured_at ASC
            """,
            memory_ids,
        ).fetchall()
        sources_by_memory_id: dict[str, list[MemorySource]] = {memory_id: [] for memory_id in memory_ids}
        for row in rows:
            sources_by_memory_id.setdefault(row["memory_id"], []).append(
                MemorySource(
                    memory_id=row["memory_id"],
                    conversation_id=row["conversation_id"],
                    message_id=row["message_id"],
                    note=row["note"],
                    captured_at=row["captured_at"],
                )
            )
        return sources_by_memory_id

    def _list_memory_revisions(
        self,
        connection: sqlite3.Connection,
        memory_ids: list[str],
    ) -> dict[str, list[MemoryRevision]]:
        if not memory_ids:
            return {}
        placeholders = ", ".join("?" for _ in memory_ids)
        rows = connection.execute(
            f"""
            SELECT memory_id, version, action, diff_json, actor, created_at
            FROM memory_revision
            WHERE memory_id IN ({placeholders})
            ORDER BY version ASC
            """,
            memory_ids,
        ).fetchall()
        revisions_by_memory_id: dict[str, list[MemoryRevision]] = {memory_id: [] for memory_id in memory_ids}
        for row in rows:
            revisions_by_memory_id.setdefault(row["memory_id"], []).append(
                MemoryRevision(
                    memory_id=row["memory_id"],
                    version=row["version"],
                    action=row["action"],
                    diff=json.loads(row["diff_json"] or "{}"),
                    actor=row["actor"],
                    created_at=row["created_at"],
                )
            )
        return revisions_by_memory_id

    @staticmethod
    def _filter_active_memory_ids(
        connection: sqlite3.Connection,
        user_id: str,
        selected_memory_ids: list[str],
    ) -> list[str]:
        deduped_memory_ids = list(dict.fromkeys(selected_memory_ids))
        if not deduped_memory_ids:
            return []
        placeholders = ", ".join("?" for _ in deduped_memory_ids)
        rows = connection.execute(
            f"""
            SELECT id
            FROM memory_item
            WHERE user_id = ? AND status = ? AND id IN ({placeholders})
            """,
            [user_id, MemoryStatus.ACTIVE.value, *deduped_memory_ids],
        ).fetchall()
        active_ids = {row["id"] for row in rows}
        return [memory_id for memory_id in deduped_memory_ids if memory_id in active_ids]

    def _get_telegram_link_row(
        self,
        connection: sqlite3.Connection,
        user_id: str,
    ) -> sqlite3.Row | None:
        row = connection.execute(
            """
            SELECT
                user_id, status, link_code, link_token_hash, expires_at, telegram_user_id,
                telegram_username, telegram_display_name, telegram_chat_id, linked_at,
                last_event_at, last_error_code, last_error_message, last_resume_token_ref
            FROM telegram_link_state
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        if row is None:
            return None

        now_iso = _utc_now_iso()
        if (
            row["status"] == TelegramLinkStatus.PENDING.value
            and row["expires_at"] is not None
            and row["expires_at"] < now_iso
        ):
            self._mark_telegram_link_error(
                connection,
                user_id=user_id,
                error_code="link_expired",
                error_message="Telegram linking code expired.",
            )
            row = connection.execute(
                """
                SELECT
                    user_id, status, link_code, link_token_hash, expires_at, telegram_user_id,
                    telegram_username, telegram_display_name, telegram_chat_id, linked_at,
                    last_event_at, last_error_code, last_error_message, last_resume_token_ref
                FROM telegram_link_state
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        return row

    def _get_telegram_link_row_by_token_hash(
        self,
        connection: sqlite3.Connection,
        link_token_hash: str,
    ) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT
                user_id, status, link_code, link_token_hash, expires_at, telegram_user_id,
                telegram_username, telegram_display_name, telegram_chat_id, linked_at,
                last_event_at, last_error_code, last_error_message, last_resume_token_ref
            FROM telegram_link_state
            WHERE link_token_hash = ?
            """,
            (link_token_hash,),
        ).fetchone()

    def _get_telegram_link_row_by_telegram_user_id(
        self,
        connection: sqlite3.Connection,
        telegram_user_id: str,
    ) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT
                user_id, status, link_code, link_token_hash, expires_at, telegram_user_id,
                telegram_username, telegram_display_name, telegram_chat_id, linked_at,
                last_event_at, last_error_code, last_error_message, last_resume_token_ref
            FROM telegram_link_state
            WHERE telegram_user_id = ?
            """,
            (telegram_user_id,),
        ).fetchone()

    def _get_linked_telegram_row(
        self,
        connection: sqlite3.Connection,
        *,
        telegram_user_id: str,
        telegram_chat_id: str,
    ) -> sqlite3.Row:
        link_row = self._get_telegram_link_row_by_telegram_user_id(connection, telegram_user_id)
        if link_row is None or link_row["status"] != TelegramLinkStatus.LINKED.value:
            raise TelegramLinkError(
                "telegram_not_linked",
                "telegram companion account must be linked before using this action",
            )
        if link_row["telegram_chat_id"] is not None and link_row["telegram_chat_id"] != telegram_chat_id:
            raise TelegramLinkError(
                "telegram_chat_mismatch",
                "telegram chat does not match the linked companion account",
            )
        return link_row

    def _mark_telegram_link_error(
        self,
        connection: sqlite3.Connection,
        *,
        user_id: str,
        error_code: str,
        error_message: str,
    ) -> None:
        now_iso = _utc_now_iso()
        connection.execute(
            """
            UPDATE telegram_link_state
            SET status = ?, link_code = NULL, link_token_hash = NULL, expires_at = NULL,
                last_event_at = ?, last_error_code = ?, last_error_message = ?
            WHERE user_id = ?
            """,
            (
                TelegramLinkStatus.ERROR.value,
                now_iso,
                error_code,
                error_message,
                user_id,
            ),
        )

    def _complete_telegram_link_row(
        self,
        connection: sqlite3.Connection,
        *,
        user_id: str,
        telegram_user_id: str,
        telegram_chat_id: str,
        telegram_username: str | None,
        telegram_display_name: str | None,
        linked_at: str,
        last_resume_token_ref: str | None,
    ) -> sqlite3.Row:
        try:
            connection.execute(
                """
                UPDATE telegram_link_state
                SET status = ?, link_code = NULL, link_token_hash = NULL, expires_at = NULL,
                    telegram_user_id = ?, telegram_username = ?, telegram_display_name = ?, telegram_chat_id = ?,
                    linked_at = ?, last_event_at = ?, last_error_code = NULL, last_error_message = NULL,
                    last_resume_token_ref = ?
                WHERE user_id = ?
                """,
                (
                    TelegramLinkStatus.LINKED.value,
                    telegram_user_id,
                    telegram_username,
                    telegram_display_name,
                    telegram_chat_id,
                    linked_at,
                    linked_at,
                    last_resume_token_ref,
                    user_id,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise TelegramLinkError(
                "telegram_account_conflict",
                "telegram account already linked to another user",
            ) from exc

        stored_row = self._get_telegram_link_row(connection, user_id)
        if stored_row is None:
            raise TelegramLinkError("link_state_missing", "failed to resolve linked telegram state")
        return stored_row

    def _record_telegram_handoff(
        self,
        connection: sqlite3.Connection,
        *,
        user_id: str,
        handoff_kind: HandoffKind,
        occurred_at: str,
        draft_text: str | None,
        telegram_chat_id: str,
        telegram_username: str | None,
        telegram_display_name: str | None,
    ) -> SessionCheckpoint:
        target_device_session_id = self._select_resume_device_session_id(connection, user_id)
        if target_device_session_id is None:
            raise TelegramLinkError(
                "resume_target_missing",
                "no active assistant device session is available for Telegram continuity",
            )

        existing_row = connection.execute(
            """
            SELECT user_id, device_session_id, conversation_id, last_message_id,
                   draft_text, selected_memory_ids_json, route, surface, handoff_kind,
                   resume_token_ref, last_surface_at, updated_at, version
            FROM session_checkpoint
            WHERE user_id = ? AND device_session_id = ?
            """,
            (user_id, target_device_session_id),
        ).fetchone()
        existing_checkpoint = self._checkpoint_from_row(existing_row) if existing_row is not None else None
        conversation_id = (
            existing_checkpoint.conversation_id if existing_checkpoint is not None else f"conv_{uuid4().hex[:12]}"
        )
        route = existing_checkpoint.route if existing_checkpoint is not None else f"/chat/{conversation_id}"
        next_version = existing_checkpoint.version + 1 if existing_checkpoint is not None else 1
        resume_token_ref = f"resume_tg_{secrets.token_hex(10)}"

        stored_checkpoint = self._write_checkpoint_record(
            connection,
            user_id=user_id,
            device_session_id=target_device_session_id,
            conversation_id=conversation_id,
            last_message_id=existing_checkpoint.last_message_id if existing_checkpoint is not None else None,
            draft_text=existing_checkpoint.draft_text if draft_text is None and existing_checkpoint is not None else draft_text or "",
            selected_memory_ids=existing_checkpoint.selected_memory_ids if existing_checkpoint is not None else [],
            route=route,
            surface=Surface.TELEGRAM,
            handoff_kind=handoff_kind,
            resume_token_ref=resume_token_ref,
            last_surface_at=occurred_at,
            updated_at=occurred_at,
            version=next_version,
        )
        connection.execute(
            """
            UPDATE telegram_link_state
            SET telegram_username = COALESCE(?, telegram_username),
                telegram_display_name = COALESCE(?, telegram_display_name),
                telegram_chat_id = COALESCE(?, telegram_chat_id),
                last_event_at = ?,
                last_error_code = NULL,
                last_error_message = NULL,
                last_resume_token_ref = ?
            WHERE user_id = ?
            """,
            (
                telegram_username,
                telegram_display_name,
                telegram_chat_id,
                occurred_at,
                resume_token_ref,
                user_id,
            ),
        )
        return stored_checkpoint

    @staticmethod
    def _select_resume_device_session_id(
        connection: sqlite3.Connection,
        user_id: str,
    ) -> str | None:
        row = connection.execute(
            """
            SELECT id
            FROM device_session
            WHERE user_id = ?
              AND expires_at >= ?
              AND auth_state IN (?, ?)
            ORDER BY
                CASE auth_state
                    WHEN ? THEN 0
                    WHEN ? THEN 1
                    ELSE 2
                END,
                last_seen_at DESC,
                connected_at DESC,
                created_at DESC
            LIMIT 1
            """,
            (
                user_id,
                _utc_now_iso(),
                AuthState.ACTIVE.value,
                AuthState.PENDING_CONSENT.value,
                AuthState.ACTIVE.value,
                AuthState.PENDING_CONSENT.value,
            ),
        ).fetchone()
        return row["id"] if row is not None else None

    def _record_runtime_job(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: str,
        user_id: str,
        device_session_id: str,
        kind: JobKind,
        status: JobStatus,
        requested_at: str,
        available_at: str | None,
        started_at: str | None,
        completed_at: str | None,
        error_code: str | None,
        error_message: str | None,
        resource_id: str | None,
        details: dict[str, Any],
    ) -> None:
        surface = self._surface_for_device_session(connection, device_session_id)
        connection.execute(
            """
            INSERT INTO runtime_job (
                job_id, user_id, device_session_id, kind, status, requested_at,
                available_at, started_at, completed_at, error_code, error_message, resource_id,
                lease_owner, lease_token, lease_expires_at, last_heartbeat_at, attempt_count,
                audit_surface, audit_conversation_id, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                user_id = excluded.user_id,
                device_session_id = excluded.device_session_id,
                kind = excluded.kind,
                status = excluded.status,
                requested_at = excluded.requested_at,
                available_at = excluded.available_at,
                started_at = excluded.started_at,
                completed_at = excluded.completed_at,
                error_code = excluded.error_code,
                error_message = excluded.error_message,
                resource_id = excluded.resource_id,
                lease_owner = NULL,
                lease_token = NULL,
                lease_expires_at = NULL,
                last_heartbeat_at = NULL,
                attempt_count = runtime_job.attempt_count,
                audit_surface = excluded.audit_surface,
                audit_conversation_id = excluded.audit_conversation_id,
                details_json = excluded.details_json
            """,
            (
                job_id,
                user_id,
                device_session_id,
                kind.value,
                status.value,
                requested_at,
                available_at,
                started_at,
                completed_at,
                error_code,
                error_message,
                resource_id,
                None,
                None,
                None,
                None,
                0,
                surface.value,
                self._conversation_for_device_session(connection, user_id, device_session_id),
                json.dumps(details),
            ),
        )

    def _memory_broker_provider(self) -> MemoryBrokerProvider:
        provider = getattr(self.memory_broker, "provider", MemoryBrokerProvider.KG_MCP)
        if isinstance(provider, MemoryBrokerProvider):
            return provider
        try:
            return MemoryBrokerProvider(str(provider))
        except ValueError:
            return MemoryBrokerProvider.KG_MCP

    @staticmethod
    def _load_memory_broker_project_ids(raw_value: str | None) -> list[str]:
        if not raw_value:
            return []
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []

        project_ids: list[str] = []
        for item in parsed:
            if not isinstance(item, str):
                continue
            normalized = item.strip()
            if not normalized or normalized in project_ids:
                continue
            project_ids.append(normalized)
        return project_ids

    @staticmethod
    def _filter_memory_broker_results(
        results: list[MemoryBrokerResult],
        *,
        workspace_id: str,
        project_id: str | None,
        allowed_project_ids: list[str],
        limit: int,
    ) -> list[MemoryBrokerResult]:
        filtered_results: list[MemoryBrokerResult] = []
        for result in results:
            if result.workspace_id != workspace_id:
                continue
            if project_id is not None and result.project_id != project_id:
                continue
            if (
                project_id is None
                and allowed_project_ids
                and result.project_id is not None
                and result.project_id not in allowed_project_ids
            ):
                continue
            filtered_results.append(result)
            if len(filtered_results) >= limit:
                break
        return filtered_results

    def _record_memory_broker_audit(
        self,
        connection: sqlite3.Connection,
        *,
        user_id: str,
        workspace_id: str,
        project_id: str | None,
        action: MemoryBrokerAuditAction,
        status: MemoryBrokerAuditStatus,
        source_surface: Surface,
        conversation_id: str | None,
        query: str | None,
        result_count: int,
        details: dict[str, object],
    ) -> MemoryBrokerAuditRecord:
        created_at = _utc_now_iso()
        audit_id = f"broker_audit_{uuid4().hex[:12]}"
        connection.execute(
            """
            INSERT INTO memory_broker_audit (
                audit_id, user_id, workspace_id, project_id, action, status, source_surface,
                conversation_id, query_text, result_count, created_at, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                user_id,
                workspace_id,
                project_id,
                action.value,
                status.value,
                source_surface.value,
                conversation_id,
                query,
                result_count,
                created_at,
                json.dumps(details),
            ),
        )
        return MemoryBrokerAuditRecord(
            audit_id=audit_id,
            action=action,
            status=status,
            workspace_id=workspace_id,
            project_id=project_id,
            source_surface=source_surface,
            conversation_id=conversation_id,
            query=query,
            result_count=result_count,
            created_at=created_at,
        )

    def _memory_broker_workspace_state_from_row(
        self,
        row: sqlite3.Row | None,
        *,
        workspace_id: str | None = None,
    ) -> MemoryBrokerWorkspaceState:
        provider = self._memory_broker_provider()
        provider_status = self.memory_broker.provider_status()
        if row is None:
            if workspace_id is None:
                raise ValueError("workspace_id is required when broker state is missing")
            return MemoryBrokerWorkspaceState(
                workspace_id=workspace_id,
                status=MemoryBrokerOptInStatus.DISABLED,
                provider=provider,
                provider_status=provider_status,
                scope=MemoryBrokerScope(workspace_id=workspace_id, project_ids=[]),
                consent=MemoryBrokerConsent(enabled=False),
                last_brokered_at=None,
                last_audit_id=None,
                last_audit_at=None,
                last_error_code=None,
                last_error_message=None,
            )

        row_provider = row["provider"] if row["provider"] else provider.value
        try:
            resolved_provider = MemoryBrokerProvider(row_provider)
        except ValueError:
            resolved_provider = provider

        resolved_workspace_id = row["workspace_id"] if row["workspace_id"] else workspace_id
        if resolved_workspace_id is None:
            raise ValueError("workspace_id is required for broker state conversion")

        return MemoryBrokerWorkspaceState(
            workspace_id=resolved_workspace_id,
            status=row["status"],
            provider=resolved_provider,
            provider_status=provider_status,
            scope=MemoryBrokerScope(
                workspace_id=resolved_workspace_id,
                project_ids=self._load_memory_broker_project_ids(row["project_ids_json"]),
            ),
            consent=MemoryBrokerConsent(
                enabled=row["status"] == MemoryBrokerOptInStatus.ENABLED.value,
                source_surface=self._surface_from_value(row["source_surface"])
                if row["source_surface"] is not None
                else None,
                granted_at=row["granted_at"],
                revoked_at=row["revoked_at"],
                updated_at=row["updated_at"],
            ),
            last_brokered_at=row["last_brokered_at"],
            last_audit_id=row["last_audit_id"],
            last_audit_at=row["last_audit_at"],
            last_error_code=row["last_error_code"],
            last_error_message=row["last_error_message"],
        )

    def _artifact_reference(self, artifact_path) -> str:
        try:
            return str(artifact_path.relative_to(self.settings.repo_root))
        except ValueError:
            return str(artifact_path)

    def _build_telegram_bot_deep_link(self, link_token: str) -> str | None:
        base_url = self.settings.telegram_bot_deep_link_base_url
        if not base_url and self.settings.telegram_bot_username:
            base_url = f"https://t.me/{self.settings.telegram_bot_username.lstrip('@')}?start="
        if not base_url:
            return None
        encoded_token = quote(link_token, safe="")
        if "{token}" in base_url:
            return base_url.replace("{token}", encoded_token)
        return f"{base_url}{encoded_token}"

    @staticmethod
    def _surface_from_value(raw_value: str | None) -> Surface:
        if raw_value is None:
            return Surface.WEB
        try:
            return Surface(raw_value)
        except ValueError:
            return Surface.WEB

    def _surface_for_device_session(
        self,
        connection: sqlite3.Connection,
        device_session_id: str,
    ) -> Surface:
        row = connection.execute(
            "SELECT platform FROM device_session WHERE id = ?",
            (device_session_id,),
        ).fetchone()
        platform = row["platform"] if row is not None else None
        return self._surface_from_value(platform)

    @staticmethod
    def _conversation_for_device_session(
        connection: sqlite3.Connection,
        user_id: str,
        device_session_id: str,
    ) -> str | None:
        row = connection.execute(
            """
            SELECT conversation_id
            FROM session_checkpoint
            WHERE user_id = ? AND device_session_id = ?
            """,
            (user_id, device_session_id),
        ).fetchone()
        return row["conversation_id"] if row is not None else None

    @staticmethod
    def _auth_session_from_row(row: sqlite3.Row) -> AuthSession:
        return AuthSession(
            user_id=row["user_id"],
            device_session_id=row["device_session_id"],
            auth_state=row["auth_state"],
            provider=ProviderMetadata(
                provider_subject=row["provider_subject"],
                scopes=json.loads(row["scopes_json"] or "[]"),
                connected_at=row["connected_at"],
            ),
            session=SessionMetadata(
                session_id=row["session_id"],
                expires_at=row["expires_at"],
                last_seen_at=row["last_seen_at"],
            ),
            memory_controls=MemoryControls(
                memory_export_supported=True,
                memory_delete_supported=True,
            ),
        )

    @staticmethod
    def _memory_record_from_row(row: sqlite3.Row, sources: list[MemorySource]) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            user_id=row["user_id"],
            kind=row["kind"],
            content=row["content"],
            status=row["status"],
            importance=row["importance"],
            source_type=row["source_type"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_used_at=row["last_used_at"],
            sources=sources,
        )

    @staticmethod
    def _telegram_link_state_from_row(
        row: sqlite3.Row,
        *,
        bot_deep_link: str | None = None,
    ) -> TelegramLinkState:
        status = TelegramLinkStatus(row["status"])
        return TelegramLinkState(
            status=status,
            is_linked=status == TelegramLinkStatus.LINKED,
            link_code=row["link_code"],
            bot_deep_link=bot_deep_link,
            expires_at=row["expires_at"],
            telegram_display_name=row["telegram_display_name"],
            telegram_username=row["telegram_username"],
            linked_at=row["linked_at"],
            last_event_at=row["last_event_at"],
            last_error_code=row["last_error_code"],
            last_error_message=row["last_error_message"],
            last_resume_token_ref=row["last_resume_token_ref"],
        )

    @staticmethod
    def _runtime_job_from_row(row: sqlite3.Row) -> RuntimeJobRecord:
        row_keys = set(row.keys())
        return RuntimeJobRecord(
            job_id=row["job_id"],
            user_id=row["user_id"],
            kind=row["kind"],
            status=row["status"],
            requested_at=row["requested_at"],
            available_at=row["available_at"] if "available_at" in row_keys else None,
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            error_code=row["error_code"],
            error_message=row["error_message"],
            resource_id=row["resource_id"],
            attempt_count=int(row["attempt_count"] or 0) if "attempt_count" in row_keys else 0,
            audit=RuntimeJobAudit(
                device_session_id=row["device_session_id"],
                surface=row["audit_surface"],
                conversation_id=row["audit_conversation_id"],
            ),
            details=json.loads(row["details_json"] or "{}"),
        )

    @staticmethod
    def _reminder_record_from_row(row: sqlite3.Row) -> ReminderRecord:
        row_keys = set(row.keys())
        return ReminderRecord(
            reminder_id=row["reminder_id"],
            job_id=row["job_id"],
            user_id=row["user_id"],
            device_session_id=row["device_session_id"],
            status=row["status"],
            channel=row["channel"],
            scheduled_for=row["scheduled_for"],
            payload=json.loads(row["payload_json"] or "{}"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            delivered_at=row["delivered_at"],
            canceled_at=row["canceled_at"],
            last_error_code=row["last_error_code"],
            last_error_message=row["last_error_message"],
            follow_up_policy=(
                _reminder_follow_up_policy_from_json(row["follow_up_policy_json"])
                if "follow_up_policy_json" in row_keys
                else ReminderFollowUpPolicy()
            ),
            follow_up_state=(
                _reminder_follow_up_state_from_json(row["follow_up_state_json"])
                if "follow_up_state_json" in row_keys
                else ReminderFollowUpState()
            ),
        )

    @staticmethod
    def _checkpoint_from_row(row: sqlite3.Row) -> SessionCheckpoint:
        row_keys = set(row.keys())
        return SessionCheckpoint(
            user_id=row["user_id"],
            device_session_id=row["device_session_id"],
            conversation_id=row["conversation_id"],
            last_message_id=row["last_message_id"],
            draft_text=row["draft_text"],
            selected_memory_ids=json.loads(row["selected_memory_ids_json"] or "[]"),
            route=row["route"],
            surface=row["surface"] if "surface" in row_keys else Surface.WEB.value,
            handoff_kind=row["handoff_kind"] if "handoff_kind" in row_keys else HandoffKind.NONE.value,
            resume_token_ref=row["resume_token_ref"] if "resume_token_ref" in row_keys else None,
            last_surface_at=row["last_surface_at"] if "last_surface_at" in row_keys else None,
            updated_at=row["updated_at"],
            version=row["version"],
        )
