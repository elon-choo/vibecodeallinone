"""assistant-api bootstrap runtime tests."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).parent.parent
SERVICE_ROOT = REPO_ROOT / "services" / "assistant-api"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from assistant_api.app import create_app  # noqa: E402
from assistant_api.config import Settings  # noqa: E402
from assistant_api.memory_broker import StaticMemoryBrokerBackend  # noqa: E402
from assistant_api.models import MemoryBrokerResult, MemoryBrokerResultKind  # noqa: E402


def write_trust_artifacts(repo_root: Path, app_version: str, bundle_id: str) -> None:
    artifacts_dir = repo_root / "artifacts"
    bundle_dir = artifacts_dir / "bundles" / bundle_id
    evidence_refs_dir = artifacts_dir / "evidence_refs"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    evidence_refs_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "schema_version": "0.1.0",
        "artifact_kind": "evidence_summary",
        "artifact_id": "summary_test",
        "bundle_id": bundle_id,
        "run_id": "run_test",
        "git_commit": "unknown",
        "git_tree_state": "unknown",
        "inputs_hash": "sha256:test",
        "content_hash": "sha256:test",
        "created_at": "2026-03-09T12:00:00Z",
        "producer": "tests",
        "visibility": "public_summary",
        "status": "pass",
        "app_version": app_version,
        "release_channel": "internal",
        "generated_at": "2026-03-09T12:00:00Z",
        "overall_status": "pass",
        "trust_label": "Evidence verified",
        "score": {"total": 90, "max": 100},
        "stage_statuses": [
            {"stage_id": "machine_gates", "status": "pass", "computed_score": 30, "max_score": 30},
            {"stage_id": "quality_review", "status": "pass", "computed_score": 20, "max_score": 30},
            {"stage_id": "e2e_validation", "status": "pass", "computed_score": 20, "max_score": 20},
            {"stage_id": "release_readiness", "status": "warn", "computed_score": 20, "max_score": 20},
        ],
        "highlights": ["Machine gates passed."],
        "user_visible_controls": {
            "memory_export_supported": True,
            "memory_delete_supported": True,
            "latest_change_log_url": "/changelog",
            "evidence_detail_url": f"/trust/evidence/{bundle_id}",
        },
        "public_evidence_links": [{"label": "Quality report", "url": f"/trust/evidence/{bundle_id}"}],
    }
    manifest = {
        "schema_version": "0.1.0",
        "artifact_kind": "bundle_manifest",
        "artifact_id": "manifest_test",
        "bundle_id": bundle_id,
        "run_id": "run_test",
        "git_commit": "unknown",
        "git_tree_state": "unknown",
        "inputs_hash": "sha256:test",
        "content_hash": "sha256:test",
        "created_at": "2026-03-09T12:00:00Z",
        "producer": "tests",
        "visibility": "operator",
        "status": "pass",
        "app_version": app_version,
        "release_channel": "internal",
        "overall_status": "pass",
        "stage_order": ["machine_gates", "quality_review", "e2e_validation", "release_readiness"],
        "stage_artifacts": {},
        "summary_artifact": "summary.json",
    }
    evidence_ref = {
        "app_version": app_version,
        "bundle_id": bundle_id,
        "summary_ref": f"artifacts/bundles/{bundle_id}/summary.json",
        "overall_status": "pass",
        "generated_at": "2026-03-09T12:00:00Z",
    }
    latest = {
        "bundle_id": bundle_id,
        "app_version": app_version,
        "overall_status": "pass",
        "generated_at": "2026-03-09T12:00:00Z",
        "manifest_path": f"artifacts/bundles/{bundle_id}/manifest.json",
        "summary_path": f"artifacts/bundles/{bundle_id}/summary.json",
    }

    (bundle_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (evidence_refs_dir / f"{app_version}.json").write_text(json.dumps(evidence_ref), encoding="utf-8")
    (artifacts_dir / "latest.json").write_text(json.dumps(latest), encoding="utf-8")


def make_settings(
    repo_root: Path,
    app_version: str,
    *,
    memory_delete_retention_seconds: int = 7 * 24 * 60 * 60,
    worker_poll_interval_seconds: float = 0.01,
    worker_job_lease_seconds: int = 30,
) -> Settings:
    return Settings(
        repo_root=repo_root,
        artifacts_dir=repo_root / "artifacts",
        db_path=repo_root / "assistant_api.sqlite3",
        migration_path=SERVICE_ROOT / "migrations" / "0001_bootstrap.sql",
        app_version=app_version,
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
        worker_poll_interval_seconds=worker_poll_interval_seconds,
        worker_job_lease_seconds=worker_job_lease_seconds,
        secure_cookies=False,
        session_ttl_seconds=3600,
    )


def request_path(target_url: str) -> str:
    parsed = urlsplit(target_url)
    return f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path


def init_git_repo(repo_root: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo_root, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(
        ["git", "config", "user.email", "assistant-runtime-tests@example.com"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["git", "config", "user.name", "Assistant Runtime Tests"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(
        ["git", "commit", "-m", "seed trust artifacts"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def bootstrap_authenticated_client(
    tmp_path: Path,
    *,
    memory_broker=None,
) -> tuple[TestClient, Path, dict[str, str]]:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "package.json").write_text(json.dumps({"version": "2.0.0"}), encoding="utf-8")
    write_trust_artifacts(repo_root, "2.0.0", "bundle_20260309T120500Z_abc1234")

    app = create_app(make_settings(repo_root, "2.0.0"), memory_broker=memory_broker)
    client = TestClient(app)

    auth_start = client.post(
        "/v1/auth/openai/start",
        json={
            "redirect_uri": "https://assistant-web.local/callback",
            "device_label": "Runtime Reminder Tests",
            "platform": "web",
        },
    )
    provider_redirect = client.get(request_path(auth_start.json()["authorization_url"]), follow_redirects=False)
    client.get(request_path(provider_redirect.headers["location"]), follow_redirects=False)
    return client, repo_root, client.get("/v1/auth/session").json()


def link_telegram_companion(
    client: TestClient,
    *,
    telegram_user_id: str = "tg_runtime_01",
    telegram_chat_id: str = "chat_runtime_01",
    telegram_username: str = "runtimebot",
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
            "telegram_display_name": "Runtime Bot",
            "last_resume_token_ref": "resume_tg_runtime",
        },
    )
    assert complete_response.status_code == 200


def test_assistant_api_auth_memory_checkpoint_and_trust_flow(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "package.json").write_text(json.dumps({"version": "2.0.0"}), encoding="utf-8")
    bundle_id = "bundle_20260309T120500Z_abc1234"
    write_trust_artifacts(repo_root, "2.0.0", bundle_id)

    app = create_app(make_settings(repo_root, "2.0.0"))
    client = TestClient(app)

    auth_start = client.post(
        "/v1/auth/openai/start",
        json={
            "redirect_uri": "https://assistant-web.local/callback",
            "device_label": "iPhone Safari",
            "platform": "web",
        },
    )
    assert auth_start.status_code == 200
    assert auth_start.cookies.get("assistant_session")
    assert "/v1/auth/openai/mock/authorize" in auth_start.json()["authorization_url"]

    session_response = client.get("/v1/auth/session")
    assert session_response.status_code == 200
    session_payload = session_response.json()
    assert session_payload["auth_state"] == "pending_consent"

    provider_redirect = client.get(request_path(auth_start.json()["authorization_url"]), follow_redirects=False)
    assert provider_redirect.status_code == 303
    assert "/v1/auth/openai/callback" in provider_redirect.headers["location"]

    callback_response = client.get(request_path(provider_redirect.headers["location"]), follow_redirects=False)
    assert callback_response.status_code == 303
    assert callback_response.headers["location"].startswith("https://assistant-web.local/callback?auth=success")

    session_response = client.get("/v1/auth/session")
    assert session_response.status_code == 200
    session_payload = session_response.json()
    assert session_payload["auth_state"] == "active"
    assert session_payload["provider"]["provider_subject"].startswith("openai-mock:")

    telegram_state = client.get("/v1/surfaces/telegram/link")
    assert telegram_state.status_code == 200
    assert telegram_state.json()["status"] == "not_linked"
    assert telegram_state.json()["is_linked"] is False

    telegram_link_start = client.post("/v1/surfaces/telegram/link")
    assert telegram_link_start.status_code == 200
    link_payload = telegram_link_start.json()
    assert link_payload["status"] == "pending"
    assert link_payload["link_code"]
    assert link_payload["bot_deep_link"].startswith("https://t.me/test_assistant_bot?start=")

    telegram_link_complete = client.post(
        "/v1/internal/test/telegram/link/complete",
        json={
            "link_code": link_payload["link_code"],
            "telegram_user_id": "tg_user_01",
            "telegram_chat_id": "chat_01",
            "telegram_username": "powerpack",
            "telegram_display_name": "Power Pack",
            "last_resume_token_ref": "resume_tg_01",
        },
    )
    assert telegram_link_complete.status_code == 200
    assert telegram_link_complete.json()["status"] == "linked"
    assert telegram_link_complete.json()["telegram_username"] == "powerpack"

    telegram_link_state = client.get("/v1/surfaces/telegram/link")
    assert telegram_link_state.status_code == 200
    assert telegram_link_state.json()["is_linked"] is True
    assert telegram_link_state.json()["last_resume_token_ref"] == "resume_tg_01"

    memory_item = {
        "id": "memory_01",
        "user_id": session_payload["user_id"],
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
                "memory_id": "memory_01",
                "conversation_id": "conv_01",
                "message_id": "msg_08",
                "note": "Captured from onboarding shell",
                "captured_at": "2026-03-09T12:01:00Z",
            }
        ],
    }
    created_memory = client.post("/v1/memory/items", json=memory_item)
    assert created_memory.status_code == 201
    assert created_memory.json()["sources"][0]["conversation_id"] == "conv_01"

    listed_memory = client.get("/v1/memory/items")
    assert listed_memory.status_code == 200
    assert listed_memory.json()["items"][0]["id"] == "memory_01"
    assert listed_memory.json()["items"][0]["sources"][0]["note"] == "Captured from onboarding shell"

    checkpoint_payload = {
        "user_id": session_payload["user_id"],
        "device_session_id": session_payload["device_session_id"],
        "conversation_id": "conv_01",
        "last_message_id": "msg_09",
        "draft_text": "Draft reply",
        "selected_memory_ids": ["memory_01"],
        "route": "/chat/conv_01",
        "surface": "web",
        "handoff_kind": "none",
        "resume_token_ref": None,
        "last_surface_at": "2026-03-09T12:05:00Z",
        "updated_at": "2026-03-09T12:05:00Z",
        "version": 1,
        "base_version": None,
        "force": False,
    }
    stored_checkpoint = client.put("/v1/checkpoints/current", json=checkpoint_payload)
    assert stored_checkpoint.status_code == 200
    assert stored_checkpoint.json()["surface"] == "web"
    assert stored_checkpoint.json()["handoff_kind"] == "none"
    current_checkpoint = client.get("/v1/checkpoints/current")
    assert current_checkpoint.status_code == 200
    assert current_checkpoint.json()["conversation_id"] == "conv_01"
    assert current_checkpoint.json()["last_surface_at"] == "2026-03-09T12:05:00Z"

    memory_export = client.post("/v1/memory/exports")
    assert memory_export.status_code == 200
    export_payload = memory_export.json()
    assert export_payload["job_id"] == export_payload["export_id"]
    assert export_payload["item_count"] == 1
    assert export_payload["items"][0]["item"]["sources"][0]["conversation_id"] == "conv_01"
    assert export_payload["items"][0]["revisions"][0]["action"] == "created"
    export_artifact = repo_root / "artifacts" / "memory_exports" / f"{export_payload['export_id']}.json"
    assert export_artifact.exists()

    checkpoint_payload["draft_text"] = "Server moved ahead"
    checkpoint_payload["selected_memory_ids"] = []
    checkpoint_payload["surface"] = "telegram"
    checkpoint_payload["handoff_kind"] = "resume_link"
    checkpoint_payload["resume_token_ref"] = "resume_tg_01"
    checkpoint_payload["last_surface_at"] = "2026-03-09T12:05:10Z"
    checkpoint_payload["updated_at"] = "2026-03-09T12:05:10Z"
    checkpoint_payload["version"] = 2
    checkpoint_payload["base_version"] = 1
    next_checkpoint = client.put("/v1/checkpoints/current", json=checkpoint_payload)
    assert next_checkpoint.status_code == 200
    assert next_checkpoint.json()["version"] == 2
    assert next_checkpoint.json()["surface"] == "telegram"
    assert next_checkpoint.json()["resume_token_ref"] == "resume_tg_01"

    stale_checkpoint = {
        "user_id": session_payload["user_id"],
        "device_session_id": session_payload["device_session_id"],
        "conversation_id": "conv_01",
        "last_message_id": "msg_10",
        "draft_text": "Local stale draft",
        "selected_memory_ids": ["memory_01"],
        "route": "/chat/conv_01",
        "surface": "web",
        "handoff_kind": "quick_capture",
        "resume_token_ref": "resume_tg_01",
        "last_surface_at": "2026-03-09T12:05:20Z",
        "updated_at": "2026-03-09T12:05:20Z",
        "version": 2,
        "base_version": 1,
        "force": False,
    }
    checkpoint_conflict = client.put("/v1/checkpoints/current", json=stale_checkpoint)
    assert checkpoint_conflict.status_code == 409
    assert checkpoint_conflict.json()["code"] == "checkpoint_conflict"
    assert checkpoint_conflict.json()["server_checkpoint"]["version"] == 2

    stale_checkpoint["force"] = True
    stale_checkpoint["base_version"] = 2
    forced_checkpoint = client.put("/v1/checkpoints/current", json=stale_checkpoint)
    assert forced_checkpoint.status_code == 200
    assert forced_checkpoint.json()["version"] == 3
    assert forced_checkpoint.json()["selected_memory_ids"] == ["memory_01"]
    assert forced_checkpoint.json()["handoff_kind"] == "quick_capture"

    deleted_memory = client.delete("/v1/memory/items/memory_01")
    assert deleted_memory.status_code == 202
    assert deleted_memory.json()["job_id"] == deleted_memory.json()["delete_id"]
    assert deleted_memory.json()["purge_status"] == "pending_purge"

    archived_memory = client.get("/v1/memory/items")
    assert archived_memory.status_code == 200
    assert archived_memory.json()["items"][0]["status"] == "deleted"

    jobs_response = client.get("/v1/jobs")
    assert jobs_response.status_code == 200
    jobs_payload = jobs_response.json()
    assert [job["kind"] for job in jobs_payload["items"]] == ["memory_delete", "memory_export"]
    assert jobs_payload["items"][0]["status"] == "queued"
    assert jobs_payload["items"][0]["resource_id"] == "memory_01"
    assert jobs_payload["items"][0]["audit"]["surface"] == "web"
    assert jobs_payload["items"][0]["audit"]["conversation_id"] == "conv_01"
    assert jobs_payload["items"][1]["job_id"] == export_payload["job_id"]
    assert jobs_payload["items"][1]["status"] == "succeeded"
    assert jobs_payload["items"][1]["details"]["item_count"] == 1

    trust_current = client.get("/v1/trust/current")
    assert trust_current.status_code == 200
    assert trust_current.json()["evidence_ref"]["bundle_id"] == bundle_id

    trust_bundle = client.get(f"/v1/trust/bundles/{bundle_id}")
    assert trust_bundle.status_code == 200
    assert trust_bundle.json()["summary"]["trust_label"] == "Evidence verified"


def test_assistant_api_checkpoint_accepts_legacy_payload_without_continuity_fields(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "package.json").write_text(json.dumps({"version": "2.0.0"}), encoding="utf-8")
    write_trust_artifacts(repo_root, "2.0.0", "bundle_20260309T120500Z_abc1234")

    app = create_app(make_settings(repo_root, "2.0.0"))
    client = TestClient(app)

    auth_start = client.post(
        "/v1/auth/openai/start",
        json={
            "redirect_uri": "https://assistant-web.local/callback",
            "device_label": "Legacy Shell",
            "platform": "web",
        },
    )
    provider_redirect = client.get(request_path(auth_start.json()["authorization_url"]), follow_redirects=False)
    client.get(request_path(provider_redirect.headers["location"]), follow_redirects=False)

    session_payload = client.get("/v1/auth/session").json()
    legacy_payload = {
        "user_id": session_payload["user_id"],
        "device_session_id": session_payload["device_session_id"],
        "conversation_id": "conv_legacy",
        "last_message_id": "msg_legacy",
        "draft_text": "Legacy checkpoint payload",
        "selected_memory_ids": [],
        "route": "/chat/conv_legacy",
        "updated_at": "2026-03-09T13:00:00Z",
        "version": 1,
        "base_version": None,
        "force": False,
    }

    stored_checkpoint = client.put("/v1/checkpoints/current", json=legacy_payload)
    assert stored_checkpoint.status_code == 200
    assert stored_checkpoint.json()["surface"] == "web"
    assert stored_checkpoint.json()["handoff_kind"] == "none"
    assert stored_checkpoint.json()["resume_token_ref"] is None
    assert stored_checkpoint.json()["last_surface_at"] == "2026-03-09T13:00:00Z"


def test_assistant_api_memory_broker_opt_in_and_query_respects_workspace_scope(tmp_path):
    memory_broker = StaticMemoryBrokerBackend(
        entries=[
            MemoryBrokerResult(
                entry_id="kg_doc_01",
                workspace_id="workspace_alpha",
                project_id="project_release",
                kind=MemoryBrokerResultKind.DOCUMENT,
                title="Release checklist",
                content="Release evidence must be refreshed before shipping.",
                source_ref="docs/release-checklist.md",
                score=0.92,
            ),
            MemoryBrokerResult(
                entry_id="kg_doc_02",
                workspace_id="workspace_alpha",
                project_id="project_ops",
                kind=MemoryBrokerResultKind.SUMMARY,
                title="Ops summary",
                content="Managed quickstart notes for operators.",
                source_ref="ops/managed/README.md",
                score=0.75,
            ),
            MemoryBrokerResult(
                entry_id="kg_doc_03",
                workspace_id="workspace_beta",
                project_id="project_release",
                kind=MemoryBrokerResultKind.CODE,
                title="Other workspace",
                content="Should never cross the workspace boundary.",
                source_ref="services/assistant-api/assistant_api/store.py",
                score=0.99,
            ),
        ]
    )
    client, _, _ = bootstrap_authenticated_client(tmp_path, memory_broker=memory_broker)

    baseline_memory = client.get("/v1/memory/items")
    assert baseline_memory.status_code == 200
    assert baseline_memory.json()["items"] == []

    initial_state = client.get("/v1/memory/broker/workspaces/workspace_alpha")
    assert initial_state.status_code == 200
    assert initial_state.json()["status"] == "disabled"
    assert initial_state.json()["provider_status"] == "ready"
    assert initial_state.json()["scope"]["project_ids"] == []

    enable_state = client.put(
        "/v1/memory/broker/workspaces/workspace_alpha",
        json={
            "enabled": True,
            "project_ids": ["project_release"],
            "source_surface": "web",
        },
    )
    assert enable_state.status_code == 200
    enable_payload = enable_state.json()
    assert enable_payload["status"] == "enabled"
    assert enable_payload["consent"]["enabled"] is True
    assert enable_payload["consent"]["source_surface"] == "web"
    assert enable_payload["consent"]["granted_at"] is not None
    assert enable_payload["scope"]["project_ids"] == ["project_release"]
    assert enable_payload["provider_status"] == "ready"

    listed_states = client.get("/v1/memory/broker/workspaces")
    assert listed_states.status_code == 200
    assert listed_states.json()["items"][0]["workspace_id"] == "workspace_alpha"

    query_response = client.post(
        "/v1/memory/broker/workspaces/workspace_alpha/query",
        json={
            "query": "release evidence",
            "project_id": "project_release",
            "limit": 5,
            "source_surface": "web",
        },
    )
    assert query_response.status_code == 200
    query_payload = query_response.json()
    assert query_payload["provider_status"] == "ready"
    assert query_payload["scope"]["project_ids"] == ["project_release"]
    assert len(query_payload["results"]) == 1
    assert query_payload["results"][0]["entry_id"] == "kg_doc_01"
    assert query_payload["results"][0]["workspace_id"] == "workspace_alpha"
    assert query_payload["results"][0]["project_id"] == "project_release"
    assert query_payload["audit"]["action"] == "read"
    assert query_payload["audit"]["status"] == "succeeded"

    refreshed_state = client.get("/v1/memory/broker/workspaces/workspace_alpha")
    assert refreshed_state.status_code == 200
    assert refreshed_state.json()["last_audit_id"] == query_payload["audit"]["audit_id"]
    assert refreshed_state.json()["last_brokered_at"] is not None
    assert refreshed_state.json()["last_error_code"] is None

    outside_scope = client.post(
        "/v1/memory/broker/workspaces/workspace_alpha/query",
        json={
            "query": "managed quickstart",
            "project_id": "project_ops",
            "source_surface": "web",
        },
    )
    assert outside_scope.status_code == 400
    assert "outside the opted-in workspace scope" in outside_scope.json()["detail"]


def test_assistant_api_memory_broker_stays_opt_in_and_blocks_raw_telegram_queries(tmp_path):
    client, _, _ = bootstrap_authenticated_client(tmp_path)

    blocked_before_opt_in = client.post(
        "/v1/memory/broker/workspaces/workspace_alpha/query",
        json={
            "query": "release evidence",
            "source_surface": "web",
        },
    )
    assert blocked_before_opt_in.status_code == 400
    assert "not enabled" in blocked_before_opt_in.json()["detail"]

    opt_in_response = client.put(
        "/v1/memory/broker/workspaces/workspace_alpha",
        json={
            "enabled": True,
            "project_ids": ["project_release"],
            "source_surface": "web",
        },
    )
    assert opt_in_response.status_code == 200
    assert opt_in_response.json()["provider_status"] == "disabled"

    unavailable_query = client.post(
        "/v1/memory/broker/workspaces/workspace_alpha/query",
        json={
            "query": "release evidence",
            "project_id": "project_release",
            "source_surface": "web",
        },
    )
    assert unavailable_query.status_code == 200
    unavailable_payload = unavailable_query.json()
    assert unavailable_payload["provider_status"] == "disabled"
    assert unavailable_payload["results"] == []
    assert unavailable_payload["audit"]["status"] == "unavailable"

    refreshed_state = client.get("/v1/memory/broker/workspaces/workspace_alpha")
    assert refreshed_state.status_code == 200
    assert refreshed_state.json()["status"] == "enabled"
    assert refreshed_state.json()["last_error_code"] == "provider_unavailable"

    telegram_opt_in = client.put(
        "/v1/memory/broker/workspaces/workspace_beta",
        json={
            "enabled": True,
            "source_surface": "telegram",
        },
    )
    assert telegram_opt_in.status_code == 400
    assert "telegram surface" in telegram_opt_in.json()["detail"]

    telegram_query = client.post(
        "/v1/memory/broker/workspaces/workspace_alpha/query",
        json={
            "query": "release evidence",
            "source_surface": "telegram",
        },
    )
    assert telegram_query.status_code == 400
    assert "telegram surface" in telegram_query.json()["detail"]


def test_assistant_api_reminder_create_list_and_cancel_flow(tmp_path):
    client, _, session_payload = bootstrap_authenticated_client(tmp_path)
    link_telegram_companion(client)

    checkpoint_response = client.put(
        "/v1/checkpoints/current",
        json={
            "user_id": session_payload["user_id"],
            "device_session_id": session_payload["device_session_id"],
            "conversation_id": "conv_reminders",
            "last_message_id": "msg_reminders",
            "draft_text": "Reminder planning",
            "selected_memory_ids": [],
            "route": "/chat/conv_reminders",
            "surface": "web",
            "handoff_kind": "none",
            "resume_token_ref": None,
            "last_surface_at": "2026-03-10T08:00:00Z",
            "updated_at": "2026-03-10T08:00:00Z",
            "version": 1,
            "base_version": None,
            "force": False,
        },
    )
    assert checkpoint_response.status_code == 200

    create_response = client.post(
        "/v1/reminders",
        json={
            "scheduled_for": "2026-03-11T09:00:00+09:00",
            "message": "  Review the reminder audit trail  ",
            "channel": "telegram",
        },
    )
    assert create_response.status_code == 201
    reminder_payload = create_response.json()
    assert reminder_payload["status"] == "scheduled"
    assert reminder_payload["channel"] == "telegram"
    assert reminder_payload["scheduled_for"] == "2026-03-11T00:00:00Z"
    assert reminder_payload["payload"]["message"] == "Review the reminder audit trail"

    list_response = client.get("/v1/reminders")
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["reminder_id"] == reminder_payload["reminder_id"]
    assert list_response.json()["items"][0]["status"] == "scheduled"

    jobs_response = client.get("/v1/jobs", params={"kind": "reminder_delivery"})
    assert jobs_response.status_code == 200
    jobs_payload = jobs_response.json()["items"]
    assert len(jobs_payload) == 1
    assert jobs_payload[0]["job_id"] == reminder_payload["job_id"]
    assert jobs_payload[0]["status"] == "queued"
    assert jobs_payload[0]["audit"]["surface"] == "web"
    assert jobs_payload[0]["audit"]["conversation_id"] == "conv_reminders"
    assert jobs_payload[0]["details"]["payload"]["message"] == "Review the reminder audit trail"

    cancel_response = client.delete(f"/v1/reminders/{reminder_payload['reminder_id']}")
    assert cancel_response.status_code == 200
    canceled_payload = cancel_response.json()
    assert canceled_payload["status"] == "canceled"
    assert canceled_payload["canceled_at"] is not None

    canceled_list = client.get("/v1/reminders", params={"status": "canceled"})
    assert canceled_list.status_code == 200
    assert canceled_list.json()["items"][0]["reminder_id"] == reminder_payload["reminder_id"]
    assert canceled_list.json()["items"][0]["status"] == "canceled"

    canceled_jobs = client.get("/v1/jobs", params={"kind": "reminder_delivery"})
    assert canceled_jobs.status_code == 200
    assert canceled_jobs.json()["items"][0]["status"] == "canceled"
    assert canceled_jobs.json()["items"][0]["details"]["delivery_status"] == "canceled"


def test_assistant_api_reminder_follow_up_policy_round_trip(tmp_path):
    client, _, _ = bootstrap_authenticated_client(tmp_path)
    link_telegram_companion(client)

    create_response = client.post(
        "/v1/reminders",
        json={
            "scheduled_for": "2026-03-11T09:00:00+09:00",
            "message": "Keep retry policy visible",
            "channel": "telegram",
            "follow_up_policy": {
                "on_failure": "retry",
                "max_attempts": 3,
                "retry_delay_seconds": 120,
            },
        },
    )
    assert create_response.status_code == 201
    reminder_payload = create_response.json()
    assert reminder_payload["follow_up_policy"] == {
        "on_failure": "retry",
        "max_attempts": 3,
        "retry_delay_seconds": 120,
    }
    assert reminder_payload["follow_up_state"]["status"] == "none"
    assert reminder_payload["follow_up_state"]["attempt_count"] == 0
    assert reminder_payload["follow_up_state"]["next_attempt_at"] == "2026-03-11T00:00:00Z"
    assert reminder_payload["follow_up_state"]["last_transition_reason"] == "scheduled"

    jobs_response = client.get("/v1/jobs", params={"kind": "reminder_delivery"})
    assert jobs_response.status_code == 200
    jobs_payload = jobs_response.json()["items"]
    assert len(jobs_payload) == 1
    assert jobs_payload[0]["available_at"] == "2026-03-11T00:00:00Z"
    assert jobs_payload[0]["attempt_count"] == 0
    assert jobs_payload[0]["details"]["follow_up_policy"]["on_failure"] == "retry"
    assert jobs_payload[0]["details"]["follow_up_state"]["next_attempt_at"] == "2026-03-11T00:00:00Z"


def test_assistant_api_auth_denial_redirects_back_to_shell(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "package.json").write_text(json.dumps({"version": "2.0.0"}), encoding="utf-8")
    write_trust_artifacts(repo_root, "2.0.0", "bundle_20260309T120500Z_abc1234")

    app = create_app(make_settings(repo_root, "2.0.0"))
    client = TestClient(app)

    auth_start = client.post(
        "/v1/auth/openai/start",
        json={
            "redirect_uri": "https://assistant-web.local/callback",
            "device_label": "MacBook Safari",
            "platform": "web",
        },
    )
    assert auth_start.status_code == 200

    provider_redirect = client.get(f"{request_path(auth_start.json()['authorization_url'])}&deny=true", follow_redirects=False)
    assert provider_redirect.status_code == 303

    callback_response = client.get(request_path(provider_redirect.headers["location"]), follow_redirects=False)
    assert callback_response.status_code == 303
    assert callback_response.headers["location"].startswith("https://assistant-web.local/callback?auth=error")

    session_response = client.get("/v1/auth/session")
    assert session_response.status_code == 200
    assert session_response.json()["auth_state"] == "reauth_required"


def test_assistant_api_trust_current_marks_stale_when_repo_moves_ahead(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "package.json").write_text(json.dumps({"version": "2.0.0"}), encoding="utf-8")
    tracked_file = repo_root / "README.md"
    tracked_file.write_text("seed runtime\n", encoding="utf-8")
    bundle_id = "bundle_20260309T120500Z_abc1234"
    write_trust_artifacts(repo_root, "2.0.0", bundle_id)
    init_git_repo(repo_root)

    time.sleep(1.1)
    tracked_file.write_text("seed runtime moved ahead\n", encoding="utf-8")

    app = create_app(make_settings(repo_root, "2.0.0"))
    client = TestClient(app)

    trust_current = client.get("/v1/trust/current")
    assert trust_current.status_code == 200
    trust_payload = trust_current.json()
    assert trust_payload["summary"]["overall_status"] == "stale"
    assert trust_payload["summary"]["trust_label"] == "Evidence stale"
    assert trust_payload["evidence_ref"]["overall_status"] == "stale"
    assert "Re-run release validation" in trust_payload["summary"]["highlights"][0]
