from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from sqlalchemy import text

from adapters.base import BaseAdapter
from adapters.memory_utils import apply_memory_patch, normalize_mgp_memory
from adapters.search_utils import lexical_search_result, recall_terms

try:  # pragma: no cover - optional dependency
    from pyobvector import ObVecClient
except Exception:  # pragma: no cover - optional dependency
    ObVecClient = None


class OceanBaseAdapter(BaseAdapter):
    """OceanBase-backed adapter using pyobvector's SQLAlchemy-compatible client."""

    def __init__(
        self,
        *,
        dsn: str | None = None,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        tenant: str | None = None,
    ) -> None:
        if ObVecClient is None:
            raise RuntimeError(
                "pyobvector is required to use the oceanbase adapter. "
                "Install it with: pip install pyobvector sqlglot==26.0.1"
            )

        connection = self._resolve_connection_settings(
            dsn=dsn,
            uri=uri,
            user=user,
            password=password,
            database=database,
            tenant=tenant,
        )
        self._manifest_path = Path(__file__).with_name("manifest.json")
        self._client = ObVecClient(
            uri=connection["uri"],
            user=self._qualified_user(connection["user"], connection["tenant"]),
            password=connection["password"],
            db_name=connection["database"],
        )
        self._engine = self._client.engine
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
        params: dict[str, Any] = {"limit": limit}

        search_clauses: list[str] = []
        for index, term in enumerate(terms):
            key = f"term_{index}"
            search_clauses.append(f"LOWER(searchable_text) LIKE :{key}")
            params[key] = f"%{term.lower()}%"
        clauses.append("(" + " OR ".join(search_clauses) + ")")

        if subject:
            clauses.append("subject_kind = :subject_kind AND subject_id = :subject_id")
            params["subject_kind"] = subject.get("kind")
            params["subject_id"] = subject.get("id")
        if scope:
            clauses.append("scope = :scope")
            params["scope"] = scope
        if types:
            type_placeholders: list[str] = []
            for index, memory_type in enumerate(types):
                key = f"type_{index}"
                type_placeholders.append(f":{key}")
                params[key] = memory_type
            clauses.append("type IN (" + ", ".join(type_placeholders) + ")")

        rows = self._fetchall(
            f"""
            SELECT memory_json, state
            FROM mgp_memories
            WHERE {" AND ".join(clauses)}
            ORDER BY memory_id ASC
            LIMIT :limit
            """,
            params,
        )

        results: list[dict[str, Any]] = []
        for row in rows:
            memory = self._row_to_memory(row)
            result = lexical_search_result(
                memory,
                terms,
                retrieval_mode="lexical",
                explanation="Matched lexical terms against OceanBase searchable text.",
                copy_memory=False,
            )
            if result is None:
                continue
            results.append(result)
        return results

    def get(self, memory_id: str) -> dict[str, Any] | None:
        row = self._fetchone(
            """
            SELECT memory_json, state
            FROM mgp_memories
            WHERE memory_id = :memory_id
            """,
            {"memory_id": memory_id},
        )
        if row is None:
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
        self._execute(
            "DELETE FROM mgp_memories WHERE memory_id = :memory_id",
            {"memory_id": memory_id},
        )
        return {"memory_id": memory_id, "state": "purged", "purged_at": purged_at, "reason": reason}

    def list_memories(
        self,
        *,
        include_inactive: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: dict[str, Any] = {}
        if not include_inactive:
            clauses.append("state = 'active'")

        sql = "SELECT memory_json, state FROM mgp_memories"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY memory_id ASC"
        if limit is not None:
            sql += " LIMIT :limit"
            params["limit"] = limit

        rows = self._fetchall(sql, params)
        return [self._row_to_memory(row) for row in rows]

    def get_manifest(self) -> dict[str, Any]:
        with self._manifest_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _resolve_connection_settings(
        self,
        *,
        dsn: str | None,
        uri: str | None,
        user: str | None,
        password: str | None,
        database: str | None,
        tenant: str | None,
    ) -> dict[str, str]:
        resolved_dsn = dsn or os.getenv("MGP_OCEANBASE_DSN")
        if resolved_dsn:
            parsed = self._parse_dsn(resolved_dsn)
            uri = uri or parsed["uri"]
            user = user or parsed["user"]
            password = password if password is not None else parsed["password"]
            database = database or parsed["database"]
            tenant = tenant or parsed["tenant"]

        resolved_uri = uri or os.getenv("MGP_OCEANBASE_URI") or "127.0.0.1:2881"
        resolved_user = user or os.getenv("MGP_OCEANBASE_USER") or "root"
        if password is not None:
            resolved_password = password
        else:
            resolved_password = os.getenv("MGP_OCEANBASE_PASSWORD", "")
        resolved_database = database or os.getenv("MGP_OCEANBASE_DATABASE") or "test"
        resolved_tenant = tenant or os.getenv("MGP_OCEANBASE_TENANT") or "sys"
        return {
            "uri": resolved_uri,
            "user": resolved_user,
            "password": resolved_password,
            "database": resolved_database,
            "tenant": resolved_tenant,
        }

    def _parse_dsn(self, dsn: str) -> dict[str, str]:
        parsed = urlparse(dsn)
        if not parsed.hostname:
            raise RuntimeError("MGP_OCEANBASE_DSN must include a hostname.")
        query = parse_qs(parsed.query)
        tenant = query.get("tenant", ["sys"])[0]
        database = parsed.path.lstrip("/") or "test"
        uri = f"{parsed.hostname}:{parsed.port or 2881}"
        username = unquote(parsed.username or "root")
        password = unquote(parsed.password or "")
        if "@" in username and "tenant" not in query:
            user_name, tenant_name = username.rsplit("@", 1)
            username = user_name
            tenant = tenant_name
        return {
            "uri": uri,
            "user": username,
            "password": password,
            "database": database,
            "tenant": tenant,
        }

    def _qualified_user(self, user: str, tenant: str) -> str:
        if "@" in user:
            return user
        return f"{user}@{tenant}"

    def _ensure_schema(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS mgp_memories (
                memory_id VARCHAR(191) PRIMARY KEY,
                tenant_id VARCHAR(191) NULL,
                subject_kind VARCHAR(64) NOT NULL,
                subject_id VARCHAR(191) NOT NULL,
                scope VARCHAR(64) NOT NULL,
                type VARCHAR(64) NOT NULL,
                state VARCHAR(32) NOT NULL,
                searchable_text TEXT NOT NULL,
                memory_json LONGTEXT NOT NULL,
                created_at VARCHAR(64) NULL,
                updated_at VARCHAR(64) NULL,
                expired_at VARCHAR(64) NULL,
                revoked_at VARCHAR(64) NULL,
                deleted_at VARCHAR(64) NULL,
                reason TEXT NULL
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS mgp_memories_tenant_state_idx
            ON mgp_memories (tenant_id, state)
            """,
            """
            CREATE INDEX IF NOT EXISTS mgp_memories_subject_idx
            ON mgp_memories (subject_kind, subject_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS mgp_memories_scope_type_idx
            ON mgp_memories (scope, type)
            """,
            """
            CREATE INDEX IF NOT EXISTS mgp_memories_created_idx
            ON mgp_memories (created_at)
            """,
        ]
        for statement in statements:
            self._execute(statement)

    def _load_state_fields(self, memory_id: str) -> dict[str, Any]:
        row = self._fetchone(
            """
            SELECT state, expired_at, revoked_at, deleted_at, reason
            FROM mgp_memories
            WHERE memory_id = :memory_id
            """,
            {"memory_id": memory_id},
        )
        if row is None:
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
        searchable_text = self._searchable_text(memory)
        payload = json.dumps(memory, ensure_ascii=False)

        self._execute(
            """
            REPLACE INTO mgp_memories (
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
                :memory_id,
                :tenant_id,
                :subject_kind,
                :subject_id,
                :scope,
                :type,
                :state,
                :searchable_text,
                :memory_json,
                :created_at,
                :updated_at,
                :expired_at,
                :revoked_at,
                :deleted_at,
                :reason
            )
            """,
            {
                "memory_id": memory["memory_id"],
                "tenant_id": tenant_id,
                "subject_kind": memory.get("subject", {}).get("kind"),
                "subject_id": memory.get("subject", {}).get("id"),
                "scope": memory.get("scope"),
                "type": memory.get("type"),
                "state": state,
                "searchable_text": searchable_text,
                "memory_json": payload,
                "created_at": memory.get("created_at"),
                "updated_at": memory.get("updated_at"),
                "expired_at": expired_at,
                "revoked_at": revoked_at,
                "deleted_at": deleted_at,
                "reason": reason,
            },
        )

    def _row_to_memory(self, row: dict[str, Any]) -> dict[str, Any]:
        memory_raw = row["memory_json"]
        if isinstance(memory_raw, str):
            memory = json.loads(memory_raw)
        else:
            memory = copy.deepcopy(memory_raw)
        memory.setdefault("backend_ref", {})["adapter"] = "oceanbase"
        memory["backend_ref"]["mgp_state"] = row.get("state", memory["backend_ref"].get("mgp_state", "active"))
        return memory

    def _normalize_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        return normalize_mgp_memory(memory, adapter_name="oceanbase")

    def _tenant_id_for_memory(self, memory: dict[str, Any]) -> str | None:
        backend_ref = memory.get("backend_ref", {})
        extensions = memory.get("extensions", {})
        return backend_ref.get("tenant_id") or extensions.get("mgp:tenant_id")

    def _searchable_text(self, memory: dict[str, Any]) -> str:
        content_json = json.dumps(memory.get("content", {}), ensure_ascii=False).lower()
        memory_id = str(memory.get("memory_id", "")).lower()
        return f"{content_json} {memory_id}".strip()

    def _serialize_timestamp(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if hasattr(value, "isoformat"):
            return value.isoformat().replace("+00:00", "Z")
        return str(value)

    def _execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        with self._engine.connect() as connection:
            with connection.begin():
                connection.execute(text(sql), params or {})

    def _fetchall(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self._engine.connect() as connection:
            with connection.begin():
                result = connection.execute(text(sql), params or {})
                return [dict(row) for row in result.mappings().all()]

    def _fetchone(self, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        rows = self._fetchall(sql, params)
        if not rows:
            return None
        return rows[0]
