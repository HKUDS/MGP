from __future__ import annotations


def test_batch_write_returns_per_item_results(mgp_post, make_memory, make_request):
    first = make_memory(
        memory_type="semantic_fact",
        content={"statement": "Remember this fact: batch token alpha.", "fact": "batch token alpha."},
    )
    second = make_memory(
        memory_type="semantic_fact",
        content={"statement": "Remember this fact: batch token beta.", "fact": "batch token beta."},
    )

    response = mgp_post(
        "/mgp/write/batch",
        make_request(
            action="write",
            payload={
                "items": [
                    {"memory": first},
                    {"memory": second},
                ]
            },
        ),
    )

    assert response.status_code == 200
    body = response.json()["data"]["results"]
    assert len(body) == 2
    assert all(item["status"] == "ok" for item in body)


def test_export_and_import_round_trip(mgp_post, make_memory, make_request):
    memory = make_memory(
        memory_type="semantic_fact",
        content={"statement": "Remember this fact: export token gamma.", "fact": "export token gamma."},
    )
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))

    exported = mgp_post(
        "/mgp/export",
        make_request(action="read", payload={"include_inactive": False, "limit": 50}),
    )
    assert exported.status_code == 200
    memories = exported.json()["data"]["memories"]
    exported_memory = next(item for item in memories if item["memory_id"] == memory["memory_id"])

    mgp_post(
        "/mgp/purge", make_request(action="purge", payload={"memory_id": memory["memory_id"], "reason": "round_trip"})
    )
    missing = mgp_post("/mgp/get", make_request(action="read", payload={"memory_id": memory["memory_id"]}))
    assert missing.status_code == 404

    imported = mgp_post(
        "/mgp/import",
        make_request(action="write", payload={"memories": [exported_memory]}),
    )
    assert imported.status_code == 200
    assert exported_memory["memory_id"] in imported.json()["data"]["memory_ids"]


def test_sync_supports_cursor_pagination(mgp_post, make_memory, make_request):
    memory_a = make_memory(
        memory_type="semantic_fact",
        content={"statement": "Remember this fact: sync token one.", "fact": "sync token one."},
    )
    memory_b = make_memory(
        memory_type="semantic_fact",
        content={"statement": "Remember this fact: sync token two.", "fact": "sync token two."},
    )
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory_a}))
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory_b}))

    first_page = mgp_post(
        "/mgp/sync",
        make_request(action="read", payload={"limit": 1}),
    )
    assert first_page.status_code == 200
    cursor = first_page.json()["data"].get("cursor")
    assert cursor is not None

    second_page = mgp_post(
        "/mgp/sync",
        make_request(action="read", payload={"limit": 10, "cursor": cursor}),
    )
    assert second_page.status_code == 200
    assert second_page.json()["data"]["memories"]


def test_async_export_can_be_polled_to_completion(mgp_post, make_memory, make_request):
    memory = make_memory(
        memory_type="semantic_fact",
        content={"statement": "Remember this fact: async export token.", "fact": "async export token."},
    )
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))

    accepted = mgp_post(
        "/mgp/export",
        make_request(action="read", payload={"include_inactive": False, "limit": 50, "execution_mode": "async"}),
    )
    assert accepted.status_code == 202
    task = accepted.json()["data"]["task"]
    assert task["status"] == "pending"

    completed = mgp_post(
        "/mgp/tasks/get",
        {
            "request_id": "req_task_poll",
            "task_id": task["task_id"],
        },
    )
    assert completed.status_code == 200
    resolved = completed.json()["data"]["task"]
    assert resolved["status"] == "completed"
    assert any(item["memory_id"] == memory["memory_id"] for item in resolved["result"]["memories"])


def test_async_import_can_be_cancelled_before_completion(mgp_post, make_memory, make_request):
    memory = make_memory(
        memory_type="semantic_fact",
        content={"statement": "Remember this fact: async import token.", "fact": "async import token."},
    )
    accepted = mgp_post(
        "/mgp/import",
        make_request(action="write", payload={"memories": [memory], "execution_mode": "async"}),
    )
    assert accepted.status_code == 202
    task = accepted.json()["data"]["task"]

    cancelled = mgp_post(
        "/mgp/tasks/cancel",
        {
            "request_id": "req_task_cancel",
            "task_id": task["task_id"],
            "reason": "test_cancel",
        },
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["task"]["status"] == "cancelled"

    polled = mgp_post(
        "/mgp/tasks/get",
        {
            "request_id": "req_task_get_cancelled",
            "task_id": task["task_id"],
        },
    )
    assert polled.status_code == 200
    assert polled.json()["data"]["task"]["status"] == "cancelled"
