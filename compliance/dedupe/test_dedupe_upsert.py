from __future__ import annotations


def test_write_candidate_dedupe_returns_existing_memory(mgp_post, make_request):
    candidate = {
        "candidate_kind": "assertion",
        "subject": {"kind": "user", "id": "user_123"},
        "scope": "user",
        "proposed_type": "preference",
        "statement": "User prefers concise replies.",
        "source": {"kind": "chat", "ref": "chat:1"},
        "content": {
            "statement": "User prefers concise replies.",
            "preference": "concise replies",
        },
        "merge_hint": {
            "strategy": "dedupe",
            "dedupe_key": "user_123:preference:concise-replies",
        },
    }

    first = mgp_post("/mgp/write", make_request(action="write", payload={"candidate": candidate}))
    second = mgp_post("/mgp/write", make_request(action="write", payload={"candidate": candidate}))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["memory"]["memory_id"] == second.json()["data"]["memory"]["memory_id"]
    assert second.json()["data"]["resolution"] == "deduped"


def test_write_with_upsert_replaces_existing_memory(mgp_post, make_memory, make_request):
    memory = make_memory(
        memory_id="mem_upsert_case",
        memory_type="preference",
        content={
            "statement": "User prefers detailed replies.",
            "preference": "detailed replies",
        },
    )
    first = mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))
    assert first.status_code == 200

    replacement = make_memory(
        memory_id="mem_new_id",
        memory_type="preference",
        content={
            "statement": "User prefers concise replies.",
            "preference": "concise replies",
        },
    )
    response = mgp_post(
        "/mgp/write",
        make_request(
            action="write",
            payload={
                "memory": replacement,
                "merge_hint": {
                    "strategy": "upsert",
                    "if_match_memory_id": "mem_upsert_case",
                },
            },
        ),
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["memory"]["memory_id"] == "mem_upsert_case"
    assert body["memory"]["content"]["statement"] == "User prefers concise replies."
    assert body["resolution"] == "replaced"
