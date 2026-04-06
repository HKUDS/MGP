from __future__ import annotations

from typing import Any, Mapping

from integrations._bridge_helpers import (
    ClientFactory,
    build_policy_context,
    build_user_search_query,
    default_client_factory,
    prompt_context_from_results,
)


class LangGraphMemoryBridge:
    """Thin helper for wiring MGP into a LangGraph-style state dictionary."""

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

    def recall_for_state(self, state: Mapping[str, Any]) -> dict[str, Any]:
        client = self._client_factory(self.gateway_url, self.timeout)
        response = client.search_memory(
            build_policy_context(
                action="search",
                actor_agent=state.get("actor_agent", "langgraph/runtime"),
                user_id=state["user_id"],
                tenant_id=state.get("tenant_id"),
                session_id=state.get("session_id"),
                task_id=state.get("thread_id"),
            ),
            build_user_search_query(
                query=state["query"],
                user_id=state["user_id"],
                limit=int(state.get("limit", 5)),
            ),
        )
        results = (response.data or {}).get("results", [])
        return {
            "request_id": response.request_id,
            "mgp_results": results,
            "mgp_prompt_context": prompt_context_from_results(results),
        }

    def commit_for_state(self, state: Mapping[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        client = self._client_factory(self.gateway_url, self.timeout)
        response = client.write_candidate(
            build_policy_context(
                action="write",
                actor_agent=state.get("actor_agent", "langgraph/runtime"),
                user_id=state["user_id"],
                tenant_id=state.get("tenant_id"),
                session_id=state.get("session_id"),
                task_id=state.get("thread_id"),
            ),
            candidate,
            merge_hint=candidate.get("merge_hint"),
        )
        return {
            "request_id": response.request_id,
            "memory": (response.data or {}).get("memory"),
        }
