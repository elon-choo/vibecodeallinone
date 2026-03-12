"""Provider adapter for the assistant-api auth bootstrap."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import Settings


class ProviderExchangeError(RuntimeError):
    """Raised when provider authorization cannot be completed."""


@dataclass(frozen=True, slots=True)
class ProviderIdentity:
    provider_subject: str
    scopes: tuple[str, ...]
    display_name: str | None = None
    email: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderTokenBundle:
    access_token: str
    token_type: str
    scopes: tuple[str, ...]
    refresh_token: str | None = None
    expires_in: int | None = None
    id_token: str | None = None

    def to_token_ref(self) -> str:
        return json.dumps(
            {
                "access_token": self.access_token,
                "token_type": self.token_type,
                "refresh_token": self.refresh_token,
                "expires_in": self.expires_in,
                "id_token": self.id_token,
                "scope": list(self.scopes),
            },
            sort_keys=True,
        )


def generate_pkce_pair() -> tuple[str, str]:
    code_verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return code_verifier, code_challenge


class OpenAiProviderAdapter:
    """Builds auth URLs and exchanges callback codes for provider identity."""

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def callback_url(self) -> str:
        return f"{self.settings.assistant_api_public_base_url}/v1/auth/openai/callback"

    def build_authorization_url(self, *, state: str, code_challenge: str) -> str:
        if self.settings.provider_mode == "mock":
            query = urlencode(
                {
                    "state": state,
                    "redirect_uri": self.callback_url,
                    "scope": " ".join(self.settings.provider_scopes),
                }
            )
            return f"{self.settings.assistant_api_public_base_url}/v1/auth/openai/mock/authorize?{query}"

        params = {
            "client_id": self.settings.provider_client_id,
            "redirect_uri": self.callback_url,
            "response_type": "code",
            "response_mode": "query",
            "scope": " ".join(self.settings.provider_scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.settings.provider_authorization_base_url}?{urlencode(params)}"

    def exchange_code(self, *, code: str, code_verifier: str) -> tuple[ProviderIdentity, ProviderTokenBundle]:
        if self.settings.provider_mode == "mock" or code.startswith("mock_"):
            return self._exchange_mock_code(code)

        token_payload = self._exchange_oidc_code(code=code, code_verifier=code_verifier)
        access_token = token_payload.get("access_token")
        token_type = token_payload.get("token_type", "bearer")
        if not isinstance(access_token, str) or not access_token:
            raise ProviderExchangeError("provider token response missing access_token")

        scopes = self._normalize_scopes(token_payload.get("scope"))
        identity = self._resolve_identity(token_payload, access_token, scopes)
        token_bundle = ProviderTokenBundle(
            access_token=access_token,
            token_type=token_type,
            refresh_token=token_payload.get("refresh_token"),
            expires_in=self._coerce_int(token_payload.get("expires_in")),
            id_token=token_payload.get("id_token"),
            scopes=identity.scopes,
        )
        return identity, token_bundle

    def _exchange_mock_code(self, code: str) -> tuple[ProviderIdentity, ProviderTokenBundle]:
        suffix = code.removeprefix("mock_") or "bootstrap"
        identity = ProviderIdentity(
            provider_subject=f"openai-mock:{suffix}",
            scopes=self.settings.provider_scopes,
            display_name="Mock OpenAI User",
            email=f"{suffix[:12]}@openai.local",
        )
        token_bundle = ProviderTokenBundle(
            access_token=f"mock_access_{suffix}",
            token_type="bearer",
            refresh_token=f"mock_refresh_{suffix}",
            expires_in=3600,
            id_token=None,
            scopes=self.settings.provider_scopes,
        )
        return identity, token_bundle

    def _exchange_oidc_code(self, *, code: str, code_verifier: str) -> dict[str, Any]:
        if not self.settings.provider_token_url:
            raise ProviderExchangeError("provider token endpoint is not configured")

        form_data: dict[str, str] = {
            "grant_type": "authorization_code",
            "client_id": self.settings.provider_client_id,
            "code": code,
            "redirect_uri": self.callback_url,
            "code_verifier": code_verifier,
        }
        if self.settings.provider_client_secret:
            form_data["client_secret"] = self.settings.provider_client_secret

        request = Request(
            self.settings.provider_token_url,
            data=urlencode(form_data).encode("utf-8"),
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        return self._read_json_response(request)

    def _resolve_identity(
        self,
        token_payload: dict[str, Any],
        access_token: str,
        fallback_scopes: tuple[str, ...],
    ) -> ProviderIdentity:
        if self.settings.provider_userinfo_url:
            request = Request(
                self.settings.provider_userinfo_url,
                method="GET",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
            )
            payload = self._read_json_response(request)
            provider_subject = payload.get("sub")
            if isinstance(provider_subject, str) and provider_subject:
                return ProviderIdentity(
                    provider_subject=provider_subject,
                    scopes=fallback_scopes,
                    display_name=self._first_string(payload, "name", "preferred_username"),
                    email=self._first_string(payload, "email"),
                )

        claims = self._parse_unverified_jwt_claims(token_payload.get("id_token"))
        provider_subject = claims.get("sub")
        if not isinstance(provider_subject, str) or not provider_subject:
            raise ProviderExchangeError("provider identity response missing subject claim")
        return ProviderIdentity(
            provider_subject=provider_subject,
            scopes=fallback_scopes,
            display_name=self._first_string(claims, "name", "preferred_username"),
            email=self._first_string(claims, "email"),
        )

    def _read_json_response(self, request: Request) -> dict[str, Any]:
        try:
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ProviderExchangeError(f"provider HTTP error {exc.code}: {body}") from exc
        except URLError as exc:
            raise ProviderExchangeError(f"provider network error: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise ProviderExchangeError("provider response was not valid JSON") from exc

        if not isinstance(payload, dict):
            raise ProviderExchangeError("provider response must be a JSON object")
        return payload

    @staticmethod
    def _normalize_scopes(raw_scope: Any) -> tuple[str, ...]:
        if isinstance(raw_scope, str):
            return tuple(scope for scope in raw_scope.split() if scope)
        if isinstance(raw_scope, list):
            return tuple(scope for scope in raw_scope if isinstance(scope, str) and scope)
        return ()

    @staticmethod
    def _parse_unverified_jwt_claims(token: Any) -> dict[str, Any]:
        if not isinstance(token, str) or token.count(".") < 2:
            return {}
        parts = token.split(".")
        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        try:
            decoded = base64.urlsafe_b64decode(payload + padding).decode("utf-8")
            claims = json.loads(decoded)
        except (ValueError, json.JSONDecodeError):
            return {}
        return claims if isinstance(claims, dict) else {}

    @staticmethod
    def _first_string(payload: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None
