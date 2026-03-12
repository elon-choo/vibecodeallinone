"""Pydantic models for the assistant-api bootstrap runtime."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _normalize_utc_timestamp(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include a timezone offset")
    return parsed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_string_list(values: list[str], *, field_name: str) -> list[str]:
    normalized_values: list[str] = []
    for raw_value in values:
        normalized = raw_value.strip()
        if not normalized:
            raise ValueError(f"{field_name} entries must be non-empty")
        if normalized not in normalized_values:
            normalized_values.append(normalized)
    return normalized_values


class Platform(StrEnum):
    WEB = "web"
    PWA = "pwa"
    IOS_WEBVIEW = "ios_webview"
    ANDROID_WEBVIEW = "android_webview"


class Surface(StrEnum):
    WEB = "web"
    PWA = "pwa"
    IOS_WEBVIEW = "ios_webview"
    ANDROID_WEBVIEW = "android_webview"
    TELEGRAM = "telegram"


class AuthState(StrEnum):
    PENDING_CONSENT = "pending_consent"
    ACTIVE = "active"
    REAUTH_REQUIRED = "reauth_required"


class MemoryKind(StrEnum):
    PROFILE = "profile"
    PREFERENCE = "preference"
    FACT = "fact"
    INSTRUCTION = "instruction"
    TASK = "task"
    SUMMARY = "summary"
    OTHER = "other"


class MemoryStatus(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MemorySourceType(StrEnum):
    CONVERSATION = "conversation"
    MANUAL_INPUT = "manual_input"
    IMPORT = "import"
    SYSTEM_CAPTURE = "system_capture"


class MemoryExportFormat(StrEnum):
    JSON = "json"


class MemoryExportStatus(StrEnum):
    READY = "ready"


class MemoryDeleteStatus(StrEnum):
    PENDING_PURGE = "pending_purge"


class MemoryBrokerProvider(StrEnum):
    KG_MCP = "kg_mcp"


class MemoryBrokerOptInStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class MemoryBrokerProviderStatus(StrEnum):
    READY = "ready"
    DISABLED = "disabled"
    NOT_CONFIGURED = "not_configured"


class MemoryBrokerAuditAction(StrEnum):
    OPT_IN_UPDATED = "opt_in_updated"
    READ = "read"


class MemoryBrokerAuditStatus(StrEnum):
    SUCCEEDED = "succeeded"
    UNAVAILABLE = "unavailable"


class MemoryBrokerResultKind(StrEnum):
    DOCUMENT = "document"
    SUMMARY = "summary"
    CODE = "code"
    OTHER = "other"


class TelegramLinkStatus(StrEnum):
    NOT_LINKED = "not_linked"
    PENDING = "pending"
    LINKED = "linked"
    ERROR = "error"


class HandoffKind(StrEnum):
    NONE = "none"
    RESUME_LINK = "resume_link"
    QUICK_CAPTURE = "quick_capture"
    REMINDER = "reminder"
    APPROVAL = "approval"


class JobKind(StrEnum):
    MEMORY_EXPORT = "memory_export"
    MEMORY_DELETE = "memory_delete"
    REMINDER_DELIVERY = "reminder_delivery"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class ReminderStatus(StrEnum):
    SCHEDULED = "scheduled"
    DELIVERED = "delivered"
    CANCELED = "canceled"
    FAILED = "failed"


class ReminderFollowUpFailureAction(StrEnum):
    NONE = "none"
    RETRY = "retry"


class ReminderFollowUpStatus(StrEnum):
    NONE = "none"
    RETRY_SCHEDULED = "retry_scheduled"
    SNOOZED = "snoozed"
    RESCHEDULED = "rescheduled"
    DEAD_LETTER = "dead_letter"


class StageStatus(StrEnum):
    NOT_RUN = "not_run"
    RUNNING = "running"
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    BLOCKED = "blocked"
    INVALID = "invalid"
    STALE = "stale"


class OpenAiStartRequest(StrictModel):
    redirect_uri: str
    device_label: str = Field(min_length=1)
    platform: Platform


class OpenAiStartResponse(StrictModel):
    authorization_url: str
    state: str = Field(min_length=8)
    provider: str = "openai"


class ProviderMetadata(StrictModel):
    provider: str = "openai"
    provider_subject: str = Field(min_length=1)
    scopes: list[str]
    connected_at: str


class SessionMetadata(StrictModel):
    session_id: str = Field(min_length=1)
    expires_at: str
    last_seen_at: str


class MemoryControls(StrictModel):
    memory_export_supported: bool
    memory_delete_supported: bool


class AuthSession(StrictModel):
    user_id: str = Field(min_length=1)
    device_session_id: str = Field(min_length=1)
    auth_state: AuthState
    provider: ProviderMetadata
    session: SessionMetadata
    memory_controls: MemoryControls


class MemoryItem(StrictModel):
    id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    kind: MemoryKind
    content: str = Field(min_length=1)
    status: MemoryStatus
    importance: int = Field(ge=0, le=100)
    source_type: MemorySourceType
    created_at: str
    updated_at: str
    last_used_at: str | None = None


class MemorySource(StrictModel):
    memory_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    message_id: str | None = None
    note: str | None = None
    captured_at: str


class MemoryRevision(StrictModel):
    memory_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    action: str = Field(min_length=1)
    diff: dict[str, object] = Field(default_factory=dict)
    actor: str = Field(min_length=1)
    created_at: str


class MemoryRecord(MemoryItem):
    sources: list[MemorySource] = Field(default_factory=list)


class MemoryCreateRequest(MemoryItem):
    sources: list[MemorySource] = Field(default_factory=list)


class MemoryItemsResponse(StrictModel):
    items: list[MemoryRecord]


class MemoryItemPatchRequest(StrictModel):
    content: str | None = None
    status: MemoryStatus | None = None
    importance: int | None = Field(default=None, ge=0, le=100)


class MemoryExportRecord(StrictModel):
    item: MemoryRecord
    revisions: list[MemoryRevision] = Field(default_factory=list)


class MemoryExportResponse(StrictModel):
    export_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    status: MemoryExportStatus
    format: MemoryExportFormat
    requested_at: str
    expires_at: str
    suggested_filename: str = Field(min_length=1)
    item_count: int = Field(ge=0)
    items: list[MemoryExportRecord] = Field(default_factory=list)


class MemoryDeleteReceipt(StrictModel):
    delete_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    memory_id: str = Field(min_length=1)
    status: MemoryStatus
    purge_status: MemoryDeleteStatus
    requested_at: str
    purge_after: str


class MemoryBrokerScope(StrictModel):
    workspace_id: str = Field(min_length=1)
    project_ids: list[str] = Field(default_factory=list)

    @field_validator("project_ids")
    @classmethod
    def validate_project_ids(cls, value: list[str]) -> list[str]:
        return _normalize_string_list(value, field_name="project_ids")


class MemoryBrokerConsent(StrictModel):
    opt_in_required: bool = True
    enabled: bool
    source_surface: Surface | None = None
    granted_at: str | None = None
    revoked_at: str | None = None
    updated_at: str | None = None


class MemoryBrokerWorkspaceState(StrictModel):
    workspace_id: str = Field(min_length=1)
    status: MemoryBrokerOptInStatus
    provider: MemoryBrokerProvider = MemoryBrokerProvider.KG_MCP
    provider_status: MemoryBrokerProviderStatus
    scope: MemoryBrokerScope
    consent: MemoryBrokerConsent
    last_brokered_at: str | None = None
    last_audit_id: str | None = None
    last_audit_at: str | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None


class MemoryBrokerWorkspaceUpsertRequest(StrictModel):
    enabled: bool
    project_ids: list[str] = Field(default_factory=list)
    source_surface: Surface = Surface.WEB

    @field_validator("project_ids")
    @classmethod
    def validate_project_ids(cls, value: list[str]) -> list[str]:
        return _normalize_string_list(value, field_name="project_ids")


class MemoryBrokerWorkspaceListResponse(StrictModel):
    items: list[MemoryBrokerWorkspaceState] = Field(default_factory=list)


class MemoryBrokerResult(StrictModel):
    entry_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    project_id: str | None = None
    kind: MemoryBrokerResultKind
    title: str | None = None
    content: str = Field(min_length=1)
    source_ref: str | None = None
    score: float | None = Field(default=None, ge=0, le=1)


class MemoryBrokerAuditRecord(StrictModel):
    audit_id: str = Field(min_length=1)
    action: MemoryBrokerAuditAction
    status: MemoryBrokerAuditStatus
    workspace_id: str = Field(min_length=1)
    project_id: str | None = None
    source_surface: Surface
    conversation_id: str | None = None
    query: str | None = None
    result_count: int = Field(ge=0)
    created_at: str


class MemoryBrokerQueryRequest(StrictModel):
    query: str = Field(min_length=1)
    project_id: str | None = None
    limit: int = Field(default=5, ge=1, le=20)
    source_surface: Surface = Surface.WEB

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query is required")
        return normalized

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("project_id must be non-empty when provided")
        return normalized


class MemoryBrokerQueryResponse(StrictModel):
    workspace_id: str = Field(min_length=1)
    project_id: str | None = None
    query: str = Field(min_length=1)
    provider: MemoryBrokerProvider = MemoryBrokerProvider.KG_MCP
    provider_status: MemoryBrokerProviderStatus
    scope: MemoryBrokerScope
    results: list[MemoryBrokerResult] = Field(default_factory=list)
    audit: MemoryBrokerAuditRecord


class SessionCheckpoint(StrictModel):
    user_id: str = Field(min_length=1)
    device_session_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    last_message_id: str | None = None
    draft_text: str
    selected_memory_ids: list[str]
    route: str = Field(min_length=1)
    surface: Surface = Surface.WEB
    handoff_kind: HandoffKind = HandoffKind.NONE
    resume_token_ref: str | None = None
    last_surface_at: str | None = None
    updated_at: str
    version: int = Field(ge=1)


class CheckpointUpsertRequest(SessionCheckpoint):
    base_version: int | None = Field(default=None, ge=1)
    force: bool = False


class CheckpointConflictResponse(StrictModel):
    code: str = "checkpoint_conflict"
    message: str = Field(min_length=1)
    server_checkpoint: SessionCheckpoint
    client_checkpoint: SessionCheckpoint


class TelegramLinkState(StrictModel):
    surface: Literal["telegram"] = "telegram"
    status: TelegramLinkStatus
    is_linked: bool
    link_code: str | None = None
    bot_deep_link: str | None = None
    expires_at: str | None = None
    telegram_display_name: str | None = None
    telegram_username: str | None = None
    linked_at: str | None = None
    last_event_at: str | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    last_resume_token_ref: str | None = None


class TelegramMockLinkCompleteRequest(StrictModel):
    link_code: str = Field(min_length=4)
    telegram_user_id: str = Field(min_length=1)
    telegram_chat_id: str = Field(min_length=1)
    telegram_username: str | None = None
    telegram_display_name: str | None = None
    last_resume_token_ref: str | None = None


class ReminderCreateRequest(StrictModel):
    scheduled_for: str
    message: str = Field(min_length=1)
    channel: Literal["telegram"] = "telegram"
    follow_up_policy: ReminderFollowUpPolicy | None = None

    @field_validator("scheduled_for")
    @classmethod
    def validate_scheduled_for(cls, value: str) -> str:
        return _normalize_utc_timestamp(value, field_name="scheduled_for")

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("message is required")
        return normalized


class ReminderFollowUpPolicy(StrictModel):
    on_failure: ReminderFollowUpFailureAction = ReminderFollowUpFailureAction.NONE
    max_attempts: int = Field(default=1, ge=1, le=10)
    retry_delay_seconds: int = Field(default=0, ge=0, le=7 * 24 * 60 * 60)

    @model_validator(mode="after")
    def validate_policy(self) -> ReminderFollowUpPolicy:
        if self.on_failure == ReminderFollowUpFailureAction.NONE:
            self.max_attempts = 1
            self.retry_delay_seconds = 0
            return self
        if self.max_attempts < 2:
            raise ValueError("follow_up_policy.max_attempts must be at least 2 when retries are enabled")
        return self


class ReminderFollowUpState(StrictModel):
    status: ReminderFollowUpStatus = ReminderFollowUpStatus.NONE
    attempt_count: int = Field(default=0, ge=0)
    last_attempt_at: str | None = None
    next_attempt_at: str | None = None
    last_transition_at: str | None = None
    last_transition_reason: str | None = None

    @field_validator("last_attempt_at", "next_attempt_at", "last_transition_at")
    @classmethod
    def validate_timestamps(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        return _normalize_utc_timestamp(value, field_name=info.field_name)


class RuntimeJobAudit(StrictModel):
    device_session_id: str = Field(min_length=1)
    surface: Surface
    conversation_id: str | None = None


class RuntimeJobRecord(StrictModel):
    job_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    kind: JobKind
    status: JobStatus
    requested_at: str
    available_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    resource_id: str | None = None
    attempt_count: int = Field(default=0, ge=0)
    audit: RuntimeJobAudit
    details: dict[str, object] = Field(default_factory=dict)


class RuntimeJobsResponse(StrictModel):
    items: list[RuntimeJobRecord] = Field(default_factory=list)


class ReminderRecord(StrictModel):
    reminder_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    device_session_id: str = Field(min_length=1)
    status: ReminderStatus
    channel: Surface
    scheduled_for: str
    payload: dict[str, object] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    delivered_at: str | None = None
    canceled_at: str | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    follow_up_policy: ReminderFollowUpPolicy = Field(default_factory=ReminderFollowUpPolicy)
    follow_up_state: ReminderFollowUpState = Field(default_factory=ReminderFollowUpState)


class ReminderListResponse(StrictModel):
    items: list[ReminderRecord] = Field(default_factory=list)


class EvidenceRef(StrictModel):
    app_version: str = Field(min_length=1)
    bundle_id: str = Field(min_length=1)
    summary_ref: str = Field(min_length=1)
    overall_status: StageStatus
    generated_at: str


class EvidenceScore(StrictModel):
    total: int = Field(ge=0)
    max: int = Field(ge=0)


class EvidenceStageStatus(StrictModel):
    stage_id: str
    status: StageStatus
    computed_score: int = Field(ge=0)
    max_score: int = Field(ge=0)


class UserVisibleControls(StrictModel):
    memory_export_supported: bool
    memory_delete_supported: bool
    latest_change_log_url: str
    evidence_detail_url: str


class PublicEvidenceLink(StrictModel):
    label: str = Field(min_length=1)
    url: str = Field(min_length=1)


class EvidenceSummary(StrictModel):
    schema_version: str = Field(min_length=1)
    artifact_kind: str
    artifact_id: str = Field(min_length=1)
    bundle_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    git_commit: str = Field(min_length=1)
    git_tree_state: str
    inputs_hash: str = Field(min_length=1)
    content_hash: str = Field(min_length=1)
    created_at: str
    producer: str = Field(min_length=1)
    visibility: str
    status: StageStatus
    app_version: str = Field(min_length=1)
    release_channel: str
    generated_at: str
    overall_status: StageStatus
    trust_label: str = Field(min_length=1)
    score: EvidenceScore
    stage_statuses: list[EvidenceStageStatus]
    highlights: list[str]
    user_visible_controls: UserVisibleControls
    public_evidence_links: list[PublicEvidenceLink]


class TrustCurrentResponse(StrictModel):
    app_version: str = Field(min_length=1)
    evidence_ref: EvidenceRef
    summary: EvidenceSummary


class TrustBundleResponse(StrictModel):
    bundle_id: str = Field(min_length=1)
    summary: EvidenceSummary
