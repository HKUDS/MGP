from __future__ import annotations

import pytest


def test_delete_hides_memory_from_search_but_keeps_get_access(mgp_post, make_memory, make_request):
    token = "deleted-proof-token-kiwi-77"
    memory = make_memory(
        memory_type="semantic_fact",
        content={"statement": f"Remember this fact: token is {token}.", "fact": f"token is {token}."},
    )
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))

    deleted = mgp_post(
        "/mgp/delete",
        make_request(action="delete", payload={"memory_id": memory["memory_id"], "reason": "user_request"}),
    )
    assert deleted.status_code == 200
    assert deleted.json()["data"]["state"] == "deleted"

    search = mgp_post("/mgp/search", make_request(action="search", payload={"query": token, "limit": 10}))
    assert search.status_code == 200
    assert search.json()["data"]["results"] == []

    get_response = mgp_post("/mgp/get", make_request(action="read", payload={"memory_id": memory["memory_id"]}))
    assert get_response.status_code == 200
    assert get_response.json()["data"]["memory"]["backend_ref"]["mgp_state"] == "deleted"
    assert get_response.json()["data"]["return_mode"] == "metadata_only"


def test_purge_removes_memory_completely(mgp_post, make_memory, make_request, manifest_capabilities):
    if not manifest_capabilities["supports_purge"]:
        pytest.skip("adapter does not support hard purge")
    token = "purged-proof-token-mango-81"
    memory = make_memory(
        memory_type="semantic_fact",
        content={"statement": f"Remember this fact: purge token is {token}.", "fact": f"purge token is {token}."},
    )
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))

    purged = mgp_post(
        "/mgp/purge",
        make_request(action="purge", payload={"memory_id": memory["memory_id"], "reason": "compliance_erase"}),
    )
    assert purged.status_code == 200
    assert purged.json()["data"]["state"] == "purged"

    get_response = mgp_post("/mgp/get", make_request(action="read", payload={"memory_id": memory["memory_id"]}))
    assert get_response.status_code == 404
