from __future__ import annotations

import time
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def test_ttl_expired_memory_is_hidden_from_search(mgp_post, make_memory, make_request):
    memory = make_memory(
        content={"topic": "temporary"},
        ttl_seconds=1,
        created_at=_now_iso(),
    )
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    time.sleep(1.2)

    response = mgp_post("/mgp/search", make_request(action="search", payload={"query": "temporary", "limit": 10}))
    assert response.status_code == 200
    assert response.json()["data"]["results"] == []


def test_persistent_memory_remains_available(mgp_post, make_memory, make_request):
    memory = make_memory(
        content={"topic": "durable"},
        retention_policy="persistent",
        created_at=_now_iso(),
    )
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))

    response = mgp_post("/mgp/search", make_request(action="search", payload={"query": "durable", "limit": 10}))
    assert response.status_code == 200
    assert len(response.json()["data"]["results"]) == 1


def test_revoked_memory_is_hidden_from_search(mgp_post, make_memory, make_request):
    memory = make_memory(content={"topic": "revoked_item"})
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    mgp_post("/mgp/revoke", make_request(action="revoke", payload={"memory_id": memory["memory_id"], "reason": "test"}))

    response = mgp_post("/mgp/search", make_request(action="search", payload={"query": "revoked_item", "limit": 10}))
    assert response.status_code == 200
    assert response.json()["data"]["results"] == []


def test_revoked_memory_is_still_gettable(mgp_post, make_memory, make_request):
    memory = make_memory(content={"topic": "revoked_but_gettable"})
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    mgp_post("/mgp/revoke", make_request(action="revoke", payload={"memory_id": memory["memory_id"], "reason": "test"}))

    response = mgp_post("/mgp/get", make_request(action="read", payload={"memory_id": memory["memory_id"]}))
    assert response.status_code == 200
    fetched = response.json()["data"]["memory"]
    assert fetched["memory_id"] == memory["memory_id"]
    assert fetched["backend_ref"]["mgp_state"] == "revoked"
