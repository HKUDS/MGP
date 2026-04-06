from __future__ import annotations

import importlib.util

import pytest


def _require_lancedb() -> None:
    if importlib.util.find_spec("lancedb") is None:
        pytest.skip("lancedb is not installed")


def _skip_unless_lancedb(adapter_name: str) -> None:
    if adapter_name != "lancedb":
        pytest.skip("lancedb-specific test")


def test_lancedb_hybrid_search_marks_results(mgp_post, make_memory, make_request, adapter_name):
    _skip_unless_lancedb(adapter_name)
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
        make_request(action="search", payload={"query": "kiwi-lantern-42", "limit": 10}),
    )

    assert response.status_code == 200
    assert response.json()["data"]["results"][0]["retrieval_mode"] == "hybrid"


def test_lancedb_collapses_duplicate_results_by_dedupe_key(mgp_post, make_memory, make_request, adapter_name):
    _skip_unless_lancedb(adapter_name)
    first = make_memory(
        memory_id="mem_dup_a",
        memory_type="semantic_fact",
        content={
            "statement": "Remember this fact: duplicate token is lantern-zeta-19.",
            "fact": "duplicate token is lantern-zeta-19.",
        },
    )
    first["extensions"]["mgp:dedupe_key"] = "shared-lantern-zeta"

    second = make_memory(
        memory_id="mem_dup_b",
        memory_type="semantic_fact",
        content={
            "statement": "Remember this fact: duplicate token is lantern-zeta-19.",
            "fact": "duplicate token is lantern-zeta-19.",
        },
    )
    second["extensions"]["mgp:dedupe_key"] = "shared-lantern-zeta"

    mgp_post("/mgp/write", make_request(action="write", payload={"memory": first}))
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": second}))

    response = mgp_post(
        "/mgp/search",
        make_request(action="search", payload={"query": "lantern-zeta-19", "limit": 10}),
    )

    assert response.status_code == 200
    results = response.json()["data"]["results"]
    assert len(results) == 1
    assert results[0]["memory"]["memory_id"] in {"mem_dup_a", "mem_dup_b"}


def test_lancedb_list_memories_hides_ttl_expired_by_default(tmp_path):
    _require_lancedb()
    from adapters.lancedb import LanceDBAdapter

    adapter = LanceDBAdapter(
        db_dir=str(tmp_path / "lancedb"),
        embedding_provider="fake",
        embedding_model="mgp-fake-embedding-v1",
        hybrid_enabled=True,
    )
    expired = {
        "memory_id": "mem_expired",
        "subject": {"kind": "user", "id": "user_123"},
        "scope": "user",
        "type": "semantic_fact",
        "content": {"statement": "Expired memory", "fact": "Expired memory"},
        "source": {"kind": "human", "ref": "chat:test"},
        "created_at": "2026-03-17T12:00:00Z",
        "ttl_seconds": 1,
        "backend_ref": {"tenant_id": "tenant_1"},
        "extensions": {},
    }
    durable = {
        "memory_id": "mem_durable",
        "subject": {"kind": "user", "id": "user_123"},
        "scope": "user",
        "type": "semantic_fact",
        "content": {"statement": "Durable memory", "fact": "Durable memory"},
        "source": {"kind": "human", "ref": "chat:test"},
        "created_at": "2026-03-17T12:00:00Z",
        "backend_ref": {"tenant_id": "tenant_1"},
        "extensions": {},
    }

    adapter.write(expired)
    adapter.write(durable)

    active_ids = [memory["memory_id"] for memory in adapter.list_memories()]
    all_ids = [memory["memory_id"] for memory in adapter.list_memories(include_inactive=True)]

    assert active_ids == ["mem_durable"]
    assert all_ids == ["mem_durable", "mem_expired"]


def test_lancedb_dimension_mismatch_fails_fast(tmp_path):
    _require_lancedb()
    from adapters.lancedb import LanceDBAdapter

    adapter = LanceDBAdapter(
        db_dir=str(tmp_path / "lancedb"),
        embedding_provider="fake",
        embedding_model="mgp-fake-embedding-v1",
        embedding_dimension=8,
        hybrid_enabled=True,
    )
    adapter.write(
        {
            "memory_id": "mem_dim_guard",
            "subject": {"kind": "user", "id": "user_123"},
            "scope": "user",
            "type": "semantic_fact",
            "content": {"statement": "Dimension check", "fact": "Dimension check"},
            "source": {"kind": "human", "ref": "chat:test"},
            "created_at": "2026-03-17T12:00:00Z",
            "backend_ref": {"tenant_id": "tenant_1"},
            "extensions": {},
        }
    )

    with pytest.raises(RuntimeError, match="mismatch|contains embeddings"):
        LanceDBAdapter(
            db_dir=str(tmp_path / "lancedb"),
            embedding_provider="fake",
            embedding_model="mgp-fake-embedding-v2",
            embedding_dimension=16,
            hybrid_enabled=True,
        )
