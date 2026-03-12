"""Configuration for the assistant-api bootstrap runtime."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SERVICE_ROOT = Path(__file__).resolve().parents[1]


def _read_package_version(repo_root: Path) -> str:
    package_json = repo_root / "package.json"
    if not package_json.exists():
        return "0.0.0-dev"

    import json

    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "0.0.0-dev"

    version = payload.get("version")
    if isinstance(version, str) and version.strip():
        return version
    return "0.0.0-dev"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None:
        return default
    values = tuple(value.strip() for value in raw.split(",") if value.strip())
    return values or default


@dataclass(frozen=True, slots=True)
class Settings:
    repo_root: Path
    artifacts_dir: Path
    db_path: Path
    migration_path: Path
    app_version: str
    release_channel: str
    cookie_name: str
    assistant_api_public_base_url: str
    web_allowed_origins: tuple[str, ...]
    provider_mode: str
    provider_client_id: str
    provider_client_secret: str | None
    provider_token_url: str | None
    provider_userinfo_url: str | None
    provider_scopes: tuple[str, ...]
    provider_authorization_base_url: str
    telegram_bot_token: str | None
    telegram_bot_username: str | None
    telegram_bot_deep_link_base_url: str | None
    telegram_api_base_url: str
    telegram_link_ttl_seconds: int
    telegram_poll_timeout_seconds: int
    memory_delete_retention_seconds: int
    worker_poll_interval_seconds: float
    worker_job_lease_seconds: int
    secure_cookies: bool
    session_ttl_seconds: int

    @classmethod
    def from_env(cls) -> Settings:
        repo_root = Path(os.getenv("ASSISTANT_API_REPO_ROOT", PROJECT_ROOT)).resolve()
        service_root = Path(os.getenv("ASSISTANT_API_SERVICE_ROOT", SERVICE_ROOT)).resolve()
        return cls(
            repo_root=repo_root,
            artifacts_dir=Path(os.getenv("ASSISTANT_API_ARTIFACTS_DIR", repo_root / "artifacts")).resolve(),
            db_path=Path(os.getenv("ASSISTANT_API_DB_PATH", service_root / "data" / "assistant_api.sqlite3")).resolve(),
            migration_path=Path(os.getenv("ASSISTANT_API_MIGRATION_PATH", service_root / "migrations" / "0001_bootstrap.sql")).resolve(),
            app_version=os.getenv("ASSISTANT_API_APP_VERSION", _read_package_version(repo_root)),
            release_channel=os.getenv("ASSISTANT_API_RELEASE_CHANNEL", "internal"),
            cookie_name=os.getenv("ASSISTANT_API_COOKIE_NAME", "assistant_session"),
            assistant_api_public_base_url=os.getenv("ASSISTANT_API_PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
            web_allowed_origins=_env_list(
                "ASSISTANT_API_WEB_ALLOWED_ORIGINS",
                (
                    "http://127.0.0.1:4173",
                    "http://localhost:4173",
                    "http://127.0.0.1:3000",
                    "http://localhost:3000",
                ),
            ),
            provider_mode=os.getenv("ASSISTANT_API_PROVIDER_MODE", "mock"),
            provider_client_id=os.getenv("ASSISTANT_API_PROVIDER_CLIENT_ID", "assistant-bootstrap-client"),
            provider_client_secret=os.getenv("ASSISTANT_API_PROVIDER_CLIENT_SECRET"),
            provider_token_url=os.getenv("ASSISTANT_API_PROVIDER_TOKEN_URL"),
            provider_userinfo_url=os.getenv("ASSISTANT_API_PROVIDER_USERINFO_URL"),
            provider_scopes=_env_list(
                "ASSISTANT_API_PROVIDER_SCOPES",
                ("openid", "profile", "email", "offline_access"),
            ),
            provider_authorization_base_url=os.getenv(
                "ASSISTANT_API_PROVIDER_AUTH_URL",
                "https://auth.openai.com/oauth/authorize",
            ),
            telegram_bot_token=os.getenv("ASSISTANT_API_TELEGRAM_BOT_TOKEN") or None,
            telegram_bot_username=os.getenv("ASSISTANT_API_TELEGRAM_BOT_USERNAME") or None,
            telegram_bot_deep_link_base_url=os.getenv("ASSISTANT_API_TELEGRAM_BOT_LINK_BASE_URL") or None,
            telegram_api_base_url=os.getenv("ASSISTANT_API_TELEGRAM_API_BASE_URL", "https://api.telegram.org").rstrip(
                "/"
            ),
            telegram_link_ttl_seconds=int(os.getenv("ASSISTANT_API_TELEGRAM_LINK_TTL_SECONDS", "900")),
            telegram_poll_timeout_seconds=int(os.getenv("ASSISTANT_API_TELEGRAM_POLL_TIMEOUT_SECONDS", "30")),
            memory_delete_retention_seconds=int(
                os.getenv("ASSISTANT_API_MEMORY_DELETE_RETENTION_SECONDS", "604800")
            ),
            worker_poll_interval_seconds=float(os.getenv("ASSISTANT_API_WORKER_POLL_INTERVAL_SECONDS", "2")),
            worker_job_lease_seconds=int(os.getenv("ASSISTANT_API_WORKER_JOB_LEASE_SECONDS", "30")),
            secure_cookies=_env_bool("ASSISTANT_API_SECURE_COOKIES", False),
            session_ttl_seconds=int(os.getenv("ASSISTANT_API_SESSION_TTL_SECONDS", "2592000")),
        )

    def require_telegram_bot_token(self) -> str:
        if self.telegram_bot_token is None:
            raise ValueError("ASSISTANT_API_TELEGRAM_BOT_TOKEN is required for Telegram transport")
        return self.telegram_bot_token
