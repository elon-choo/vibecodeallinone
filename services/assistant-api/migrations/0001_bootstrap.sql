CREATE TABLE IF NOT EXISTS user (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    display_name TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_account (
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_subject TEXT NOT NULL,
    scope_json TEXT NOT NULL,
    token_ref TEXT,
    connected_at TEXT NOT NULL,
    last_refresh_at TEXT,
    PRIMARY KEY (user_id, provider),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS device_session (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    device_label TEXT NOT NULL,
    platform TEXT NOT NULL,
    session_id TEXT NOT NULL UNIQUE,
    auth_state TEXT NOT NULL,
    provider_subject TEXT NOT NULL,
    scopes_json TEXT NOT NULL,
    connected_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_device_session_user_id ON device_session(user_id);
CREATE INDEX IF NOT EXISTS idx_device_session_session_id ON device_session(session_id);

CREATE TABLE IF NOT EXISTS auth_flow (
    oauth_state TEXT PRIMARY KEY,
    device_session_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    code_verifier TEXT NOT NULL,
    code_challenge TEXT NOT NULL,
    consumed_at TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (device_session_id) REFERENCES device_session(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_auth_flow_device_session_id ON auth_flow(device_session_id);

CREATE TABLE IF NOT EXISTS memory_item (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL,
    importance INTEGER NOT NULL,
    source_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_used_at TEXT,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_memory_item_user_status ON memory_item(user_id, status);

CREATE TABLE IF NOT EXISTS memory_revision (
    memory_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    action TEXT NOT NULL,
    diff_json TEXT,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (memory_id, version),
    FOREIGN KEY (memory_id) REFERENCES memory_item(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS memory_source (
    memory_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    message_id TEXT,
    note TEXT,
    captured_at TEXT NOT NULL,
    PRIMARY KEY (memory_id, conversation_id, captured_at),
    FOREIGN KEY (memory_id) REFERENCES memory_item(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS memory_export_job (
    export_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL,
    format TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    item_count INTEGER NOT NULL,
    requested_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_memory_export_job_user_id ON memory_export_job(user_id);

CREATE TABLE IF NOT EXISTS memory_delete_job (
    delete_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    memory_id TEXT NOT NULL,
    status TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    purge_after TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (memory_id) REFERENCES memory_item(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_memory_delete_job_user_id ON memory_delete_job(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_delete_job_memory_id ON memory_delete_job(memory_id);

CREATE TABLE IF NOT EXISTS session_checkpoint (
    user_id TEXT NOT NULL,
    device_session_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    last_message_id TEXT,
    draft_text TEXT NOT NULL,
    selected_memory_ids_json TEXT NOT NULL,
    route TEXT NOT NULL,
    surface TEXT NOT NULL DEFAULT 'web',
    handoff_kind TEXT NOT NULL DEFAULT 'none',
    resume_token_ref TEXT,
    last_surface_at TEXT,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    PRIMARY KEY (user_id, device_session_id),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (device_session_id) REFERENCES device_session(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS telegram_link_state (
    user_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    link_code TEXT,
    link_token_hash TEXT,
    expires_at TEXT,
    telegram_user_id TEXT,
    telegram_username TEXT,
    telegram_display_name TEXT,
    telegram_chat_id TEXT,
    linked_at TEXT,
    last_event_at TEXT,
    last_error_code TEXT,
    last_error_message TEXT,
    last_resume_token_ref TEXT,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_telegram_link_state_status ON telegram_link_state(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_telegram_link_state_telegram_user_id
    ON telegram_link_state(telegram_user_id)
    WHERE telegram_user_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS runtime_job (
    job_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    device_session_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    available_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    error_code TEXT,
    error_message TEXT,
    resource_id TEXT,
    lease_owner TEXT,
    lease_token TEXT,
    lease_expires_at TEXT,
    last_heartbeat_at TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    audit_surface TEXT NOT NULL,
    audit_conversation_id TEXT,
    details_json TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (device_session_id) REFERENCES device_session(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_runtime_job_user_requested_at ON runtime_job(user_id, requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_runtime_job_user_status ON runtime_job(user_id, status);
CREATE INDEX IF NOT EXISTS idx_runtime_job_status_available_at
    ON runtime_job(status, available_at, requested_at);

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
);

CREATE INDEX IF NOT EXISTS idx_reminder_delivery_user_scheduled_for
    ON reminder_delivery(user_id, scheduled_for);
CREATE INDEX IF NOT EXISTS idx_reminder_delivery_status
    ON reminder_delivery(status);

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
);

CREATE INDEX IF NOT EXISTS idx_memory_broker_workspace_user_status
    ON memory_broker_workspace(user_id, status);

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
);

CREATE INDEX IF NOT EXISTS idx_memory_broker_audit_user_created_at
    ON memory_broker_audit(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS telegram_transport_cursor (
    cursor_name TEXT PRIMARY KEY,
    next_update_id INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_ref (
    app_version TEXT PRIMARY KEY,
    bundle_id TEXT NOT NULL,
    summary_ref TEXT NOT NULL,
    overall_status TEXT NOT NULL,
    generated_at TEXT NOT NULL
);
