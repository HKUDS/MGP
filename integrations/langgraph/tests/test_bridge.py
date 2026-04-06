from __future__ import annotations

from mgp_client.types import MGPResponse

from integrations.langgraph import LangGraphMemoryBridge


class FakeClient:
    def search_memory(self, policy_context, search, request_id=None):
        return MGPResponse(
            request_id="req_search",
            status="ok",
            data={"results": [{"consumable_text": "theme=dark"}]},
            error=None,
        )

    def write_candidate(self, policy_context, candidate, merge_hint=None, request_id=None):
        return MGPResponse(
            request_id="req_write",
            status="ok",
            data={"memory": {"memory_id": "mem_1"}},
            error=None,
        )


def test_langgraph_bridge_maps_state() -> None:
    bridge = LangGraphMemoryBridge("http://mgp.invalid", client_factory=lambda base_url, timeout: FakeClient())
    state = {
        "actor_agent": "langgraph/runtime",
        "user_id": "user_123",
        "tenant_id": "tenant_demo",
        "thread_id": "thread_001",
        "session_id": "session_001",
        "query": "theme preference",
    }

    recall_patch = bridge.recall_for_state(state)
    commit_patch = bridge.commit_for_state(
        state,
        {
            "candidate_kind": "assertion",
            "subject": {"kind": "user", "id": "user_123"},
            "scope": "user",
            "proposed_type": "preference",
            "statement": "User prefers dark mode.",
            "source": {"kind": "runtime", "ref": "thread:thread_001"},
            "content": {"statement": "User prefers dark mode."},
        },
    )

    assert recall_patch["mgp_prompt_context"] == "theme=dark"
    assert commit_patch["memory"]["memory_id"] == "mem_1"
