from __future__ import annotations

from scripts.assistant.deployment_contract import (
    MANAGED_QUICKSTART_OPERATOR_MODE,
    SELF_HOST_OPERATOR_MODE,
    build_operator_mode_contract,
)


def test_self_host_contract_defaults_to_ready() -> None:
    contract = build_operator_mode_contract(
        {
            "ASSISTANT_API_PROVIDER_MODE": "mock",
            "ASSISTANT_API_PUBLIC_BASE_URL": "http://127.0.0.1:8000",
            "ASSISTANT_API_WEB_ALLOWED_ORIGINS": "http://127.0.0.1:4173",
            "ASSISTANT_RUNTIME_TELEGRAM_MODE": "auto",
        }
    )

    assert contract["operator_mode"] == SELF_HOST_OPERATOR_MODE
    assert contract["status"] == "self-host-ready"
    assert contract["blockers"] == []
    assert "shared assistant runtime path" in contract["summary"]


def test_managed_quickstart_contract_blocks_insecure_or_missing_inputs() -> None:
    contract = build_operator_mode_contract(
        {
            "ASSISTANT_RUNTIME_OPERATOR_MODE": MANAGED_QUICKSTART_OPERATOR_MODE,
            "ASSISTANT_API_PROVIDER_MODE": "mock",
            "ASSISTANT_API_PUBLIC_BASE_URL": "http://localhost:8000",
            "ASSISTANT_API_WEB_ALLOWED_ORIGINS": "http://localhost:4173",
            "ASSISTANT_API_SECURE_COOKIES": "false",
            "ASSISTANT_RUNTIME_TELEGRAM_MODE": "enabled",
        }
    )

    assert contract["status"] == "managed-blocked"
    assert "ASSISTANT_API_PROVIDER_MODE must be set to 'oidc' for managed quickstart." in contract["blockers"]
    assert "ASSISTANT_API_SECURE_COOKIES must be true for managed quickstart." in contract["blockers"]
    assert (
        "ASSISTANT_RUNTIME_TELEGRAM_MODE=enabled requires ASSISTANT_API_TELEGRAM_BOT_TOKEN for managed quickstart."
        in contract["blockers"]
    )


def test_managed_quickstart_contract_blocks_placeholder_values() -> None:
    contract = build_operator_mode_contract(
        {
            "ASSISTANT_RUNTIME_OPERATOR_MODE": MANAGED_QUICKSTART_OPERATOR_MODE,
            "ASSISTANT_API_RELEASE_CHANNEL": "managed-quickstart",
            "ASSISTANT_API_PROVIDER_MODE": "oidc",
            "ASSISTANT_API_PUBLIC_BASE_URL": "https://api.example.com",
            "ASSISTANT_API_WEB_ALLOWED_ORIGINS": "https://app.example.com",
            "ASSISTANT_API_PROVIDER_CLIENT_ID": "replace-me",
            "ASSISTANT_API_PROVIDER_AUTH_URL": "https://auth.example.com/authorize",
            "ASSISTANT_API_PROVIDER_TOKEN_URL": "https://auth.example.com/token",
            "ASSISTANT_API_PROVIDER_USERINFO_URL": "https://auth.example.com/userinfo",
            "ASSISTANT_API_SECURE_COOKIES": "true",
            "ASSISTANT_RUNTIME_TELEGRAM_MODE": "auto",
        }
    )

    assert contract["status"] == "managed-blocked"
    assert (
        "ASSISTANT_API_PUBLIC_BASE_URL still contains a placeholder value and must be replaced for managed quickstart."
        in contract["blockers"]
    )
    assert (
        "ASSISTANT_API_PROVIDER_CLIENT_ID still contains a placeholder value and must be replaced for managed quickstart."
        in contract["blockers"]
    )


def test_managed_quickstart_contract_reports_ready_with_required_inputs() -> None:
    contract = build_operator_mode_contract(
        {
            "ASSISTANT_RUNTIME_OPERATOR_MODE": MANAGED_QUICKSTART_OPERATOR_MODE,
            "ASSISTANT_API_RELEASE_CHANNEL": "managed-quickstart",
            "ASSISTANT_API_PROVIDER_MODE": "oidc",
            "ASSISTANT_API_PUBLIC_BASE_URL": "https://api.managed-quickstart.dev",
            "ASSISTANT_API_WEB_ALLOWED_ORIGINS": "https://app.managed-quickstart.dev",
            "ASSISTANT_API_PROVIDER_CLIENT_ID": "client-id",
            "ASSISTANT_API_PROVIDER_AUTH_URL": "https://login.managed-quickstart.dev/authorize",
            "ASSISTANT_API_PROVIDER_TOKEN_URL": "https://login.managed-quickstart.dev/token",
            "ASSISTANT_API_PROVIDER_USERINFO_URL": "https://login.managed-quickstart.dev/userinfo",
            "ASSISTANT_API_SECURE_COOKIES": "true",
            "ASSISTANT_RUNTIME_TELEGRAM_MODE": "auto",
        }
    )

    assert contract["status"] == "managed-ready"
    assert contract["blockers"] == []
    assert contract["managed_quickstart"]["selected"] is True
    assert (
        "Telegram companion stays auto-disabled until ASSISTANT_API_TELEGRAM_BOT_TOKEN is configured."
        in contract["warnings"]
    )
