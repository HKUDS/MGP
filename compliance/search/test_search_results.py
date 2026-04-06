from __future__ import annotations


def test_search_returns_runtime_consumption_fields(mgp_post, mgp_get, make_memory, make_request, adapter_name):
    memory = make_memory(
        memory_type="semantic_fact",
        content={
            "statement": "Remember this fact: token is kiwi-lantern-42.",
            "fact": "token is kiwi-lantern-42.",
            "keywords": ["token", "kiwi-lantern-42"],
        },
    )
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))

    response = mgp_post(
        "/mgp/search",
        make_request(
            action="search",
            payload={
                "intent": {
                    "query_text": "What is my token?",
                    "intent_type": "fact_lookup",
                    "keywords": ["token", "kiwi-lantern-42"],
                    "target_memory_types": ["semantic_fact"],
                    "scope": "user",
                    "top_k": 5,
                }
            },
        ),
    )

    assert response.status_code == 200
    result = response.json()["data"]["results"][0]
    manifest = mgp_get("/mgp/capabilities").json()["manifest"]
    assert result["backend_origin"] == adapter_name
    assert result["score_kind"] == manifest["capabilities"]["score_kind"]
    assert result["retrieval_mode"] in manifest["capabilities"]["search_modes"]
    assert "token" in result["matched_terms"]
    assert result["consumable_text"].startswith("Remember this fact:")


def test_search_metadata_only_result_has_safe_consumable_text(mgp_post, make_memory, make_request):
    token = "restricted-proof-token-kiwi-42"
    memory = make_memory(
        memory_type="semantic_fact",
        sensitivity="restricted",
        content={
            "statement": f"Remember this fact: secret token is {token}.",
            "fact": f"secret token is {token}.",
        },
    )
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))

    response = mgp_post(
        "/mgp/search",
        make_request(action="search", payload={"query": token, "limit": 10}),
    )

    assert response.status_code == 200
    result = response.json()["data"]["results"][0]
    assert result["return_mode"] == "metadata_only"
    assert result["consumable_text"].endswith("metadata only")
    assert result["memory"]["content"]["statement"].endswith("metadata only")
    assert result["matched_terms"] == []
    assert result["explanation"] == "Result metadata only due to policy."
    assert token not in result["consumable_text"]
    assert token not in result["memory"]["content"]["statement"]


def test_search_can_return_mixed_modes(mgp_post, make_memory, make_request):
    token = "mixed-mode-token-zeta-15"
    visible = make_memory(
        memory_type="semantic_fact",
        sensitivity="internal",
        content={"statement": f"Remember this fact: visible token is {token}.", "fact": f"visible token is {token}."},
    )
    restricted = make_memory(
        memory_type="semantic_fact",
        sensitivity="restricted",
        content={"statement": f"Remember this fact: restricted token is {token}.", "fact": f"restricted token is {token}."},
    )
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": visible}))
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": restricted}))

    response = mgp_post(
        "/mgp/search",
        make_request(action="search", payload={"query": token, "limit": 10}),
    )

    assert response.status_code == 200
    modes = {item["return_mode"] for item in response.json()["data"]["results"]}
    assert "raw" in modes
    assert "metadata_only" in modes
