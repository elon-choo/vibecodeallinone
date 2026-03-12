#!/usr/bin/env python3
"""Shared helpers for assistant-api and assistant-web smoke runs."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE_ROOT = REPO_ROOT / "services" / "assistant-api"
WEB_ROOT = REPO_ROOT / "apps" / "assistant-web"
PLACEHOLDER_MARKERS = ("replace-me", "example.com", "example.org", "example.net", ".invalid", "placeholder")


@dataclass(frozen=True, slots=True)
class RuntimeSeed:
    app_version: str
    bundle_id: str
    repo_root: Path


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def artifact_safe_payload(payload: object) -> object:
    if isinstance(payload, dict):
        return {
            key: artifact_safe_payload(value)
            for key, value in payload.items()
            if not key.startswith("_")
        }
    if isinstance(payload, list):
        return [artifact_safe_payload(item) for item in payload]
    return payload


def initialize_runtime_repo(runtime_root: Path, *, stale_trust: bool) -> RuntimeSeed:
    runtime_root.mkdir(parents=True, exist_ok=True)
    app_version = "2.0.0"
    bundle_id = f"bundle_smoke_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    created_at = utc_now_iso()
    bundle_dir = runtime_root / "artifacts" / "bundles" / bundle_id
    summary_path = bundle_dir / "summary.json"
    manifest_path = bundle_dir / "manifest.json"
    evidence_ref_path = runtime_root / "artifacts" / "evidence_refs" / f"{app_version}.json"
    current_ref_path = runtime_root / "artifacts" / "evidence_refs" / "current.json"
    latest_path = runtime_root / "artifacts" / "latest.json"

    write_json(runtime_root / "package.json", {"name": "assistant-smoke-runtime", "version": app_version})
    (runtime_root / "README.md").write_text("assistant smoke runtime fixture\n", encoding="utf-8")

    summary = {
        "schema_version": "0.1.0",
        "artifact_kind": "evidence_summary",
        "artifact_id": "summary_smoke",
        "bundle_id": bundle_id,
        "run_id": "run_smoke",
        "git_commit": "unknown",
        "git_tree_state": "unknown",
        "inputs_hash": "sha256:smoke",
        "content_hash": "sha256:smoke",
        "created_at": created_at,
        "producer": "scripts/assistant",
        "visibility": "public_summary",
        "status": "pass",
        "app_version": app_version,
        "release_channel": "local",
        "generated_at": created_at,
        "overall_status": "pass",
        "trust_label": "Evidence verified",
        "score": {"total": 92, "max": 100},
        "stage_statuses": [
            {"stage_id": "machine_gates", "status": "pass", "computed_score": 30, "max_score": 30},
            {"stage_id": "quality_review", "status": "pass", "computed_score": 24, "max_score": 30},
            {"stage_id": "e2e_validation", "status": "pass", "computed_score": 18, "max_score": 20},
            {"stage_id": "release_readiness", "status": "warn", "computed_score": 20, "max_score": 20},
        ],
        "highlights": [
            "Machine gates passed.",
            "Memory export and delete controls are wired to runtime handlers.",
        ],
        "user_visible_controls": {
            "memory_export_supported": True,
            "memory_delete_supported": True,
            "latest_change_log_url": "/changelog",
            "evidence_detail_url": f"/trust/evidence/{bundle_id}",
        },
        "public_evidence_links": [
            {"label": "Quality report", "url": f"/trust/evidence/{bundle_id}"},
            {"label": "Release checklist", "url": "/docs/release-checklist"},
        ],
    }
    manifest = {
        "schema_version": "0.1.0",
        "artifact_kind": "bundle_manifest",
        "artifact_id": "manifest_smoke",
        "bundle_id": bundle_id,
        "run_id": "run_smoke",
        "git_commit": "unknown",
        "git_tree_state": "unknown",
        "inputs_hash": "sha256:smoke",
        "content_hash": "sha256:smoke",
        "created_at": created_at,
        "producer": "scripts/assistant",
        "visibility": "operator",
        "status": "pass",
        "app_version": app_version,
        "release_channel": "local",
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
        "generated_at": created_at,
    }
    latest = {
        "bundle_id": bundle_id,
        "app_version": app_version,
        "overall_status": "pass",
        "generated_at": created_at,
        "manifest_path": f"artifacts/bundles/{bundle_id}/manifest.json",
        "summary_path": f"artifacts/bundles/{bundle_id}/summary.json",
    }

    write_json(summary_path, summary)
    write_json(manifest_path, manifest)
    write_json(evidence_ref_path, evidence_ref)
    write_json(current_ref_path, evidence_ref)
    write_json(latest_path, latest)

    run_git(runtime_root, "init")
    run_git(runtime_root, "config", "user.email", "assistant-smoke@example.com")
    run_git(runtime_root, "config", "user.name", "Assistant Smoke")
    run_git(runtime_root, "add", ".")
    run_git(runtime_root, "commit", "-m", "seed smoke runtime")

    if stale_trust:
        time.sleep(1.1)
        (runtime_root / "README.md").write_text("assistant smoke runtime fixture updated after summary\n", encoding="utf-8")

    return RuntimeSeed(app_version=app_version, bundle_id=bundle_id, repo_root=runtime_root)


def run_git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_http(url: str, *, accepted_statuses: tuple[int, ...] = (200,), timeout_seconds: float = 20.0) -> None:
    deadline = time.time() + timeout_seconds
    last_error: str | None = None
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=1.5)
            if response.status_code in accepted_statuses:
                return
            last_error = f"unexpected status {response.status_code}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(0.2)
    raise RuntimeError(f"timed out waiting for {url}: {last_error or 'no response'}")


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


@contextmanager
def start_assistant_api(
    runtime_repo_root: Path,
    *,
    api_port: int,
    web_port: int,
    provider_mode: str = "mock",
    telegram_bot_username: str | None = None,
) -> Iterator[str]:
    with tempfile.NamedTemporaryFile(prefix="assistant-api-smoke-", suffix=".log", delete=False) as log_handle:
        log_path = Path(log_handle.name)

    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(SERVICE_ROOT),
            "ASSISTANT_API_REPO_ROOT": str(runtime_repo_root),
            "ASSISTANT_API_ARTIFACTS_DIR": str(runtime_repo_root / "artifacts"),
            "ASSISTANT_API_DB_PATH": str(runtime_repo_root / "assistant_api.sqlite3"),
            "ASSISTANT_API_MIGRATION_PATH": str(SERVICE_ROOT / "migrations" / "0001_bootstrap.sql"),
            "ASSISTANT_API_PUBLIC_BASE_URL": f"http://127.0.0.1:{api_port}",
            "ASSISTANT_API_WEB_ALLOWED_ORIGINS": f"http://127.0.0.1:{web_port}",
            "ASSISTANT_API_PROVIDER_MODE": provider_mode,
            "ASSISTANT_API_SECURE_COOKIES": "false",
        }
    )
    if telegram_bot_username:
        env["ASSISTANT_API_TELEGRAM_BOT_USERNAME"] = telegram_bot_username

    process = subprocess.Popen(
        [
            "python3",
            "-m",
            "uvicorn",
            "assistant_api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(api_port),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    base_url = f"http://127.0.0.1:{api_port}"
    try:
        wait_for_http(f"{base_url}/v1/trust/current", accepted_statuses=(200,))
        yield base_url
    except Exception as exc:
        _terminate_process(process)
        stdout_output = process.stdout.read() if process.stdout is not None else ""
        log_path.write_text(stdout_output, encoding="utf-8")
        log_output = log_path.read_text(encoding="utf-8", errors="replace")
        raise RuntimeError(f"assistant-api failed to start cleanly:\n{log_output}") from exc
    finally:
        _terminate_process(process)
        if process.stdout is not None:
            remaining_output = process.stdout.read()
            if remaining_output:
                log_path.write_text(remaining_output, encoding="utf-8")
        log_path.unlink(missing_ok=True)


@contextmanager
def start_assistant_web(*, web_port: int) -> Iterator[str]:
    process = subprocess.Popen(
        [
            "python3",
            "-m",
            "http.server",
            str(web_port),
            "--bind",
            "127.0.0.1",
            "--directory",
            str(WEB_ROOT),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    base_url = f"http://127.0.0.1:{web_port}"
    try:
        wait_for_http(base_url, accepted_statuses=(200,))
        yield base_url
    finally:
        _terminate_process(process)


def _env_bool(name: str, default: bool, env: dict[str, str]) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _split_csv(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _looks_placeholder(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    if not normalized:
        return False
    return any(marker in normalized for marker in PLACEHOLDER_MARKERS)


def _is_http_url(value: str | None) -> bool:
    if not value:
        return False
    parts = urlsplit(value)
    return parts.scheme in {"http", "https"} and bool(parts.netloc)


def _is_local_host(value: str | None) -> bool:
    if not value:
        return False
    hostname = (urlsplit(value).hostname or "").lower()
    return hostname in {"127.0.0.1", "localhost"}


def _is_public_https_url(value: str | None) -> bool:
    if not value:
        return False
    parts = urlsplit(value)
    hostname = (parts.hostname or "").lower()
    return parts.scheme == "https" and hostname not in {"", "127.0.0.1", "localhost"}


def _redact_url(url: str | None) -> dict[str, object] | None:
    if not url:
        return None
    parts = urlsplit(url)
    return {
        "scheme": parts.scheme,
        "host": parts.netloc,
        "path": parts.path,
        "has_query": bool(parts.query),
    }


def _build_redirect_uri(
    env: dict[str, str],
    *,
    blockers: list[str],
) -> str | None:
    explicit_redirect_uri = env.get("ASSISTANT_OPERATOR_VALIDATION_WEB_REDIRECT_URI")
    if explicit_redirect_uri:
        if not _is_http_url(explicit_redirect_uri):
            blockers.append("ASSISTANT_OPERATOR_VALIDATION_WEB_REDIRECT_URI must be an absolute http(s) URL.")
            return None
        return explicit_redirect_uri

    allowed_origins = _split_csv(env.get("ASSISTANT_API_WEB_ALLOWED_ORIGINS"))
    if not allowed_origins:
        return None
    return f"{allowed_origins[0].rstrip('/')}/callback"


def _build_validation_api_base(
    env: dict[str, str],
    *,
    blockers: list[str],
    warnings: list[str],
) -> str | None:
    validation_api_base = (env.get("ASSISTANT_OPERATOR_VALIDATION_API_BASE_URL") or env.get("ASSISTANT_API_PUBLIC_BASE_URL") or "").strip()
    if not validation_api_base:
        return None
    if not _is_http_url(validation_api_base):
        blockers.append("ASSISTANT_OPERATOR_VALIDATION_API_BASE_URL must be an absolute http(s) URL when provided.")
        return None

    public_base_url = (env.get("ASSISTANT_API_PUBLIC_BASE_URL") or "").strip()
    if public_base_url and validation_api_base.rstrip("/") != public_base_url.rstrip("/"):
        warnings.append(
            "ASSISTANT_OPERATOR_VALIDATION_API_BASE_URL overrides the live request target; the public callback URL still comes from ASSISTANT_API_PUBLIC_BASE_URL."
        )
    return validation_api_base.rstrip("/")


def build_live_provider_preflight(env: dict[str, str] | None = None) -> dict[str, object]:
    environment = env or os.environ
    provider_mode = environment.get("ASSISTANT_API_PROVIDER_MODE", "mock").strip().lower() or "mock"
    blockers: list[str] = []
    warnings: list[str] = []
    required_live_vars = (
        "ASSISTANT_API_PUBLIC_BASE_URL",
        "ASSISTANT_API_WEB_ALLOWED_ORIGINS",
        "ASSISTANT_API_PROVIDER_CLIENT_ID",
        "ASSISTANT_API_PROVIDER_AUTH_URL",
        "ASSISTANT_API_PROVIDER_TOKEN_URL",
    )
    public_base = (environment.get("ASSISTANT_API_PUBLIC_BASE_URL") or "").strip()
    allowed_origins = _split_csv(environment.get("ASSISTANT_API_WEB_ALLOWED_ORIGINS"))
    validation_api_base = _build_validation_api_base(environment, blockers=blockers, warnings=warnings)
    redirect_uri = _build_redirect_uri(environment, blockers=blockers)

    if provider_mode != "oidc":
        blockers.append("ASSISTANT_API_PROVIDER_MODE must be set to 'oidc' for live provider validation.")

    for name in required_live_vars:
        value = (environment.get(name) or "").strip()
        if not value:
            blockers.append(f"{name} is not set.")
        elif _looks_placeholder(value):
            blockers.append(f"{name} still contains a placeholder value and must be replaced for live provider validation.")

    if public_base and not _is_local_host(public_base) and not _is_public_https_url(public_base):
        blockers.append("ASSISTANT_API_PUBLIC_BASE_URL must be HTTPS outside localhost.")

    if allowed_origins:
        invalid_origins = [origin for origin in allowed_origins if not _is_http_url(origin)]
        if invalid_origins:
            blockers.append("ASSISTANT_API_WEB_ALLOWED_ORIGINS must contain only absolute http(s) origins.")
        placeholder_origins = [origin for origin in allowed_origins if _looks_placeholder(origin)]
        if placeholder_origins:
            blockers.append(
                "ASSISTANT_API_WEB_ALLOWED_ORIGINS still contains placeholder origins and must be replaced for live provider validation."
            )
        elif public_base and not _is_local_host(public_base):
            insecure_origins = [origin for origin in allowed_origins if not _is_public_https_url(origin)]
            if insecure_origins:
                blockers.append("ASSISTANT_API_WEB_ALLOWED_ORIGINS must contain only HTTPS public origins outside localhost.")

    if public_base and not _is_local_host(public_base) and not _env_bool("ASSISTANT_API_SECURE_COOKIES", False, environment):
        blockers.append("ASSISTANT_API_SECURE_COOKIES must be true for live provider validation outside localhost.")

    if redirect_uri is None:
        blockers.append(
            "ASSISTANT_OPERATOR_VALIDATION_WEB_REDIRECT_URI must be set or ASSISTANT_API_WEB_ALLOWED_ORIGINS must contain at least one origin."
        )
    elif not _is_http_url(redirect_uri):
        blockers.append("The resolved live validation redirect URI must be an absolute http(s) URL.")

    if not environment.get("ASSISTANT_API_PROVIDER_USERINFO_URL"):
        warnings.append(
            "ASSISTANT_API_PROVIDER_USERINFO_URL is not set. Live identity resolution then depends on an id_token with a stable subject claim."
        )
    elif _looks_placeholder(environment.get("ASSISTANT_API_PROVIDER_USERINFO_URL")):
        warnings.append(
            "ASSISTANT_API_PROVIDER_USERINFO_URL still looks like a placeholder and should be replaced before live validation."
        )

    if not environment.get("OPENAI_API_KEY"):
        warnings.append("OPENAI_API_KEY is not set. This is not required for OAuth, but it means only the auth surface is being validated.")

    return {
        "provider_mode": provider_mode,
        "eligible_for_live_validation": not blockers,
        "manual_browser_step_required": True,
        "public_base_url": public_base or None,
        "validation_api_base": validation_api_base,
        "redirect_uri": redirect_uri,
        "required_env": list(required_live_vars),
        "blockers": blockers,
        "warnings": warnings,
    }


def build_live_telegram_preflight(env: dict[str, str] | None = None) -> dict[str, object]:
    environment = env or os.environ
    provider_preflight = build_live_provider_preflight(environment)
    blockers = list(provider_preflight["blockers"])
    warnings = list(provider_preflight["warnings"])
    telegram_mode = (environment.get("ASSISTANT_RUNTIME_TELEGRAM_MODE") or "auto").strip().lower() or "auto"
    telegram_api_base_url = (environment.get("ASSISTANT_API_TELEGRAM_API_BASE_URL") or "https://api.telegram.org").rstrip("/")
    bot_token = (environment.get("ASSISTANT_API_TELEGRAM_BOT_TOKEN") or "").strip()
    bot_username = (environment.get("ASSISTANT_API_TELEGRAM_BOT_USERNAME") or "").strip()
    bot_link_base_url = (environment.get("ASSISTANT_API_TELEGRAM_BOT_LINK_BASE_URL") or "").strip()

    if telegram_mode == "disabled":
        blockers.append("ASSISTANT_RUNTIME_TELEGRAM_MODE must not be 'disabled' for live Telegram validation.")
    elif telegram_mode == "enabled" and not bot_token:
        blockers.append("ASSISTANT_RUNTIME_TELEGRAM_MODE=enabled requires ASSISTANT_API_TELEGRAM_BOT_TOKEN.")
    elif telegram_mode == "auto" and not bot_token:
        blockers.append("ASSISTANT_API_TELEGRAM_BOT_TOKEN is required before live Telegram validation can run.")

    if bot_token and not (bot_username or bot_link_base_url):
        blockers.append(
            "ASSISTANT_API_TELEGRAM_BOT_USERNAME or ASSISTANT_API_TELEGRAM_BOT_LINK_BASE_URL must be set for live Telegram validation."
        )

    if bot_username and _looks_placeholder(bot_username):
        blockers.append("ASSISTANT_API_TELEGRAM_BOT_USERNAME still contains a placeholder value.")

    if bot_link_base_url:
        if not _is_http_url(bot_link_base_url):
            blockers.append("ASSISTANT_API_TELEGRAM_BOT_LINK_BASE_URL must be an absolute http(s) URL.")
        elif _looks_placeholder(bot_link_base_url):
            blockers.append("ASSISTANT_API_TELEGRAM_BOT_LINK_BASE_URL still contains a placeholder value.")

    if not _is_http_url(telegram_api_base_url):
        blockers.append("ASSISTANT_API_TELEGRAM_API_BASE_URL must be an absolute http(s) URL.")

    return {
        "eligible_for_live_validation": not blockers,
        "validation_api_base": provider_preflight["validation_api_base"],
        "redirect_uri": provider_preflight["redirect_uri"],
        "public_base_url": provider_preflight["public_base_url"],
        "telegram_mode": telegram_mode,
        "telegram_api_base_url": telegram_api_base_url,
        "bot_username": bot_username or None,
        "has_custom_link_base_url": bool(bot_link_base_url),
        "blockers": blockers,
        "warnings": warnings,
    }


def _probe_provider_authorization_url(authorization_url: str, *, timeout_seconds: float) -> dict[str, object]:
    try:
        response = requests.get(authorization_url, allow_redirects=False, timeout=timeout_seconds)
    except requests.RequestException as exc:
        return {
            "status": "fail",
            "detail": f"provider authorization URL probe failed: {exc}",
            "authorization_url_preview": _redact_url(authorization_url),
        }

    detail = f"provider authorization endpoint responded with HTTP {response.status_code}"
    if 200 <= response.status_code < 400:
        if response.headers.get("location"):
            detail += f" redirecting to {response.headers['location']}"
        return {
            "status": "pass",
            "status_code": response.status_code,
            "detail": detail,
            "authorization_url_preview": _redact_url(authorization_url),
            "redirect_location_preview": _redact_url(response.headers.get("location")),
        }

    return {
        "status": "fail",
        "status_code": response.status_code,
        "detail": detail,
        "authorization_url_preview": _redact_url(authorization_url),
        "response_snippet": response.text[:200],
    }


def _probe_telegram_bot_identity(
    *,
    telegram_api_base_url: str,
    bot_token: str,
    timeout_seconds: float,
) -> dict[str, object]:
    try:
        response = requests.get(
            f"{telegram_api_base_url.rstrip('/')}/bot{bot_token}/getMe",
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        return {"status": "fail", "detail": f"telegram bot probe failed: {exc}"}
    except json.JSONDecodeError as exc:
        return {"status": "fail", "detail": f"telegram bot probe returned invalid JSON: {exc}"}

    if not isinstance(payload, dict) or payload.get("ok") is not True or not isinstance(payload.get("result"), dict):
        return {"status": "fail", "detail": "telegram bot probe returned an invalid payload."}

    result = payload["result"]
    return {
        "status": "pass",
        "detail": f"Telegram bot @{result.get('username') or 'unknown'} responded to getMe.",
        "bot_id": result.get("id"),
        "bot_username": result.get("username"),
        "bot_name": result.get("first_name"),
    }


def _start_live_auth_session(
    *,
    api_base: str,
    redirect_uri: str,
    timeout_seconds: float,
) -> tuple[requests.Session, dict[str, object], dict[str, object]]:
    session = requests.Session()
    auth_start = session.post(
        f"{api_base}/v1/auth/openai/start",
        json={
            "redirect_uri": redirect_uri,
            "device_label": "live operator validation",
            "platform": "web",
        },
        timeout=timeout_seconds,
    )
    auth_start.raise_for_status()
    start_payload = auth_start.json()

    auth_session = session.get(f"{api_base}/v1/auth/session", timeout=timeout_seconds)
    auth_session.raise_for_status()
    return session, start_payload, auth_session.json()


def _poll_live_auth_state(
    session: requests.Session,
    *,
    api_base: str,
    wait_seconds: float,
    poll_interval_seconds: float,
    timeout_seconds: float,
) -> str:
    deadline = time.time() + max(wait_seconds, 0.0)
    last_state = "unknown"
    while True:
        response = session.get(f"{api_base}/v1/auth/session", timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        raw_state = payload.get("auth_state")
        last_state = raw_state if isinstance(raw_state, str) else "unknown"
        if last_state in {"active", "reauth_required"}:
            return last_state
        if time.time() >= deadline:
            return last_state
        time.sleep(max(poll_interval_seconds, 0.1))


def run_live_provider_validation(
    env: dict[str, str] | None = None,
    *,
    wait_seconds: float = 0.0,
    poll_interval_seconds: float = 2.0,
    request_timeout_seconds: float = 15.0,
) -> dict[str, object]:
    preflight = build_live_provider_preflight(env)
    report = {
        "status": "blocked" if preflight["blockers"] else "not_attempted",
        "attempted": False,
        "manual_browser_step_required": True,
        "api_base": preflight["validation_api_base"],
        "public_base_url": preflight["public_base_url"],
        "redirect_uri": preflight["redirect_uri"],
        "wait_seconds": wait_seconds,
        "poll_interval_seconds": poll_interval_seconds,
        "blockers": list(preflight["blockers"]),
        "warnings": list(preflight["warnings"]),
        "checks": [],
        "manual_steps": [
            "Open the provider authorization URL printed by this script in a real browser.",
            "Complete provider login/consent and let the callback reach the configured public base URL.",
            "Keep the process running or re-run it with a non-zero --live-provider-wait-seconds value to observe auth_state=active.",
        ],
    }
    if preflight["blockers"]:
        return report

    try:
        session, auth_start_payload, auth_session_payload = _start_live_auth_session(
            api_base=str(preflight["validation_api_base"]),
            redirect_uri=str(preflight["redirect_uri"]),
            timeout_seconds=request_timeout_seconds,
        )
    except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError) as exc:
        report["status"] = "fail"
        report["attempted"] = True
        report["blockers"].append(f"failed to bootstrap live provider validation session: {exc}")
        return report

    authorization_url = auth_start_payload.get("authorization_url")
    if not isinstance(authorization_url, str) or not authorization_url:
        report["status"] = "fail"
        report["attempted"] = True
        report["blockers"].append("live provider validation start route did not return an authorization URL.")
        return report

    report["attempted"] = True
    report["_operator_authorization_url"] = authorization_url
    report["authorization_url_preview"] = _redact_url(authorization_url)
    report["authorization_state"] = auth_start_payload.get("state")
    report["session_cookie_present"] = bool(session.cookies)
    report["auth_state_before_wait"] = auth_session_payload.get("auth_state")
    report["checks"].append(
        {
            "check": "live_auth_start",
            "detail": "live auth start returned a real provider authorization URL and session cookie.",
        }
    )

    provider_probe = _probe_provider_authorization_url(authorization_url, timeout_seconds=request_timeout_seconds)
    report["provider_authorization_probe"] = provider_probe
    if provider_probe["status"] != "pass":
        report["status"] = "fail"
        report["blockers"].append(str(provider_probe["detail"]))
        return report
    report["checks"].append(
        {
            "check": "provider_authorization_probe",
            "detail": str(provider_probe["detail"]),
        }
    )

    try:
        final_auth_state = _poll_live_auth_state(
            session,
            api_base=str(preflight["validation_api_base"]),
            wait_seconds=wait_seconds,
            poll_interval_seconds=poll_interval_seconds,
            timeout_seconds=request_timeout_seconds,
        )
    except (requests.RequestException, json.JSONDecodeError) as exc:
        report["status"] = "fail"
        report["blockers"].append(f"failed while polling live provider auth session state: {exc}")
        return report

    report["auth_state_after_wait"] = final_auth_state
    if final_auth_state == "active":
        report["status"] = "pass"
        report["manual_browser_step_required"] = False
        report["checks"].append(
            {
                "check": "live_auth_callback",
                "detail": "provider callback completed and the live auth session became active.",
            }
        )
    elif final_auth_state == "reauth_required":
        report["status"] = "fail"
        report["blockers"].append("provider callback returned an error and the auth session became reauth_required.")
    else:
        report["status"] = "manual-step-required"
        report["warnings"].append(
            "live provider auth remains pending_consent; complete the browser step or verify that the public callback URL is reachable."
        )
    return report


def run_live_telegram_validation(
    env: dict[str, str] | None = None,
    *,
    wait_seconds: float = 0.0,
    poll_interval_seconds: float = 2.0,
    request_timeout_seconds: float = 15.0,
) -> dict[str, object]:
    environment = env or os.environ
    preflight = build_live_telegram_preflight(environment)
    report = {
        "status": "blocked" if preflight["blockers"] else "not_attempted",
        "attempted": False,
        "manual_step_required": True,
        "api_base": preflight["validation_api_base"],
        "public_base_url": preflight["public_base_url"],
        "redirect_uri": preflight["redirect_uri"],
        "telegram_mode": preflight["telegram_mode"],
        "telegram_api_base_url": preflight["telegram_api_base_url"],
        "wait_seconds": wait_seconds,
        "poll_interval_seconds": poll_interval_seconds,
        "blockers": list(preflight["blockers"]),
        "warnings": list(preflight["warnings"]),
        "checks": [],
        "manual_steps": [
            "Open the Telegram deep link printed by this script from a real Telegram account.",
            "Make sure the live runtime is running the Telegram polling transport while this validation waits.",
            "After linking succeeds, re-run the script or keep it running until the link state becomes linked.",
        ],
    }
    if preflight["blockers"]:
        return report

    bot_probe = _probe_telegram_bot_identity(
        telegram_api_base_url=str(preflight["telegram_api_base_url"]),
        bot_token=str(environment.get("ASSISTANT_API_TELEGRAM_BOT_TOKEN")),
        timeout_seconds=request_timeout_seconds,
    )
    report["bot_probe"] = bot_probe
    if bot_probe["status"] != "pass":
        report["status"] = "fail"
        report["attempted"] = True
        report["blockers"].append(str(bot_probe["detail"]))
        return report

    configured_bot_username = environment.get("ASSISTANT_API_TELEGRAM_BOT_USERNAME")
    actual_bot_username = bot_probe.get("bot_username")
    if configured_bot_username and actual_bot_username and configured_bot_username.lstrip("@") != str(actual_bot_username).lstrip("@"):
        report["status"] = "fail"
        report["attempted"] = True
        report["blockers"].append(
            "ASSISTANT_API_TELEGRAM_BOT_USERNAME does not match the username returned by Telegram getMe."
        )
        return report

    try:
        session, _, auth_session_payload = _start_live_auth_session(
            api_base=str(preflight["validation_api_base"]),
            redirect_uri=str(preflight["redirect_uri"]),
            timeout_seconds=request_timeout_seconds,
        )
    except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError) as exc:
        report["status"] = "fail"
        report["attempted"] = True
        report["blockers"].append(f"failed to bootstrap the live Telegram validation session: {exc}")
        return report

    report["attempted"] = True
    report["auth_state_for_link_bootstrap"] = auth_session_payload.get("auth_state")
    report["checks"].append(
        {
            "check": "telegram_bot_probe",
            "detail": str(bot_probe["detail"]),
        }
    )
    report["checks"].append(
        {
            "check": "telegram_link_session_bootstrap",
            "detail": "live auth start created a session that can request a Telegram deep link.",
        }
    )

    try:
        link_start = session.post(
            f"{preflight['validation_api_base']}/v1/surfaces/telegram/link",
            timeout=request_timeout_seconds,
        )
        link_start.raise_for_status()
        link_payload = link_start.json()
    except (requests.RequestException, json.JSONDecodeError) as exc:
        report["status"] = "fail"
        report["blockers"].append(f"failed to request a live Telegram deep link: {exc}")
        return report

    bot_deep_link = link_payload.get("bot_deep_link")
    if not isinstance(bot_deep_link, str) or not bot_deep_link:
        report["status"] = "fail"
        report["blockers"].append("live Telegram link start did not return a bot deep link.")
        return report

    report["_operator_bot_deep_link"] = bot_deep_link
    report["bot_deep_link_preview"] = _redact_url(bot_deep_link)
    report["link_expires_at"] = link_payload.get("expires_at")
    report["telegram_link_status_before_wait"] = link_payload.get("status")
    report["checks"].append(
        {
            "check": "telegram_link_start",
            "detail": "live Telegram link state entered pending and returned a bot deep link.",
        }
    )

    final_link_payload = link_payload
    deadline = time.time() + max(wait_seconds, 0.0)
    while wait_seconds > 0 and time.time() <= deadline:
        try:
            link_state_response = session.get(
                f"{preflight['validation_api_base']}/v1/surfaces/telegram/link",
                timeout=request_timeout_seconds,
            )
            link_state_response.raise_for_status()
            final_link_payload = link_state_response.json()
        except (requests.RequestException, json.JSONDecodeError) as exc:
            report["status"] = "fail"
            report["blockers"].append(f"failed while polling live Telegram link state: {exc}")
            return report
        if final_link_payload.get("status") == "linked":
            break
        time.sleep(max(poll_interval_seconds, 0.1))

    report["telegram_link_status_after_wait"] = final_link_payload.get("status")
    report["linked_telegram_username"] = final_link_payload.get("telegram_username")
    report["linked_at"] = final_link_payload.get("linked_at")
    report["last_event_at"] = final_link_payload.get("last_event_at")
    report["last_error_code"] = final_link_payload.get("last_error_code")
    report["last_error_message"] = final_link_payload.get("last_error_message")

    if final_link_payload.get("status") != "linked":
        report["status"] = "manual-step-required"
        report["warnings"].append(
            "live Telegram link state is still pending; open the deep link from Telegram and verify the polling transport is running."
        )
        return report

    try:
        checkpoint_response = session.get(
            f"{preflight['validation_api_base']}/v1/checkpoints/current",
            timeout=request_timeout_seconds,
        )
        checkpoint_response.raise_for_status()
        checkpoint_payload = checkpoint_response.json()
    except (requests.RequestException, json.JSONDecodeError) as exc:
        report["status"] = "fail"
        report["blockers"].append(f"live Telegram link completed but checkpoint validation failed: {exc}")
        return report

    report["checkpoint_surface"] = checkpoint_payload.get("surface")
    report["checkpoint_handoff_kind"] = checkpoint_payload.get("handoff_kind")
    report["checkpoint_resume_token_ref"] = checkpoint_payload.get("resume_token_ref")
    if checkpoint_payload.get("surface") != "telegram" or checkpoint_payload.get("handoff_kind") != "resume_link":
        report["status"] = "fail"
        report["blockers"].append("live Telegram link did not produce the expected resume_link checkpoint.")
        return report

    report["status"] = "pass"
    report["manual_step_required"] = False
    report["checks"].append(
        {
            "check": "telegram_link_complete",
            "detail": "the live Telegram runtime linked the account and wrote resume-link checkpoint metadata.",
        }
    )
    return report
