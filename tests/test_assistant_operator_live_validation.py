from __future__ import annotations

from scripts.assistant.smoke_support import (
    artifact_safe_payload,
    build_live_provider_preflight,
    build_live_telegram_preflight,
    run_live_provider_validation,
    run_live_telegram_validation,
)


def make_live_provider_env() -> dict[str, str]:
    return {
        "ASSISTANT_API_PROVIDER_MODE": "oidc",
        "ASSISTANT_API_PUBLIC_BASE_URL": "https://api.managed-quickstart.dev",
        "ASSISTANT_API_WEB_ALLOWED_ORIGINS": "https://app.managed-quickstart.dev",
        "ASSISTANT_API_PROVIDER_CLIENT_ID": "managed-client-id",
        "ASSISTANT_API_PROVIDER_AUTH_URL": "https://login.managed-quickstart.dev/oauth/authorize",
        "ASSISTANT_API_PROVIDER_TOKEN_URL": "https://login.managed-quickstart.dev/oauth/token",
        "ASSISTANT_API_PROVIDER_USERINFO_URL": "https://login.managed-quickstart.dev/oauth/userinfo",
        "ASSISTANT_API_SECURE_COOKIES": "true",
    }


def test_artifact_safe_payload_strips_private_fields() -> None:
    payload = {
        "status": "manual-step-required",
        "_operator_authorization_url": "https://example.com",
        "nested": {
            "_operator_bot_deep_link": "https://t.me/example?start=abc",
            "keep": "value",
        },
    }

    assert artifact_safe_payload(payload) == {
        "status": "manual-step-required",
        "nested": {"keep": "value"},
    }


def test_live_provider_preflight_accepts_local_validation_override() -> None:
    env = make_live_provider_env()
    env["ASSISTANT_OPERATOR_VALIDATION_API_BASE_URL"] = "http://127.0.0.1:8000"

    preflight = build_live_provider_preflight(env)

    assert preflight["eligible_for_live_validation"] is True
    assert preflight["validation_api_base"] == "http://127.0.0.1:8000"
    assert preflight["redirect_uri"] == "https://app.managed-quickstart.dev/callback"
    assert (
        "ASSISTANT_OPERATOR_VALIDATION_API_BASE_URL overrides the live request target; the public callback URL still comes from ASSISTANT_API_PUBLIC_BASE_URL."
        in preflight["warnings"]
    )


def test_live_provider_preflight_blocks_placeholders() -> None:
    env = {
        "ASSISTANT_API_PROVIDER_MODE": "oidc",
        "ASSISTANT_API_PUBLIC_BASE_URL": "https://api.example.com",
        "ASSISTANT_API_WEB_ALLOWED_ORIGINS": "https://app.example.com",
        "ASSISTANT_API_PROVIDER_CLIENT_ID": "replace-me",
        "ASSISTANT_API_PROVIDER_AUTH_URL": "https://auth.example.com/oauth/authorize",
        "ASSISTANT_API_PROVIDER_TOKEN_URL": "https://auth.example.com/oauth/token",
        "ASSISTANT_API_SECURE_COOKIES": "true",
    }

    preflight = build_live_provider_preflight(env)

    assert preflight["eligible_for_live_validation"] is False
    assert (
        "ASSISTANT_API_PUBLIC_BASE_URL still contains a placeholder value and must be replaced for live provider validation."
        in preflight["blockers"]
    )
    assert (
        "ASSISTANT_API_PROVIDER_CLIENT_ID still contains a placeholder value and must be replaced for live provider validation."
        in preflight["blockers"]
    )


def test_live_telegram_preflight_requires_bot_inputs() -> None:
    env = make_live_provider_env()
    env["ASSISTANT_RUNTIME_TELEGRAM_MODE"] = "auto"

    preflight = build_live_telegram_preflight(env)

    assert preflight["eligible_for_live_validation"] is False
    assert "ASSISTANT_API_TELEGRAM_BOT_TOKEN is required before live Telegram validation can run." in preflight["blockers"]


def test_live_telegram_preflight_accepts_real_bot_config() -> None:
    env = make_live_provider_env()
    env.update(
        {
            "ASSISTANT_RUNTIME_TELEGRAM_MODE": "enabled",
            "ASSISTANT_API_TELEGRAM_BOT_TOKEN": "123456:abc",
            "ASSISTANT_API_TELEGRAM_BOT_USERNAME": "assistant_runtime_bot",
        }
    )

    preflight = build_live_telegram_preflight(env)

    assert preflight["eligible_for_live_validation"] is True
    assert preflight["bot_username"] == "assistant_runtime_bot"
    assert preflight["telegram_mode"] == "enabled"


def test_live_provider_validation_is_blocked_without_required_env() -> None:
    report = run_live_provider_validation({})

    assert report["status"] == "blocked"
    assert report["attempted"] is False
    assert "ASSISTANT_API_PROVIDER_MODE must be set to 'oidc' for live provider validation." in report["blockers"]


def test_live_telegram_validation_is_blocked_without_required_env() -> None:
    report = run_live_telegram_validation({})

    assert report["status"] == "blocked"
    assert report["attempted"] is False
    assert "ASSISTANT_API_TELEGRAM_BOT_TOKEN is required before live Telegram validation can run." in report["blockers"]
