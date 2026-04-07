from __future__ import annotations

import importlib.util
import os
from urllib.parse import parse_qs, unquote, urlparse
from uuid import uuid4

import pymysql
import pytest


def _require_oceanbase() -> None:
    if importlib.util.find_spec("pyobvector") is None:
        pytest.skip("pyobvector is not installed")
    if not (os.getenv("MGP_OCEANBASE_DSN") or os.getenv("MGP_OCEANBASE_URI")):
        pytest.skip("oceanbase-specific tests require MGP_OCEANBASE_DSN or MGP_OCEANBASE_URI")


def _oceanbase_settings() -> dict[str, object]:
    dsn = os.getenv("MGP_OCEANBASE_DSN")
    if dsn:
        parsed = urlparse(dsn)
        if not parsed.hostname:
            raise RuntimeError("MGP_OCEANBASE_DSN must include a hostname")
        query = parse_qs(parsed.query)
        username = unquote(parsed.username or "root")
        tenant = query.get("tenant", [os.getenv("MGP_OCEANBASE_TENANT") or "sys"])[0]
        if "@" in username and "tenant" not in query:
            username, tenant = username.rsplit("@", 1)
        return {
            "uri": f"{parsed.hostname}:{parsed.port or 2881}",
            "host": parsed.hostname,
            "port": parsed.port or 2881,
            "user": username,
            "tenant": tenant,
            "password": unquote(parsed.password or ""),
            "database": parsed.path.lstrip("/") or os.getenv("MGP_OCEANBASE_DATABASE") or "test",
        }

    raw_uri = os.getenv("MGP_OCEANBASE_URI", "127.0.0.1:2881")
    host, _, port_text = raw_uri.partition(":")
    return {
        "uri": raw_uri,
        "host": host or "127.0.0.1",
        "port": int(port_text or "2881"),
        "user": os.getenv("MGP_OCEANBASE_USER", "root"),
        "tenant": os.getenv("MGP_OCEANBASE_TENANT", "sys"),
        "password": os.getenv("MGP_OCEANBASE_PASSWORD", ""),
        "database": os.getenv("MGP_OCEANBASE_DATABASE", "test"),
    }


@pytest.fixture
def oceanbase_adapter():
    _require_oceanbase()
    from adapters.oceanbase import OceanBaseAdapter

    settings = _oceanbase_settings()
    database_name = f"{settings['database']}_adapter_{uuid4().hex[:8]}"
    connection = pymysql.connect(
        host=str(settings["host"]),
        port=int(settings["port"]),
        user=f"{settings['user']}@{settings['tenant']}",
        password=str(settings["password"]),
        charset="utf8mb4",
        autocommit=True,
    )
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database_name}`")
    connection.close()

    adapter = OceanBaseAdapter(
        uri=str(settings["uri"]),
        user=str(settings["user"]),
        password=str(settings["password"]),
        tenant=str(settings["tenant"]),
        database=database_name,
    )
    created_ids: list[str] = []
    try:
        yield adapter, created_ids
    finally:
        for memory_id in created_ids:
            adapter.purge(memory_id)
        connection = pymysql.connect(
            host=str(settings["host"]),
            port=int(settings["port"]),
            user=f"{settings['user']}@{settings['tenant']}",
            password=str(settings["password"]),
            charset="utf8mb4",
            autocommit=True,
        )
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{database_name}`")
        connection.close()


def _memory(*, memory_id: str, subject_id: str, scope: str, memory_type: str, statement: str) -> dict[str, object]:
    return {
        "memory_id": memory_id,
        "subject": {"kind": "user", "id": subject_id},
        "scope": scope,
        "type": memory_type,
        "content": {
            "statement": statement,
            "summary": statement,
        },
        "source": {"kind": "human", "ref": "chat:test"},
        "created_at": "2026-03-17T12:00:00Z",
        "updated_at": "2026-03-17T12:00:00Z",
        "backend_ref": {"tenant_id": "tenant_oceanbase_test"},
        "extensions": {},
    }


def _normalized_memory(memory: dict[str, object] | None) -> dict[str, object] | None:
    if memory is None:
        return None
    copied = dict(memory)
    backend_ref = dict(copied.get("backend_ref", {}))
    backend_ref.pop("adapter", None)
    copied["backend_ref"] = backend_ref
    return copied


def test_oceanbase_upsert_keeps_single_row(oceanbase_adapter):
    adapter, created_ids = oceanbase_adapter
    memory_id = f"mem_oceanbase_upsert_{uuid4().hex}"
    created_ids.append(memory_id)

    first = _memory(
        memory_id=memory_id,
        subject_id="user_oceanbase_upsert",
        scope="user",
        memory_type="semantic_fact",
        statement="oceanbase-upsert-token first version",
    )
    second = _memory(
        memory_id=memory_id,
        subject_id="user_oceanbase_upsert",
        scope="user",
        memory_type="semantic_fact",
        statement="oceanbase-upsert-token updated version",
    )
    second["updated_at"] = "2026-03-17T12:30:00Z"

    adapter.write(first)
    adapter.write(second)

    stored = adapter.get(memory_id)
    assert stored is not None
    assert stored["content"]["statement"] == "oceanbase-upsert-token updated version"

    all_memories = adapter.list_memories(include_inactive=True)
    assert sum(memory["memory_id"] == memory_id for memory in all_memories) == 1


def test_oceanbase_list_memories_hides_inactive_by_default(oceanbase_adapter):
    adapter, created_ids = oceanbase_adapter
    active_id = f"mem_oceanbase_active_{uuid4().hex}"
    expired_id = f"mem_oceanbase_expired_{uuid4().hex}"
    created_ids.extend([active_id, expired_id])

    adapter.write(
        _memory(
            memory_id=active_id,
            subject_id="user_oceanbase_states",
            scope="user",
            memory_type="profile",
            statement="oceanbase-state-token active",
        )
    )
    adapter.write(
        _memory(
            memory_id=expired_id,
            subject_id="user_oceanbase_states",
            scope="user",
            memory_type="profile",
            statement="oceanbase-state-token expired",
        )
    )
    adapter.expire(expired_id, expired_at="2026-03-18T00:00:00Z", reason="ttl")

    active_ids = {memory["memory_id"] for memory in adapter.list_memories()}
    all_ids = {memory["memory_id"] for memory in adapter.list_memories(include_inactive=True)}

    assert active_id in active_ids
    assert expired_id not in active_ids
    assert {active_id, expired_id}.issubset(all_ids)


def test_oceanbase_search_applies_subject_scope_and_type_filters(oceanbase_adapter):
    adapter, created_ids = oceanbase_adapter
    matching_id = f"mem_oceanbase_match_{uuid4().hex}"
    other_subject_id = f"mem_oceanbase_other_subject_{uuid4().hex}"
    other_type_id = f"mem_oceanbase_other_type_{uuid4().hex}"
    created_ids.extend([matching_id, other_subject_id, other_type_id])

    shared_token = f"oceanbase-filter-token-{uuid4().hex}"
    adapter.write(
        _memory(
            memory_id=matching_id,
            subject_id="user_oceanbase_target",
            scope="user",
            memory_type="semantic_fact",
            statement=f"{shared_token} target memory",
        )
    )
    adapter.write(
        _memory(
            memory_id=other_subject_id,
            subject_id="user_oceanbase_other",
            scope="user",
            memory_type="semantic_fact",
            statement=f"{shared_token} other subject",
        )
    )
    adapter.write(
        _memory(
            memory_id=other_type_id,
            subject_id="user_oceanbase_target",
            scope="user",
            memory_type="profile",
            statement=f"{shared_token} other type",
        )
    )

    results = adapter.search(
        query=shared_token,
        subject={"kind": "user", "id": "user_oceanbase_target"},
        scope="user",
        types=["semantic_fact"],
        limit=10,
    )

    assert [result["memory"]["memory_id"] for result in results] == [matching_id]


def test_oceanbase_matches_graph_adapter_on_shared_operations(oceanbase_adapter, tmp_path):
    adapter, created_ids = oceanbase_adapter
    from adapters.graph import GraphAdapter

    graph = GraphAdapter(db_path=str(tmp_path / "graph.db"))
    memory_id = f"mem_oceanbase_parity_{uuid4().hex}"
    created_ids.append(memory_id)

    memory = _memory(
        memory_id=memory_id,
        subject_id="user_oceanbase_parity",
        scope="user",
        memory_type="preference",
        statement="oceanbase sqlite parity token",
    )
    memory["updated_at"] = "2026-03-17T12:30:00Z"
    memory["sensitivity"] = "internal"
    memory["retention_policy"] = "persistent"

    graph.write(memory)
    adapter.write(memory)

    assert _normalized_memory(graph.get(memory_id)) == _normalized_memory(adapter.get(memory_id))

    patch = {"content": {"statement": "oceanbase sqlite parity updated", "theme": "light"}}
    graph_updated = graph.update(memory_id, patch)
    oceanbase_updated = adapter.update(memory_id, patch)
    assert _normalized_memory(graph_updated) == _normalized_memory(oceanbase_updated)

    graph_type_search = graph.search("preference", limit=10)
    oceanbase_type_search = adapter.search("preference", limit=10)
    assert graph_type_search == []
    assert oceanbase_type_search == []

    graph_search = graph.search("parity updated", limit=10)
    oceanbase_search = adapter.search("parity updated", limit=10)
    assert [item["memory"]["memory_id"] for item in graph_search] == [
        item["memory"]["memory_id"] for item in oceanbase_search
    ]
    assert [item["matched_terms"] for item in graph_search] == [item["matched_terms"] for item in oceanbase_search]
    assert [item["retrieval_mode"] for item in graph_search] == [item["retrieval_mode"] for item in oceanbase_search]
    assert [item["score"] for item in graph_search] == [item["score"] for item in oceanbase_search]

    assert graph.expire(memory_id, reason="ttl") == adapter.expire(memory_id, reason="ttl")
    assert [memory["memory_id"] for memory in graph.list_memories()] == [
        memory["memory_id"] for memory in adapter.list_memories()
    ]
    assert [memory["memory_id"] for memory in graph.list_memories(include_inactive=True)] == [
        memory["memory_id"] for memory in adapter.list_memories(include_inactive=True)
    ]
