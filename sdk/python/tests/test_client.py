from __future__ import annotations

import json

import httpx
from mgp_client import BearerAuth, MGPClient

from .conftest import mgp_ok


def test_write_memory_builds_envelope_and_auth_headers():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["headers"] = dict(request.headers)
        seen["json"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json=mgp_ok({"memory": {"memory_id": "mem_1"}}))

    client = MGPClient("http://testserver", auth=BearerAuth("token-123"), transport=httpx.MockTransport(handler))
    response = client.write_memory(
        {
            "actor_agent": "agent/test",
            "acting_for_subject": {"kind": "user", "id": "user_1"},
            "requested_action": "write",
        },
        {"memory_id": "mem_1"},
        request_id="req_write",
    )

    assert response.request_id == "req_test"
    assert seen["path"] == "/mgp/write"
    assert seen["headers"]["authorization"] == "Bearer token-123"
    assert seen["json"]["request_id"] == "req_write"
    assert seen["json"]["payload"]["memory"]["memory_id"] == "mem_1"


def test_get_capabilities_returns_raw_document(sync_client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/mgp/capabilities"
        return httpx.Response(
            200,
            json={
                "manifest": {"backend_kind": "memory"},
                "protocol_capabilities": {"supports_discovery": True},
            },
        )

    client = sync_client_factory(handler)
    capabilities = client.get_capabilities()
    assert capabilities["manifest"]["backend_kind"] == "memory"
