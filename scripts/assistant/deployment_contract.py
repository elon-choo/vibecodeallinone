#!/usr/bin/env python3
"""Operator-mode and managed quickstart deployment contract helpers."""

from __future__ import annotations

import argparse
import json
import os
from urllib.parse import urlsplit

SELF_HOST_OPERATOR_MODE = "self-host"
MANAGED_QUICKSTART_OPERATOR_MODE = "managed-quickstart"
SUPPORTED_OPERATOR_MODES = (
    SELF_HOST_OPERATOR_MODE,
    MANAGED_QUICKSTART_OPERATOR_MODE,
)

MANAGED_REQUIRED_ENV = (
    "ASSISTANT_API_PUBLIC_BASE_URL",
    "ASSISTANT_API_WEB_ALLOWED_ORIGINS",
    "ASSISTANT_API_PROVIDER_CLIENT_ID",
    "ASSISTANT_API_PROVIDER_AUTH_URL",
    "ASSISTANT_API_PROVIDER_TOKEN_URL",
)

MANAGED_SECRET_ENV = (
    "ASSISTANT_API_PROVIDER_CLIENT_SECRET",
    "ASSISTANT_API_TELEGRAM_BOT_TOKEN",
)

MANAGED_RECOMMENDED_ENV = (
    "ASSISTANT_API_PROVIDER_USERINFO_URL",
    "ASSISTANT_API_TELEGRAM_BOT_USERNAME",
    "ASSISTANT_API_TELEGRAM_BOT_LINK_BASE_URL",
)
PLACEHOLDER_MARKERS = ("replace-me", "example.com", "example.org", "example.net", ".invalid", "placeholder")


def _env_bool(name: str, default: bool, env: dict[str, str]) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _normalize_operator_mode(raw: str | None) -> str:
    if raw is None or not raw.strip():
        return SELF_HOST_OPERATOR_MODE

    normalized = raw.strip().lower()
    aliases = {
        "self_host": SELF_HOST_OPERATOR_MODE,
        "selfhost": SELF_HOST_OPERATOR_MODE,
        "local": SELF_HOST_OPERATOR_MODE,
        "managed": MANAGED_QUICKSTART_OPERATOR_MODE,
        "managed_quickstart": MANAGED_QUICKSTART_OPERATOR_MODE,
        "managed-quickstart": MANAGED_QUICKSTART_OPERATOR_MODE,
        "hosted": MANAGED_QUICKSTART_OPERATOR_MODE,
    }
    return aliases.get(normalized, normalized)


def _is_https_public_url(value: str) -> bool:
    if not value:
        return False

    parts = urlsplit(value)
    if parts.scheme != "https":
        return False

    hostname = (parts.hostname or "").lower()
    return hostname not in {"127.0.0.1", "localhost"}


def _split_origins(value: str) -> tuple[str, ...]:
    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


def _looks_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return False
    return any(marker in normalized for marker in PLACEHOLDER_MARKERS)


def _build_self_host_surface(env: dict[str, str]) -> dict[str, object]:
    warnings: list[str] = []
    provider_mode = env.get("ASSISTANT_API_PROVIDER_MODE", "mock")

    if provider_mode != "mock":
        warnings.append(
            "self-host operator mode is active; local bootstrap still works, but auth now depends on the configured OIDC provider."
        )

    return {
        "selected": True,
        "status": "self-host-ready",
        "summary": "self-host reference stack defaults are active on the shared assistant runtime path.",
        "warnings": warnings,
        "blockers": [],
    }


def _build_managed_surface(env: dict[str, str], *, selected: bool) -> dict[str, object]:
    blockers: list[str] = []
    warnings: list[str] = []

    provider_mode = env.get("ASSISTANT_API_PROVIDER_MODE", "mock")
    public_base_url = env.get("ASSISTANT_API_PUBLIC_BASE_URL", "")
    allowed_origins = _split_origins(env.get("ASSISTANT_API_WEB_ALLOWED_ORIGINS", ""))
    telegram_mode = env.get("ASSISTANT_RUNTIME_TELEGRAM_MODE", "auto").strip().lower() or "auto"

    for name in MANAGED_REQUIRED_ENV:
        value = env.get(name, "")
        if not value:
            blockers.append(f"{name} is not set.")
        elif _looks_placeholder(value):
            blockers.append(f"{name} still contains a placeholder value and must be replaced for managed quickstart.")

    if provider_mode != "oidc":
        blockers.append("ASSISTANT_API_PROVIDER_MODE must be set to 'oidc' for managed quickstart.")

    if not _env_bool("ASSISTANT_API_SECURE_COOKIES", False, env):
        blockers.append("ASSISTANT_API_SECURE_COOKIES must be true for managed quickstart.")

    if public_base_url and not _is_https_public_url(public_base_url):
        blockers.append("ASSISTANT_API_PUBLIC_BASE_URL must be an HTTPS public URL for managed quickstart.")

    if not allowed_origins:
        blockers.append("ASSISTANT_API_WEB_ALLOWED_ORIGINS must include the managed web origin.")
    else:
        invalid_origins = [origin for origin in allowed_origins if not _is_https_public_url(origin)]
        if invalid_origins:
            blockers.append(
                "ASSISTANT_API_WEB_ALLOWED_ORIGINS must contain only HTTPS public origins for managed quickstart."
            )
        elif any(_looks_placeholder(origin) for origin in allowed_origins):
            blockers.append(
                "ASSISTANT_API_WEB_ALLOWED_ORIGINS still contains placeholder origins and must be replaced for managed quickstart."
            )

    if env.get("ASSISTANT_API_RELEASE_CHANNEL") != MANAGED_QUICKSTART_OPERATOR_MODE:
        warnings.append("ASSISTANT_API_RELEASE_CHANNEL should be set to 'managed-quickstart'.")

    if not env.get("ASSISTANT_API_PROVIDER_USERINFO_URL"):
        warnings.append(
            "ASSISTANT_API_PROVIDER_USERINFO_URL is not set. Identity resolution then depends on an id_token with a stable subject claim."
        )
    elif _looks_placeholder(env["ASSISTANT_API_PROVIDER_USERINFO_URL"]):
        warnings.append(
            "ASSISTANT_API_PROVIDER_USERINFO_URL still looks like a placeholder and should be replaced before live validation."
        )

    if telegram_mode in {"enabled", "true", "1", "yes", "on"}:
        if not env.get("ASSISTANT_API_TELEGRAM_BOT_TOKEN"):
            blockers.append(
                "ASSISTANT_RUNTIME_TELEGRAM_MODE=enabled requires ASSISTANT_API_TELEGRAM_BOT_TOKEN for managed quickstart."
            )
    elif telegram_mode == "auto" and not env.get("ASSISTANT_API_TELEGRAM_BOT_TOKEN"):
        warnings.append(
            "Telegram companion stays auto-disabled until ASSISTANT_API_TELEGRAM_BOT_TOKEN is configured."
        )

    if env.get("ASSISTANT_API_TELEGRAM_BOT_TOKEN") and not (
        env.get("ASSISTANT_API_TELEGRAM_BOT_USERNAME") or env.get("ASSISTANT_API_TELEGRAM_BOT_LINK_BASE_URL")
    ):
        warnings.append(
            "Set ASSISTANT_API_TELEGRAM_BOT_USERNAME or ASSISTANT_API_TELEGRAM_BOT_LINK_BASE_URL so web surfaces can render deep-link instructions."
        )

    return {
        "selected": selected,
        "status": "managed-ready" if selected and not blockers else "managed-blocked" if selected else "not-selected",
        "summary": (
            "managed quickstart contract is selected on top of the shared assistant runtime path."
            if selected
            else "managed quickstart contract is defined but not selected in this runtime workspace."
        ),
        "warnings": warnings,
        "blockers": blockers,
        "required_env": list(MANAGED_REQUIRED_ENV),
        "required_secrets": list(MANAGED_SECRET_ENV),
        "recommended_env": list(MANAGED_RECOMMENDED_ENV),
    }


def build_operator_mode_contract(env: dict[str, str] | None = None) -> dict[str, object]:
    environment = env or os.environ
    operator_mode = _normalize_operator_mode(environment.get("ASSISTANT_RUNTIME_OPERATOR_MODE"))
    if operator_mode not in SUPPORTED_OPERATOR_MODES:
        return {
            "operator_mode": operator_mode,
            "runtime_path": "reference-stack",
            "shared_runtime_components": ["assistant-api", "assistant-web", "worker", "telegram"],
            "status": "invalid",
            "summary": "operator mode is not recognized.",
            "blockers": [
                "ASSISTANT_RUNTIME_OPERATOR_MODE must be one of: self-host, managed-quickstart."
            ],
            "warnings": [],
            "self_host": _build_self_host_surface(environment),
            "managed_quickstart": _build_managed_surface(environment, selected=False),
        }

    self_host = _build_self_host_surface(environment)
    managed = _build_managed_surface(environment, selected=operator_mode == MANAGED_QUICKSTART_OPERATOR_MODE)

    if operator_mode == SELF_HOST_OPERATOR_MODE:
        status = self_host["status"]
        summary = self_host["summary"]
        blockers = list(self_host["blockers"])
        warnings = list(self_host["warnings"])
    else:
        status = managed["status"]
        summary = managed["summary"]
        blockers = list(managed["blockers"])
        warnings = list(managed["warnings"])

    return {
        "operator_mode": operator_mode,
        "contract_version": "2026-03-10",
        "runtime_path": "reference-stack",
        "shared_runtime_components": ["assistant-api", "assistant-web", "worker", "telegram"],
        "status": status,
        "summary": summary,
        "blockers": blockers,
        "warnings": warnings,
        "self_host": self_host,
        "managed_quickstart": managed,
    }


def _render_status(contract: dict[str, object]) -> str:
    lines = [
        f"operator-mode: {contract['operator_mode']}",
        f"deployment-readiness: {contract['status']}",
        f"deployment-summary: {contract['summary']}",
    ]
    for blocker in contract["blockers"]:
        lines.append(f"deployment-blocker: {blocker}")
    for warning in contract["warnings"]:
        lines.append(f"deployment-warning: {warning}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=("json", "status"),
        default="json",
        help="Output format.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = build_operator_mode_contract()
    if args.format == "status":
        print(_render_status(contract))
    else:
        print(json.dumps(contract, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
