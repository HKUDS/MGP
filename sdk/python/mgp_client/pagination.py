from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any, AsyncIterator, Iterator

from .models import AuditEvent, AuditQueryResponseData, PolicyContext, SearchResponseData, SearchResultItem
from .types import AuditQuery, SearchQuery

if TYPE_CHECKING:
    from .async_client import AsyncMGPClient
    from .client import MGPClient


def _search_with_token(search: SearchQuery | dict[str, object], token: str | None) -> SearchQuery | dict[str, object]:
    if isinstance(search, SearchQuery):
        return replace(search, pagination_token=token)
    updated = dict(search)
    if token is None:
        updated.pop("pagination_token", None)
    else:
        updated["pagination_token"] = token
    return updated


def _audit_with_token(query: AuditQuery | dict[str, object], token: str | None) -> AuditQuery | dict[str, object]:
    if isinstance(query, AuditQuery):
        return replace(query, pagination_token=token)
    updated = dict(query)
    if token is None:
        updated.pop("pagination_token", None)
    else:
        updated["pagination_token"] = token
    return updated


def iterate_search_pages(
    client: "MGPClient",
    policy_context: PolicyContext | dict[str, Any],
    search: SearchQuery | dict[str, Any],
) -> Iterator[SearchResponseData]:
    token: str | None = None
    while True:
        response = client.search_memory(policy_context, _search_with_token(search, token))
        data = response.data or {}
        yield data
        token = data.get("next_token")
        if not token:
            return


def iterate_search_results(
    client: "MGPClient",
    policy_context: PolicyContext | dict[str, Any],
    search: SearchQuery | dict[str, Any],
) -> Iterator[SearchResultItem]:
    for page in iterate_search_pages(client, policy_context, search):
        for item in page.get("results", []):
            yield item


def iterate_audit_pages(
    client: "MGPClient",
    policy_context: PolicyContext | dict[str, Any],
    query: AuditQuery | dict[str, Any],
) -> Iterator[AuditQueryResponseData]:
    token: str | None = None
    while True:
        response = client.query_audit(policy_context, _audit_with_token(query, token))
        data = response.data or {}
        yield data
        token = data.get("next_token")
        if not token:
            return


def iterate_audit_events(
    client: "MGPClient",
    policy_context: PolicyContext | dict[str, Any],
    query: AuditQuery | dict[str, Any],
) -> Iterator[AuditEvent]:
    for page in iterate_audit_pages(client, policy_context, query):
        for item in page.get("events", []):
            yield item


async def iterate_search_pages_async(
    client: "AsyncMGPClient",
    policy_context: PolicyContext | dict[str, Any],
    search: SearchQuery | dict[str, Any],
) -> AsyncIterator[SearchResponseData]:
    token: str | None = None
    while True:
        response = await client.search_memory(policy_context, _search_with_token(search, token))
        data = response.data or {}
        yield data
        token = data.get("next_token")
        if not token:
            return


async def iterate_search_results_async(
    client: "AsyncMGPClient",
    policy_context: PolicyContext | dict[str, Any],
    search: SearchQuery | dict[str, Any],
) -> AsyncIterator[SearchResultItem]:
    async for page in iterate_search_pages_async(client, policy_context, search):
        for item in page.get("results", []):
            yield item


async def iterate_audit_pages_async(
    client: "AsyncMGPClient",
    policy_context: PolicyContext | dict[str, Any],
    query: AuditQuery | dict[str, Any],
) -> AsyncIterator[AuditQueryResponseData]:
    token: str | None = None
    while True:
        response = await client.query_audit(policy_context, _audit_with_token(query, token))
        data = response.data or {}
        yield data
        token = data.get("next_token")
        if not token:
            return


async def iterate_audit_events_async(
    client: "AsyncMGPClient",
    policy_context: PolicyContext | dict[str, Any],
    query: AuditQuery | dict[str, Any],
) -> AsyncIterator[AuditEvent]:
    async for page in iterate_audit_pages_async(client, policy_context, query):
        for item in page.get("events", []):
            yield item
