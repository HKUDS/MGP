from __future__ import annotations

from mgp_client.types import MGPResponse

from integrations.minimal_runtime import MinimalRuntimeMemoryBridge


class FakeClient:
    def __init__(self) -> None:
        self.search_calls: list[tuple[dict, object]] = []
        self.write_calls: list[tuple[dict, dict, dict | None]] = []

    def search_memory(self, policy_context, search, request_id=None):
        self.search_calls.append((policy_context, search))
        return MGPResponse(
            request_id="req_search",
            status="ok",
            data={"results": [{"consumable_text": "theme=dark"}]},
            error=None,
        )

    def write_candidate(self, policy_context, candidate, merge_hint=None, request_id=None):
        self.write_calls.append((policy_context, candidate, merge_hint))
        return MGPResponse(
            request_id="req_write",
            status="ok",
            data={"memory": {"memory_id": "mem_1"}},
            error=None,
        )


def test_minimal_bridge_recall_and_commit() -> None:
    fake = FakeClient()
    bridge = MinimalRuntimeMemoryBridge("http://mgp.invalid", client_factory=lambda base_url, timeout: fake)

    recall = bridge.recall(
        actor_agent="minimal-runtime/agent",
        user_id="user_123",
        tenant_id="tenant_demo",
        query="theme preference",
    )
    commit = bridge.commit_candidate(
        actor_agent="minimal-runtime/agent",
        user_id="user_123",
        tenant_id="tenant_demo",
        candidate={
            "candidate_kind": "assertion",
            "subject": {"kind": "user", "id": "user_123"},
            "scope": "user",
            "proposed_type": "preference",
            "statement": "User prefers dark mode.",
            "source": {"kind": "runtime", "ref": "turn:1"},
            "content": {"statement": "User prefers dark mode."},
        },
    )

    assert recall["prompt_context"] == "theme=dark"
    assert commit["memory"]["memory_id"] == "mem_1"
    assert fake.search_calls[0][0]["tenant_id"] == "tenant_demo"
    assert fake.write_calls[0][0]["requested_action"] == "write"
