"""FastAPI bootstrap runtime for assistant-api."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from .config import Settings
from .memory_broker import MemoryBrokerBackend, create_memory_broker_backend
from .models import (
    AuthSession,
    CheckpointUpsertRequest,
    JobKind,
    JobStatus,
    MemoryBrokerQueryRequest,
    MemoryBrokerQueryResponse,
    MemoryBrokerWorkspaceListResponse,
    MemoryBrokerWorkspaceState,
    MemoryBrokerWorkspaceUpsertRequest,
    MemoryCreateRequest,
    MemoryDeleteReceipt,
    MemoryExportResponse,
    MemoryItemPatchRequest,
    MemoryItemsResponse,
    MemoryRecord,
    OpenAiStartRequest,
    OpenAiStartResponse,
    ReminderCreateRequest,
    ReminderListResponse,
    ReminderRecord,
    ReminderStatus,
    RuntimeJobsResponse,
    SessionCheckpoint,
    Surface,
    TelegramLinkState,
    TelegramMockLinkCompleteRequest,
    TrustBundleResponse,
    TrustCurrentResponse,
)
from .provider import OpenAiProviderAdapter, ProviderExchangeError
from .store import CheckpointConflictError, SQLiteAssistantStore
from .trust import TrustResolver


def _append_query_params(url: str, updates: dict[str, str]) -> str:
    parts = urlsplit(url)
    current_params = dict(parse_qsl(parts.query, keep_blank_values=True))
    current_params.update(updates)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(current_params), parts.fragment))


def create_app(
    settings: Settings | None = None,
    *,
    memory_broker: MemoryBrokerBackend | None = None,
) -> FastAPI:
    runtime_settings = settings or Settings.from_env()
    store = SQLiteAssistantStore(
        runtime_settings,
        memory_broker=memory_broker or create_memory_broker_backend(),
    )
    store.initialize()
    trust_resolver = TrustResolver(runtime_settings, store)
    provider_adapter = OpenAiProviderAdapter(runtime_settings)

    app = FastAPI(title="Assistant API", version="0.1.0")
    app.state.settings = runtime_settings
    app.state.store = store
    app.state.trust_resolver = trust_resolver
    app.state.provider_adapter = provider_adapter

    if runtime_settings.web_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(runtime_settings.web_allowed_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def session_context_middleware(request: Request, call_next):
        request.state.auth_session = None
        session_cookie = request.cookies.get(runtime_settings.cookie_name)
        if session_cookie:
            auth_session = store.touch_session(session_cookie)
            if auth_session is not None:
                request.state.auth_session = auth_session
        return await call_next(request)

    def require_session(request: Request) -> AuthSession:
        auth_session = request.state.auth_session
        if auth_session is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="assistant session required")
        return auth_session

    @app.post("/v1/auth/openai/start", response_model=OpenAiStartResponse)
    def start_openai_auth(payload: OpenAiStartRequest, response: Response) -> OpenAiStartResponse:
        pending_flow, auth_session = store.start_auth_session(payload)

        response.set_cookie(
            key=runtime_settings.cookie_name,
            value=auth_session.session.session_id,
            httponly=True,
            secure=runtime_settings.secure_cookies,
            samesite="lax",
            max_age=runtime_settings.session_ttl_seconds,
        )
        return OpenAiStartResponse(
            authorization_url=provider_adapter.build_authorization_url(
                state=pending_flow.oauth_state,
                code_challenge=pending_flow.code_challenge,
            ),
            state=pending_flow.oauth_state,
        )

    @app.get("/v1/auth/openai/callback")
    def complete_openai_auth(
        state: str = Query(min_length=8),
        code: str | None = Query(default=None),
        error: str | None = Query(default=None),
        error_description: str | None = Query(default=None),
    ) -> RedirectResponse:
        pending_flow = store.get_pending_auth_flow(state)
        if pending_flow is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="auth state invalid or expired")

        if error is not None:
            store.fail_auth_flow(state)
            redirect_target = _append_query_params(
                pending_flow.redirect_uri,
                {
                    "auth": "error",
                    "provider": "openai",
                    "reason": error,
                    "error_description": error_description or "",
                },
            )
            return RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER)

        if code is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="provider callback missing code")

        try:
            identity, token_bundle = provider_adapter.exchange_code(
                code=code,
                code_verifier=pending_flow.code_verifier,
            )
            auth_session, redirect_uri = store.complete_auth_flow(state, identity, token_bundle)
        except ProviderExchangeError:
            redirect_uri = store.fail_auth_flow(state)
            if redirect_uri is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="auth state invalid or expired") from None
            redirect_target = _append_query_params(
                redirect_uri,
                {
                    "auth": "error",
                    "provider": "openai",
                    "reason": "exchange_failed",
                },
            )
            return RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER)

        if auth_session is None or redirect_uri is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="auth state invalid or expired")

        redirect_target = _append_query_params(
            redirect_uri,
            {
                "auth": "success",
                "provider": "openai",
                "session": auth_session.auth_state.value,
            },
        )
        redirect_response = RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER)
        redirect_response.set_cookie(
            key=runtime_settings.cookie_name,
            value=auth_session.session.session_id,
            httponly=True,
            secure=runtime_settings.secure_cookies,
            samesite="lax",
            max_age=runtime_settings.session_ttl_seconds,
        )
        return redirect_response

    @app.get("/v1/auth/openai/mock/authorize", include_in_schema=False)
    def authorize_openai_mock(
        redirect_uri: str,
        state: str,
        deny: bool = Query(default=False),
    ) -> RedirectResponse:
        if deny:
            return RedirectResponse(
                url=_append_query_params(
                    redirect_uri,
                    {
                        "state": state,
                        "error": "access_denied",
                        "error_description": "mock provider denied access",
                    },
                ),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        return RedirectResponse(
            url=_append_query_params(
                redirect_uri,
                {
                    "state": state,
                    "code": f"mock_{state[:12]}",
                },
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.get("/v1/auth/session", response_model=AuthSession)
    def get_auth_session(request: Request) -> AuthSession:
        return require_session(request)

    @app.get("/v1/surfaces/telegram/link", response_model=TelegramLinkState)
    def get_telegram_link_state(request: Request) -> TelegramLinkState:
        auth_session = require_session(request)
        return store.get_telegram_link_state(auth_session.user_id)

    @app.post("/v1/surfaces/telegram/link", response_model=TelegramLinkState)
    def start_telegram_link(request: Request) -> TelegramLinkState:
        auth_session = require_session(request)
        return store.start_telegram_link(auth_session.user_id)

    @app.post("/v1/internal/test/telegram/link/complete", include_in_schema=False, response_model=TelegramLinkState)
    def complete_mock_telegram_link(
        payload: TelegramMockLinkCompleteRequest,
        request: Request,
    ) -> TelegramLinkState:
        if runtime_settings.provider_mode != "mock":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
        auth_session = require_session(request)
        try:
            return store.complete_mock_telegram_link(
                auth_session.user_id,
                link_code=payload.link_code,
                telegram_user_id=payload.telegram_user_id,
                telegram_chat_id=payload.telegram_chat_id,
                telegram_username=payload.telegram_username,
                telegram_display_name=payload.telegram_display_name,
                last_resume_token_ref=payload.last_resume_token_ref,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/v1/memory/items", response_model=MemoryItemsResponse)
    def list_memory_items(
        request: Request,
        status_filter: str | None = Query(default=None, alias="status"),
        limit: int = Query(default=20, ge=1, le=100),
    ) -> MemoryItemsResponse:
        auth_session = require_session(request)
        return store.list_memory_items(auth_session.user_id, status_filter, limit)

    @app.post("/v1/memory/items", response_model=MemoryRecord, status_code=status.HTTP_201_CREATED)
    def create_memory_item(item: MemoryCreateRequest, request: Request) -> MemoryRecord:
        auth_session = require_session(request)
        try:
            return store.create_memory_item(auth_session.user_id, item)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/v1/memory/broker/workspaces", response_model=MemoryBrokerWorkspaceListResponse)
    def list_memory_broker_workspaces(request: Request) -> MemoryBrokerWorkspaceListResponse:
        auth_session = require_session(request)
        return store.list_memory_broker_workspaces(auth_session.user_id)

    @app.get("/v1/memory/broker/workspaces/{workspace_id}", response_model=MemoryBrokerWorkspaceState)
    def get_memory_broker_workspace_state(
        workspace_id: str,
        request: Request,
    ) -> MemoryBrokerWorkspaceState:
        auth_session = require_session(request)
        try:
            return store.get_memory_broker_workspace(auth_session.user_id, workspace_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.put("/v1/memory/broker/workspaces/{workspace_id}", response_model=MemoryBrokerWorkspaceState)
    def put_memory_broker_workspace_state(
        workspace_id: str,
        payload: MemoryBrokerWorkspaceUpsertRequest,
        request: Request,
    ) -> MemoryBrokerWorkspaceState:
        auth_session = require_session(request)
        try:
            return store.upsert_memory_broker_workspace(auth_session.user_id, workspace_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.post(
        "/v1/memory/broker/workspaces/{workspace_id}/query",
        response_model=MemoryBrokerQueryResponse,
    )
    def query_memory_broker_workspace(
        workspace_id: str,
        payload: MemoryBrokerQueryRequest,
        request: Request,
    ) -> MemoryBrokerQueryResponse:
        auth_session = require_session(request)
        try:
            return store.query_memory_broker_workspace(
                auth_session.user_id,
                auth_session.device_session_id,
                workspace_id,
                payload,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.patch("/v1/memory/items/{memory_id}", response_model=MemoryRecord)
    def patch_memory_item(
        memory_id: str,
        patch: MemoryItemPatchRequest,
        request: Request,
    ) -> MemoryRecord:
        auth_session = require_session(request)
        try:
            memory_item = store.patch_memory_item(auth_session.user_id, memory_id, patch)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if memory_item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="memory item not found")
        return memory_item

    @app.post("/v1/memory/exports", response_model=MemoryExportResponse)
    def export_memory_items(request: Request) -> MemoryExportResponse:
        auth_session = require_session(request)
        return store.create_memory_export(auth_session.user_id, auth_session.device_session_id)

    @app.delete("/v1/memory/items/{memory_id}", response_model=MemoryDeleteReceipt, status_code=status.HTTP_202_ACCEPTED)
    def delete_memory_item(memory_id: str, request: Request) -> MemoryDeleteReceipt:
        auth_session = require_session(request)
        receipt = store.delete_memory_item(auth_session.user_id, auth_session.device_session_id, memory_id)
        if receipt is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="memory item not found")
        return receipt

    @app.get("/v1/checkpoints/current", response_model=SessionCheckpoint)
    def get_current_checkpoint(request: Request) -> SessionCheckpoint:
        auth_session = require_session(request)
        checkpoint = store.get_checkpoint(auth_session.user_id, auth_session.device_session_id)
        if checkpoint is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="checkpoint not found")
        return checkpoint

    @app.put("/v1/checkpoints/current", response_model=SessionCheckpoint)
    def put_current_checkpoint(checkpoint: CheckpointUpsertRequest, request: Request) -> SessionCheckpoint | JSONResponse:
        auth_session = require_session(request)
        try:
            return store.upsert_checkpoint(auth_session.user_id, auth_session.device_session_id, checkpoint)
        except CheckpointConflictError as exc:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=exc.response.model_dump(mode="json"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/v1/reminders", response_model=ReminderListResponse)
    def list_reminders(
        request: Request,
        status_filter: Annotated[ReminderStatus | None, Query(alias="status")] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> ReminderListResponse:
        auth_session = require_session(request)
        return store.list_reminder_deliveries(
            auth_session.user_id,
            status=status_filter,
            limit=limit,
        )

    @app.post("/v1/reminders", response_model=ReminderRecord, status_code=status.HTTP_201_CREATED)
    def create_reminder(payload: ReminderCreateRequest, request: Request) -> ReminderRecord:
        auth_session = require_session(request)
        try:
            return store.schedule_reminder_delivery(
                auth_session.user_id,
                auth_session.device_session_id,
                scheduled_for=payload.scheduled_for,
                payload={"message": payload.message},
                channel=Surface(payload.channel),
                follow_up_policy=payload.follow_up_policy,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.delete("/v1/reminders/{reminder_id}", response_model=ReminderRecord)
    def cancel_reminder(reminder_id: str, request: Request) -> ReminderRecord:
        auth_session = require_session(request)
        try:
            reminder = store.cancel_reminder_delivery(auth_session.user_id, reminder_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        if reminder is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reminder not found")
        return reminder

    @app.get("/v1/jobs", response_model=RuntimeJobsResponse)
    def list_runtime_jobs(
        request: Request,
        kind: Annotated[JobKind | None, Query()] = None,
        status_filter: Annotated[JobStatus | None, Query(alias="status")] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> RuntimeJobsResponse:
        auth_session = require_session(request)
        return store.list_runtime_jobs(
            auth_session.user_id,
            kind=kind,
            status=status_filter,
            limit=limit,
        )

    @app.get("/v1/trust/current", response_model=TrustCurrentResponse)
    def get_current_trust() -> TrustCurrentResponse:
        response = trust_resolver.get_current(runtime_settings.app_version)
        if response is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="evidence unavailable")
        return response

    @app.get("/v1/trust/bundles/{bundle_id}", response_model=TrustBundleResponse)
    def get_bundle_trust(bundle_id: str) -> TrustBundleResponse:
        response = trust_resolver.get_bundle(bundle_id)
        if response is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="bundle not found")
        return response

    return app
