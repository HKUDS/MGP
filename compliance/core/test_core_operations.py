from __future__ import annotations


def test_write_success(mgp_post, make_memory, make_request):
    memory = make_memory(content={"theme": "dark"})
    response = mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["memory"]["memory_id"] == memory["memory_id"]


def test_write_duplicate_memory_id_returns_conflict(mgp_post, make_memory, make_request):
    memory = make_memory(memory_id="mem_duplicate", content={"theme": "dark"})
    first = mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    second = mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "MGP_CONFLICT_UNRESOLVED"


def test_search_success(mgp_post, make_memory, make_request):
    memory = make_memory(content={"city": "beijing"})
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    response = mgp_post("/mgp/search", make_request(action="search", payload={"query": "beijing", "limit": 10}))
    assert response.status_code == 200
    assert response.json()["data"]["results"]


def test_search_empty_query_returns_empty(mgp_post, make_memory, make_request):
    memory = make_memory(content={"city": "beijing"})
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    response = mgp_post("/mgp/search", make_request(action="search", payload={"query": "", "limit": 10}))
    assert response.status_code == 200
    assert response.json()["data"]["results"] == []


def test_get_existing_returns_memory(mgp_post, make_memory, make_request):
    memory = make_memory(content={"name": "alice"})
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    response = mgp_post("/mgp/get", make_request(action="read", payload={"memory_id": memory["memory_id"]}))
    assert response.status_code == 200
    assert response.json()["data"]["memory"]["memory_id"] == memory["memory_id"]


def test_get_nonexistent_returns_not_found(mgp_post, make_request):
    response = mgp_post("/mgp/get", make_request(action="read", payload={"memory_id": "missing_memory"}))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MGP_MEMORY_NOT_FOUND"


def test_update_existing_succeeds(mgp_post, make_memory, make_request):
    memory = make_memory(content={"theme": "dark"})
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    response = mgp_post(
        "/mgp/update",
        make_request(
            action="update",
            payload={"memory_id": memory["memory_id"], "patch": {"content": {"theme": "light"}}},
        ),
    )
    assert response.status_code == 200
    assert response.json()["data"]["memory"]["content"]["theme"] == "light"


def test_update_nonexistent_returns_not_found(mgp_post, make_request):
    response = mgp_post(
        "/mgp/update",
        make_request(action="update", payload={"memory_id": "missing_memory", "patch": {"content": {"a": 1}}}),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MGP_MEMORY_NOT_FOUND"


def test_expire_existing_returns_expired(mgp_post, make_memory, make_request):
    memory = make_memory()
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    response = mgp_post(
        "/mgp/expire",
        make_request(action="expire", payload={"memory_id": memory["memory_id"], "reason": "test"}),
    )
    assert response.status_code == 200
    assert response.json()["data"]["state"] == "expired"


def test_expire_nonexistent_returns_not_found(mgp_post, make_request):
    response = mgp_post(
        "/mgp/expire",
        make_request(action="expire", payload={"memory_id": "missing_memory", "reason": "test"}),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MGP_MEMORY_NOT_FOUND"


def test_revoke_existing_returns_revoked(mgp_post, make_memory, make_request):
    memory = make_memory()
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    response = mgp_post(
        "/mgp/revoke",
        make_request(action="revoke", payload={"memory_id": memory["memory_id"], "reason": "test"}),
    )
    assert response.status_code == 200
    assert response.json()["data"]["state"] == "revoked"


def test_revoke_nonexistent_returns_not_found(mgp_post, make_request):
    response = mgp_post(
        "/mgp/revoke",
        make_request(action="revoke", payload={"memory_id": "missing_memory", "reason": "test"}),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MGP_MEMORY_NOT_FOUND"
