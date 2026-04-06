from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Protocol

from mgp_client import MGPClient, PolicyContextBuilder, SearchQuery
from mgp_client.models import PolicyContext


class SupportsGatewayClient(Protocol):
    def search_memory(
        self,
        policy_context: PolicyContext | dict[str, Any],
        search: SearchQuery | dict[str, Any],
        request_id: str | None = None,
    ) -> Any:
        ...

    def write_candidate(
        self,
        policy_context: PolicyContext | dict[str, Any],
        candidate: dict[str, Any],
        *,
        merge_hint: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> Any:
        ...


ClientFactory = Callable[[str, float], SupportsGatewayClient]


def default_client_factory(base_url: str, timeout: float) -> SupportsGatewayClient:
    return MGPClient(base_url, timeout=timeout)


def build_policy_context(
    *,
    action: str,
    actor_agent: str,
    user_id: str,
    tenant_id: str | None = None,
    session_id: str | None = None,
    task_id: str | None = None,
) -> PolicyContext:
    builder = PolicyContextBuilder(
        actor_agent=actor_agent,
        subject_id=user_id,
        tenant_id=tenant_id,
        session_id=session_id,
        task_id=task_id,
    )
    return builder.build(action)


def build_user_search_query(*, query: str, user_id: str, limit: int) -> SearchQuery:
    return SearchQuery(query_text=query, limit=limit, subject={"kind": "user", "id": user_id})


def prompt_context_from_results(results: Iterable[Mapping[str, Any]]) -> str:
    return "\n".join(str(item["consumable_text"]) for item in results if item.get("consumable_text"))
