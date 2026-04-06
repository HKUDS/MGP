from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = ROOT / "reference"
if str(REFERENCE_DIR) not in sys.path:
    sys.path.insert(0, str(REFERENCE_DIR))

from gateway.validation import validate_adapter_manifest, validate_capabilities_response


def test_capabilities_returns_valid_manifest(mgp_get):
    response = mgp_get("/mgp/capabilities")
    assert response.status_code == 200
    validate_capabilities_response(response.json())
    manifest = response.json()["manifest"]
    validate_adapter_manifest(manifest)


def test_manifest_declares_write_and_search(mgp_get):
    response = mgp_get("/mgp/capabilities")
    manifest = response.json()["manifest"]
    assert manifest["capabilities"]["supports_write"] is True
    assert manifest["capabilities"]["supports_search"] is True


def test_capabilities_returns_protocol_capabilities(mgp_get):
    response = mgp_get("/mgp/capabilities")
    protocol_capabilities = response.json()["protocol_capabilities"]
    assert protocol_capabilities["supports_initialize"] is True
    assert protocol_capabilities["supports_runtime_capability_negotiation"] is True
    assert protocol_capabilities["supports_negotiated_capabilities"] is True


def test_write_and_search_follow_manifest(mgp_get, mgp_post, make_memory, make_request):
    manifest = mgp_get("/mgp/capabilities").json()["manifest"]
    memory = make_memory(content={"fact": "adapter-check"})

    if manifest["capabilities"]["supports_write"]:
        write_response = mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
        assert write_response.status_code == 200

    if manifest["capabilities"]["supports_search"]:
        search_response = mgp_post(
            "/mgp/search",
            make_request(action="search", payload={"query": "adapter-check", "limit": 10}),
        )
        assert search_response.status_code == 200
        assert search_response.json()["data"]["results"]


def test_round_trip_preserves_core_fields(mgp_post, make_memory, make_request):
    memory = make_memory(
        content={"favorite_color": "blue"},
        memory_type="profile",
        sensitivity="internal",
    )
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    response = mgp_post("/mgp/get", make_request(action="read", payload={"memory_id": memory["memory_id"]}))

    assert response.status_code == 200
    returned = response.json()["data"]["memory"]
    assert returned["memory_id"] == memory["memory_id"]
    assert returned["subject"] == memory["subject"]
    assert returned["scope"] == memory["scope"]
    assert returned["type"] == memory["type"]
    assert returned["content"] == memory["content"]
    assert returned["source"] == memory["source"]
