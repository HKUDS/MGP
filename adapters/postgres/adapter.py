from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from adapters.base import BaseAdapter
from adapters.memory_utils import apply_memory_patch, normalize_mgp_memory
from adapters.search_utils import lexical_search_result, recall_terms, search_blob

try:  # pragma: no cover - optional dependency
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - optional dependency
    psycopg = None
    dict_row = None


class PostgresAdapter(BaseAdapter):
    """PostgreSQL-backed adapter intended as a production-oriented baseline."""

    def __init__(self, dsn: str | None = None) -> None:
        if psycopg is None or dict_row is None:
            raise RuntimeError("psycopg is required to use the postgres adapter.")

        self._dsn = dsn or os.getenv("MGP_POSTGRES_DSN")
        if not self._dsn:
            raise RuntimeError("MGP_POSTGRES_DSN is required to use the postgres adapter.")

        self._manifest_path = Path(__file__).with_name("manifest.json")
        self._migrations_dir = Path(__file__).with_name("migrations")
        self._connection = psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row)
        self._ensure_schema()

    def write(self, memory: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_memory(memory)
        self._upsert_memory(
            normalized,
            state="active",
            expired_at=None,
            revoked_at=None,
            deleted_at=None,
            reason=None,
        )
        return copy.deepcopy(normalized)

    def search(
        self,
        query: str,
        intent: dict[str, Any] | None = None,
        subject: dict[str, Any] | None = None,
        scope: str | None = None,
        types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        terms = recall_terms(query, intent)
        if not terms:
            return []

        clauses = ["state NOT IN ('expired', 'revoked', 'deleted')"]
        params: list[Any] = []

        search_clauses = []
        for term in terms:
            search_clauses.append("searchable_text ILIKE %s")
            params.append(f"%{term}%")
        clauses.append("(" + " OR ".join(search_clauses) + ")")

        if subject:
            clauses.append("subject_kind = %s AND subject_id = %s")
            params.extend([subject.get("kind"), subject.get("id")])
        if scope:
            clauses.append("scope = %s")
            params.append(scope)
        if types:
            placeholders = ", ".join("%s" for _ in types)
            clauses.append(f"type IN ({placeholders})")
            params.extend(types)

        sql = f"""
            SELECT memory_json
            FROM mgp_memories
            WHERE {" AND ".join(clauses)}
            ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST, memory_id ASC
            LIMIT %s
        """
        params.append(limit)

        with self._connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            memory = self._row_to_memory(row)
            result = lexical_search_result(
                memory,
                terms,
                retrieval_mode="lexical",
                explanation="Matched lexical terms against PostgreSQL-backed searchable text.",
                copy_memory=False,
            )
            if result is None:
                continue
            results.append(result)
        results.sort(key=lambda item: (item["score"], item["memory"]["memory_id"]), reverse=True)
        return results

    def get(self, memory_id: str) -> dict[str, Any] | None:
        with self._connection.cursor() as cursor:
            cursor.execute("SELECT memory_json FROM mgp_memories WHERE memory_id = %s", (memory_id,))
            row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_memory(row)

    def update(self, memory_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        current = self.get(memory_id)
        if not current:
            return None
        if current.get("backend_ref", {}).get("mgp_state") == "deleted":
            return None

        normalized = self._normalize_memory(apply_memory_patch(current, patch))
        state_fields = self._load_state_fields(memory_id)
        self._upsert_memory(normalized, **state_fields)
        return copy.deepcopy(normalized)

    def expire(
        self,
        memory_id: str,
        expired_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        return self._set_state(memory_id, "expired", expired_at=expired_at, reason=reason)

    def revoke(
        self,
        memory_id: str,
        revoked_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        return self._set_state(memory_id, "revoked", revoked_at=revoked_at, reason=reason)

    def delete(
        self,
        memory_id: str,
        deleted_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        return self._set_state(memory_id, "deleted", deleted_at=deleted_at, reason=reason)

    def purge(
        self,
        memory_id: str,
        purged_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        current = self.get(memory_id)
        if not current:
            return None
        with self._connection.cursor() as cursor:
            cursor.execute("DELETE FROM mgp_memories WHERE memory_id = %s", (memory_id,))
        return {"memory_id": memory_id, "state": "purged", "purged_at": purged_at, "reason": reason}

    def list_memories(
        self,
        *,
        include_inactive: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if not include_inactive:
            clauses.append("state = 'active'")

        sql = "SELECT memory_json FROM mgp_memories"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY memory_id ASC"
        if limit is not None:
            sql += " LIMIT %s"
            params.append(limit)

        with self._connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return [self._row_to_memory(row) for row in rows]

    def get_manifest(self) -> dict[str, Any]:
        with self._manifest_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _ensure_schema(self) -> None:
        migration_paths = sorted(self._migrations_dir.glob("*.sql"))
        with self._connection.cursor() as cursor:
            for migration_path in migration_paths:
                cursor.execute(migration_path.read_text(encoding="utf-8"))

    def _load_state_fields(self, memory_id: str) -> dict[str, Any]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT state, expired_at, revoked_at, deleted_at, reason
                FROM mgp_memories
                WHERE memory_id = %s
                """,
                (memory_id,),
            )
            row = cursor.fetchone()
        if not row:
            return {
                "state": "active",
                "expired_at": None,
                "revoked_at": None,
                "deleted_at": None,
                "reason": None,
            }
        return {
            "state": row["state"],
            "expired_at": self._serialize_timestamp(row["expired_at"]),
            "revoked_at": self._serialize_timestamp(row["revoked_at"]),
            "deleted_at": self._serialize_timestamp(row["deleted_at"]),
            "reason": row["reason"],
        }

    def _set_state(
        self,
        memory_id: str,
        state: str,
        *,
        expired_at: str | None = None,
        revoked_at: str | None = None,
        deleted_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        current = self.get(memory_id)
        if not current:
            return None

        normalized = self._normalize_memory(current)
        normalized.setdefault("backend_ref", {})["mgp_state"] = state
        state_fields = self._load_state_fields(memory_id)
        if expired_at is not None:
            state_fields["expired_at"] = expired_at
        if revoked_at is not None:
            state_fields["revoked_at"] = revoked_at
        if deleted_at is not None:
            state_fields["deleted_at"] = deleted_at
        state_fields["state"] = state
        state_fields["reason"] = reason
        self._upsert_memory(normalized, **state_fields)
        return {
            "memory_id": memory_id,
            "state": state,
            "reason": reason,
            "expired_at": expired_at,
            "revoked_at": revoked_at,
            "deleted_at": deleted_at,
        }

    def _upsert_memory(
        self,
        memory: dict[str, Any],
        *,
        state: str,
        expired_at: str | None,
        revoked_at: str | None,
        deleted_at: str | None,
        reason: str | None,
    ) -> None:
        tenant_id = self._tenant_id_for_memory(memory)
        searchable_text = search_blob(memory)
        payload = json.dumps(memory, ensure_ascii=False)

        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO mgp_memories (
                    memory_id,
                    tenant_id,
                    subject_kind,
                    subject_id,
                    scope,
                    type,
                    state,
                    searchable_text,
                    memory_json,
                    created_at,
                    updated_at,
                    expired_at,
                    revoked_at,
                    deleted_at,
                    reason
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s::jsonb,
                    NULLIF(%s, '')::timestamptz,
                    NULLIF(%s, '')::timestamptz,
                    NULLIF(%s, '')::timestamptz,
                    NULLIF(%s, '')::timestamptz,
                    NULLIF(%s, '')::timestamptz,
                    %s
                )
                ON CONFLICT (memory_id) DO UPDATE SET
                    tenant_id = EXCLUDED.tenant_id,
                    subject_kind = EXCLUDED.subject_kind,
                    subject_id = EXCLUDED.subject_id,
                    scope = EXCLUDED.scope,
                    type = EXCLUDED.type,
                    state = EXCLUDED.state,
                    searchable_text = EXCLUDED.searchable_text,
                    memory_json = EXCLUDED.memory_json,
                    created_at = COALESCE(EXCLUDED.created_at, mgp_memories.created_at),
                    updated_at = COALESCE(EXCLUDED.updated_at, mgp_memories.updated_at),
                    expired_at = EXCLUDED.expired_at,
                    revoked_at = EXCLUDED.revoked_at,
                    deleted_at = EXCLUDED.deleted_at,
                    reason = EXCLUDED.reason
                """,
                (
                    memory["memory_id"],
                    tenant_id,
                    memory.get("subject", {}).get("kind"),
                    memory.get("subject", {}).get("id"),
                    memory.get("scope"),
                    memory.get("type"),
                    state,
                    searchable_text,
                    payload,
                    memory.get("created_at") or "",
                    memory.get("updated_at") or "",
                    expired_at or "",
                    revoked_at or "",
                    deleted_at or "",
                    reason,
                ),
            )

    def _row_to_memory(self, row: dict[str, Any]) -> dict[str, Any]:
        memory_raw = row["memory_json"]
        if isinstance(memory_raw, str):
            memory = json.loads(memory_raw)
        else:
            memory = copy.deepcopy(memory_raw)
        memory.setdefault("backend_ref", {})["adapter"] = "postgres"
        memory["backend_ref"]["mgp_state"] = row.get("state", memory["backend_ref"].get("mgp_state", "active"))
        return memory

    def _normalize_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        return normalize_mgp_memory(memory, adapter_name="postgres")

    def _tenant_id_for_memory(self, memory: dict[str, Any]) -> str | None:
        backend_ref = memory.get("backend_ref", {})
        extensions = memory.get("extensions", {})
        return backend_ref.get("tenant_id") or extensions.get("mgp:tenant_id")

    def _serialize_timestamp(self, value: Any) -> str | None:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat().replace("+00:00", "Z")
        return str(value)
