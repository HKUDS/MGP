from __future__ import annotations


def test_duplicate_write_returns_conflict(mgp_post, make_memory, make_request):
    memory = make_memory(memory_id="mem_conflict_case", content={"value": "one"})
    first = mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    second = mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))

    assert first.status_code == 200
    assert second.status_code == 409
    body = second.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "MGP_CONFLICT_UNRESOLVED"


def test_write_then_update_does_not_conflict(mgp_post, make_memory, make_request):
    memory = make_memory(content={"value": "initial"})
    write_response = mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    update_response = mgp_post(
        "/mgp/update",
        make_request(
            action="update",
            payload={"memory_id": memory["memory_id"], "patch": {"content": {"value": "updated"}}},
        ),
    )

    assert write_response.status_code == 200
    assert update_response.status_code == 200
    assert update_response.json()["data"]["memory"]["content"]["value"] == "updated"
