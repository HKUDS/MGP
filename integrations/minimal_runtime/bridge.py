from __future__ import annotations

from typing import Any

from integrations._bridge_helpers import (
    ClientFactory,
    build_policy_context,
    build_user_search_query,
    default_client_factory,
    prompt_context_from_results,
)


class MinimalRuntimeMemoryBridge:
    def __init__(
        self,
        gateway_url: str,
        *,
        timeout: float = 5.0,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.gateway_url = gateway_url
        self.timeout = timeout
        self._client_factory = client_factory or default_client_factory

    def recall(
        self,
        *,
        actor_agent: str,
        user_id: str,
        tenant_id: str,
        query: str,
        limit: int = 5,
    ) -> dict[str, Any]:
        client = self._client_factory(self.gateway_url, self.timeout)
        response = client.search_memory(
            build_policy_context(
                action="search",
                actor_agent=actor_agent,
                user_id=user_id,
                tenant_id=tenant_id,
            ),
            build_user_search_query(query=query, user_id=user_id, limit=limit),
        )
        results = (response.data or {}).get("results", [])
        return {
            "request_id": response.request_id,
            "results": results,
            "prompt_context": prompt_context_from_results(results),
        }

    def commit_candidate(
        self,
        *,
        actor_agent: str,
        user_id: str,
        tenant_id: str,
        candidate: dict[str, Any],
        merge_hint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = self._client_factory(self.gateway_url, self.timeout)
        response = client.write_candidate(
            build_policy_context(
                action="write",
                actor_agent=actor_agent,
                user_id=user_id,
                tenant_id=tenant_id,
            ),
            candidate,
            merge_hint=merge_hint,
        )
        return {
            "request_id": response.request_id,
            "memory": (response.data or {}).get("memory"),
        }
