"""Optional workspace/project memory broker backends for assistant-api."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .models import (
    MemoryBrokerProvider,
    MemoryBrokerProviderStatus,
    MemoryBrokerResult,
)


@dataclass(frozen=True, slots=True)
class MemoryBrokerSearchContext:
    user_id: str
    workspace_id: str
    project_id: str | None
    allowed_project_ids: tuple[str, ...]
    query: str
    limit: int


class MemoryBrokerBackend(Protocol):
    provider: MemoryBrokerProvider

    def provider_status(self) -> MemoryBrokerProviderStatus:
        """Return the current provider readiness for the additive broker path."""

    def provider_message(self) -> str | None:
        """Return an operator-facing reason when the provider is unavailable."""

    def search(self, context: MemoryBrokerSearchContext) -> list[MemoryBrokerResult]:
        """Return workspace/project-scoped memory results."""


@dataclass(slots=True)
class DisabledMemoryBrokerBackend:
    provider: MemoryBrokerProvider = MemoryBrokerProvider.KG_MCP
    status: MemoryBrokerProviderStatus = MemoryBrokerProviderStatus.DISABLED
    message: str | None = "KG memory broker is not configured for this runtime."

    def provider_status(self) -> MemoryBrokerProviderStatus:
        return self.status

    def provider_message(self) -> str | None:
        return self.message

    def search(self, context: MemoryBrokerSearchContext) -> list[MemoryBrokerResult]:
        return []


@dataclass(slots=True)
class StaticMemoryBrokerBackend:
    entries: list[MemoryBrokerResult] = field(default_factory=list)
    provider: MemoryBrokerProvider = MemoryBrokerProvider.KG_MCP
    status: MemoryBrokerProviderStatus = MemoryBrokerProviderStatus.READY

    def provider_status(self) -> MemoryBrokerProviderStatus:
        return self.status

    def provider_message(self) -> str | None:
        return None

    def search(self, context: MemoryBrokerSearchContext) -> list[MemoryBrokerResult]:
        normalized_query = context.query.strip().lower()
        matches: list[MemoryBrokerResult] = []
        for entry in self.entries:
            if entry.workspace_id != context.workspace_id:
                continue
            if context.project_id is not None and entry.project_id != context.project_id:
                continue
            if (
                context.project_id is None
                and context.allowed_project_ids
                and entry.project_id is not None
                and entry.project_id not in context.allowed_project_ids
            ):
                continue
            haystack = " ".join(
                part
                for part in (entry.title, entry.content, entry.source_ref)
                if isinstance(part, str) and part
            ).lower()
            if normalized_query and normalized_query not in haystack:
                continue
            matches.append(entry)
            if len(matches) >= context.limit:
                break
        return matches


def create_memory_broker_backend() -> MemoryBrokerBackend:
    """Return the default additive-only broker backend.

    The runtime defaults to a disabled provider so KG never becomes an implicit
    dependency for unrelated requests. Tests can inject a ready backend.
    """

    return DisabledMemoryBrokerBackend()
