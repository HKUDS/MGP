from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mgp_client.errors import BackendError
from mgp_client.types import MGPResponse

from integrations.nanobot.sidecar import (
    MemoryCandidate,
    NanobotMGPSidecar,
    NanobotRuntimeState,
    NanobotSidecarConfig,
    RecallIntent,
    build_policy_context,
    build_search_query,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def load_runtime() -> NanobotRuntimeState:
    return NanobotRuntimeState.from_mapping(
        json.loads((FIXTURES_DIR / "runtime_state.json").read_text(encoding="utf-8"))
    )


def load_candidate() -> MemoryCandidate:
    return MemoryCandidate.from_mapping(
        json.loads((FIXTURES_DIR / "memory_candidate.json").read_text(encoding="utf-8"))
    )


class FakeClient:
    def __init__(self) -> None:
        self.closed = False
        self.search_response: MGPResponse[dict[str, Any]] = MGPResponse(
            request_id="req_search",
            status="ok",
            data={"results": []},
            error=None,
        )
        self.write_response: MGPResponse[dict[str, Any]] = MGPResponse(
            request_id="req_write",
            status="ok",
            data={"memory": {}},
            error=None,
        )
        self.search_error: Exception | None = None
        self.write_error: Exception | None = None
        self.search_calls: list[tuple[dict, object]] = []
        self.write_calls: list[tuple[dict, dict]] = []
        self.write_candidate_calls: list[tuple[dict, dict, dict | None]] = []

    def search_memory(self, policy_context, search, request_id=None):
        self.search_calls.append((policy_context, search))
        if self.search_error is not None:
            raise self.search_error
        return self.search_response

    def write_memory(self, policy_context, memory, request_id=None):
        self.write_calls.append((policy_context, memory))
        if self.write_error is not None:
            raise self.write_error
        if not self.write_response.data or "memory" not in self.write_response.data:
            self.write_response.data = {"memory": memory}
        return self.write_response

    def write_candidate(self, policy_context, candidate, merge_hint=None, request_id=None):
        self.write_candidate_calls.append((policy_context, candidate, merge_hint))
        if self.write_error is not None:
            raise self.write_error
        candidate_payload = candidate.to_payload() if hasattr(candidate, "to_payload") else candidate
        memory = {
            "memory_id": "mem_from_candidate",
            "subject": candidate_payload["subject"],
            "scope": candidate_payload["scope"],
            "type": candidate_payload["proposed_type"],
            "content": candidate_payload["content"],
            "source": candidate_payload["source"],
            "created_at": "2026-03-18T00:00:00Z",
            "backend_ref": {"tenant_id": policy_context.get("tenant_id")},
            "extensions": candidate_payload.get("extensions", {}),
        }
        self.write_response.data = {"memory": memory}
        return self.write_response

    def close(self) -> None:
        self.closed = True


def make_factory(client: FakeClient):
    return lambda base_url, timeout, headers: client


class FakeTelemetry:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def emit(self, event: str, **fields) -> None:
        self.events.append((event, fields))


def test_policy_context_uses_workspace_as_default_tenant() -> None:
    runtime = load_runtime()
    context = build_policy_context(runtime, "search")

    assert context["actor_agent"] == "nanobot/main"
    assert context["acting_for_subject"] == {"kind": "user", "id": "user_nanobot_demo"}
    assert context["tenant_id"] == "workspace_demo"
    assert context["task_id"] == "cli:user_nanobot_demo"
    assert context["task_type"] == "process_direct"


def test_off_mode_skips_mgp_calls() -> None:
    fake = FakeClient()
    sidecar = NanobotMGPSidecar(
        NanobotSidecarConfig(gateway_url="http://mgp.invalid", mode="off"),
        client_factory=make_factory(fake),
    )

    recall = sidecar.recall(load_runtime(), RecallIntent(query="quiet hours"))
    commit = sidecar.commit(load_runtime(), load_candidate())

    assert recall.executed is False
    assert recall.fallback == "nanobot-native"
    assert commit.written is False
    assert fake.search_calls == []
    assert fake.write_calls == []


def test_shadow_mode_executes_without_prompt_injection() -> None:
    fake = FakeClient()
    fake.search_response = MGPResponse(
        request_id="req_shadow",
        status="ok",
        data={
            "results": [
                {
                    "memory": {
                        "memory_id": "mem_1",
                        "scope": "user",
                        "type": "preference",
                        "content": {"quiet_hours": "22:00-07:00"},
                    },
                    "score": 0.9,
                    "return_mode": "raw",
                    "backend_origin": "memory",
                }
            ]
        },
        error=None,
    )

    sidecar = NanobotMGPSidecar(
        NanobotSidecarConfig(gateway_url="http://mgp.invalid", mode="shadow", reuse_client=False),
        client_factory=make_factory(fake),
    )
    outcome = sidecar.recall(load_runtime(), RecallIntent(query="quiet hours"))

    assert outcome.executed is True
    assert outcome.degraded is False
    assert outcome.prompt_context == ""
    assert outcome.used_prompt is False
    assert len(outcome.results) == 1
    assert fake.closed is True


def test_reuse_client_keeps_shared_client_until_close() -> None:
    fake = FakeClient()
    telemetry = FakeTelemetry()
    sidecar = NanobotMGPSidecar(
        NanobotSidecarConfig(gateway_url="http://mgp.invalid", mode="shadow", reuse_client=True),
        client_factory=make_factory(fake),
        telemetry=telemetry,
    )

    recall = sidecar.recall(load_runtime(), RecallIntent(query="quiet hours"))
    commit = sidecar.commit(load_runtime(), load_candidate())

    assert recall.executed is True
    assert commit.written is True
    assert fake.closed is False
    assert telemetry.events[0][0] == "recall_started"
    assert telemetry.events[-1][0] == "commit_completed"

    sidecar.close()
    assert fake.closed is True


def test_primary_mode_filters_metadata_only_from_prompt_context() -> None:
    fake = FakeClient()
    fake.search_response = MGPResponse(
        request_id="req_primary",
        status="ok",
        data={
            "results": [
                {
                    "memory": {
                        "memory_id": "mem_visible",
                        "scope": "user",
                        "type": "preference",
                        "content": {"response_style": "concise"},
                    },
                    "score": 0.8,
                    "return_mode": "raw",
                    "backend_origin": "memory",
                },
                {
                    "memory": {
                        "memory_id": "mem_hidden",
                        "scope": "user",
                        "type": "profile",
                        "content": {"secret_note": "should_not_be_in_prompt"},
                    },
                    "score": 0.4,
                    "return_mode": "metadata_only",
                    "backend_origin": "memory",
                },
            ]
        },
        error=None,
    )

    sidecar = NanobotMGPSidecar(
        NanobotSidecarConfig(gateway_url="http://mgp.invalid", mode="primary"),
        client_factory=make_factory(fake),
    )
    outcome = sidecar.recall(load_runtime(), RecallIntent(query="response style"))

    assert outcome.executed is True
    assert outcome.used_prompt is True
    assert "response_style" in outcome.prompt_context
    assert "should_not_be_in_prompt" not in outcome.prompt_context


def test_commit_builds_canonical_memory_and_context() -> None:
    fake = FakeClient()
    sidecar = NanobotMGPSidecar(
        NanobotSidecarConfig(gateway_url="http://mgp.invalid", mode="shadow"),
        client_factory=make_factory(fake),
    )

    outcome = sidecar.commit(load_runtime(), load_candidate())

    assert outcome.written is True
    assert len(fake.write_candidate_calls) == 1

    policy_context, protocol_candidate, merge_hint = fake.write_candidate_calls[0]
    assert policy_context["requested_action"] == "write"
    assert policy_context["tenant_id"] == "workspace_demo"
    candidate_payload = (
        protocol_candidate.to_payload() if hasattr(protocol_candidate, "to_payload") else protocol_candidate
    )
    assert candidate_payload["subject"] == {"kind": "user", "id": "user_nanobot_demo"}
    assert candidate_payload["proposed_type"] == "preference"
    assert candidate_payload["extensions"]["nanobot:workspace"] == "workspace_demo"
    assert candidate_payload["extensions"]["nanobot:session_key"] == "cli:user_nanobot_demo"
    assert merge_hint is not None


def test_recall_fail_open_returns_native_fallback() -> None:
    fake = FakeClient()
    fake.search_error = BackendError(code="MGP_BACKEND_ERROR", message="gateway unavailable", details=None)
    sidecar = NanobotMGPSidecar(
        NanobotSidecarConfig(gateway_url="http://mgp.invalid", mode="primary", fail_open=True),
        client_factory=make_factory(fake),
    )

    outcome = sidecar.recall(load_runtime(), RecallIntent(query="quiet hours"))

    assert outcome.executed is False
    assert outcome.degraded is True
    assert outcome.fallback == "nanobot-native"
    assert outcome.error_code == "MGP_BACKEND_ERROR"


def test_build_search_query_normalizes_recall_prompt() -> None:
    runtime = load_runtime()
    search = build_search_query(runtime, RecallIntent(query="What did I say about concise replies?"))

    assert search.query == "concise replies"
    assert search.subject == {"kind": "user", "id": "user_nanobot_demo"}
