from __future__ import annotations

import copy
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from adapters.base import BaseAdapter
from adapters.memory_utils import apply_memory_patch, normalize_mgp_memory
from adapters.search_utils import build_search_result_item, memory_matches_terms, recall_terms, search_score


class GraphAdapter(BaseAdapter):
    """SQLite-backed reference adapter for graph and relationship memories."""

    def __init__(self, db_path: str | None = None) -> None:
        configured_path = db_path or os.getenv("MGP_GRAPH_DB_PATH")
        self._db_path = Path(configured_path or Path(__file__).with_name("graph.db"))
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._manifest_path = Path(__file__).with_name("manifest.json")
        self._connection = sqlite3.connect(str(self._db_path))
        self._connection.row_factory = sqlite3.Row
        self._ensure_schema()

    def write(self, memory: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_memory(memory)
        self._upsert_memory(normalized, state="active", expired_at=None, revoked_at=None, deleted_at=None, reason=None)
        self._replace_edges(normalized)
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

        like_clauses = []
        params: list[Any] = []
        for term in terms:
            like_clauses.append("(lower(content_json) LIKE ? OR lower(memory_id) LIKE ?)")
            params.extend([f"%{term.lower()}%", f"%{term.lower()}%"])

        clauses = ["state NOT IN ('expired', 'revoked', 'deleted')", "(" + " OR ".join(like_clauses) + ")"]

        if subject:
            clauses.append("subject_kind = ? AND subject_id = ?")
            params.extend([subject.get("kind"), subject.get("id")])
        if scope:
            clauses.append("scope = ?")
            params.append(scope)
        if types:
            placeholders = ", ".join("?" for _ in types)
            clauses.append(f"type IN ({placeholders})")
            params.extend(types)

        sql = f"""
            SELECT *
            FROM memories
            WHERE {" AND ".join(clauses)}
            ORDER BY memory_id ASC
            LIMIT ?
        """
        params.append(limit)

        results: list[dict[str, Any]] = []
        for row in self._connection.execute(sql, params):
            memory = self._row_to_memory(row)
            matches = memory_matches_terms(memory, terms)
            results.append(
                build_search_result_item(
                    memory,
                    score=search_score(matches, terms),
                    retrieval_mode="graph" if memory.get("type") == "relationship" else "lexical",
                    term_matches=matches,
                    explanation="Matched lexical terms against SQLite-backed graph memory rows.",
                )
            )
        return results

    def get(self, memory_id: str) -> dict[str, Any] | None:
        row = self._connection.execute(
            "SELECT * FROM memories WHERE memory_id = ?",
            (memory_id,),
        ).fetchone()
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
        row = self._connection.execute(
            "SELECT state, expired_at, revoked_at, deleted_at, reason FROM memories WHERE memory_id = ?",
            (memory_id,),
        ).fetchone()
        self._upsert_memory(
            normalized,
            state=row["state"],
            expired_at=row["expired_at"],
            revoked_at=row["revoked_at"],
            deleted_at=row["deleted_at"],
            reason=row["reason"],
        )
        self._replace_edges(normalized)
        return copy.deepcopy(normalized)

    def expire(
        self,
        memory_id: str,
        expired_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        current = self.get(memory_id)
        if not current:
            return None
        self._connection.execute(
            "UPDATE memories SET state = 'expired', expired_at = ?, reason = ? WHERE memory_id = ?",
            (expired_at, reason, memory_id),
        )
        self._connection.commit()
        return {"memory_id": memory_id, "state": "expired"}

    def revoke(
        self,
        memory_id: str,
        revoked_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        current = self.get(memory_id)
        if not current:
            return None
        self._connection.execute(
            "UPDATE memories SET state = 'revoked', revoked_at = ?, reason = ? WHERE memory_id = ?",
            (revoked_at, reason, memory_id),
        )
        self._connection.commit()
        return {"memory_id": memory_id, "state": "revoked"}

    def delete(
        self,
        memory_id: str,
        deleted_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        current = self.get(memory_id)
        if not current:
            return None
        self._connection.execute(
            "UPDATE memories SET state = 'deleted', deleted_at = ?, reason = ? WHERE memory_id = ?",
            (deleted_at, reason, memory_id),
        )
        self._connection.commit()
        return {"memory_id": memory_id, "state": "deleted"}

    def purge(
        self,
        memory_id: str,
        purged_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        current = self.get(memory_id)
        if not current:
            return None
        self._connection.execute(
            "DELETE FROM edges WHERE source_memory_id = ? OR target_memory_id = ?",
            (memory_id, memory_id),
        )
        self._connection.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
        self._connection.commit()
        return {"memory_id": memory_id, "state": "purged", "purged_at": purged_at, "reason": reason}

    def list_memories(
        self,
        *,
        include_inactive: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM memories"
        params: list[Any] = []
        if not include_inactive:
            sql += " WHERE state = 'active'"
        sql += " ORDER BY memory_id ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        return [self._row_to_memory(row) for row in self._connection.execute(sql, params)]

    def get_manifest(self) -> dict[str, Any]:
        with self._manifest_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _ensure_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                subject_kind TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                scope TEXT NOT NULL,
                type TEXT NOT NULL,
                content_json TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                confidence REAL,
                sensitivity TEXT,
                retention_policy TEXT,
                ttl_seconds INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                valid_from TEXT,
                valid_to TEXT,
                backend_ref_json TEXT NOT NULL,
                extensions_json TEXT NOT NULL,
                state TEXT NOT NULL,
                expired_at TEXT,
                revoked_at TEXT,
                deleted_at TEXT,
                reason TEXT
            );

            CREATE TABLE IF NOT EXISTS edges (
                edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_memory_id TEXT NOT NULL,
                target_memory_id TEXT NOT NULL,
                relation TEXT,
                edge_type TEXT,
                metadata_json TEXT NOT NULL
            );
            """
        )
        self._ensure_column("memories", "deleted_at", "TEXT")
        self._connection.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        existing = {row["name"] for row in self._connection.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            self._connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            self._connection.commit()

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
        backend_ref = copy.deepcopy(memory.get("backend_ref", {}))
        backend_ref.setdefault("adapter", "graph")
        backend_ref["mgp_state"] = state
        self._connection.execute(
            """
            INSERT OR REPLACE INTO memories (
                memory_id, subject_kind, subject_id, scope, type, content_json,
                source_kind, source_ref, confidence, sensitivity, retention_policy,
                ttl_seconds, created_at, updated_at, valid_from, valid_to,
                backend_ref_json, extensions_json, state, expired_at, revoked_at, deleted_at, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory["memory_id"],
                memory["subject"]["kind"],
                memory["subject"]["id"],
                memory["scope"],
                memory["type"],
                json.dumps(memory.get("content", {}), ensure_ascii=False),
                memory["source"]["kind"],
                memory["source"]["ref"],
                memory.get("confidence"),
                memory.get("sensitivity"),
                memory.get("retention_policy"),
                memory.get("ttl_seconds"),
                memory["created_at"],
                memory.get("updated_at"),
                memory.get("valid_from"),
                memory.get("valid_to"),
                json.dumps(backend_ref, ensure_ascii=False),
                json.dumps(memory.get("extensions", {}), ensure_ascii=False),
                state,
                expired_at,
                revoked_at,
                deleted_at,
                reason,
            ),
        )
        self._connection.commit()

    def _replace_edges(self, memory: dict[str, Any]) -> None:
        self._connection.execute("DELETE FROM edges WHERE source_memory_id = ?", (memory["memory_id"],))
        extensions = memory.get("extensions", {})
        target_memory_id = extensions.get("graph:target_memory_id")
        relation = extensions.get("graph:relation")
        edge_type = extensions.get("graph:edge_type")

        if target_memory_id:
            metadata = {
                "memory_type": memory.get("type"),
                "scope": memory.get("scope"),
            }
            self._connection.execute(
                """
                INSERT INTO edges (source_memory_id, target_memory_id, relation, edge_type, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    memory["memory_id"],
                    target_memory_id,
                    relation,
                    edge_type,
                    json.dumps(metadata, ensure_ascii=False),
                ),
            )
        self._connection.commit()

    def _row_to_memory(self, row: sqlite3.Row) -> dict[str, Any]:
        backend_ref = json.loads(row["backend_ref_json"])
        backend_ref["adapter"] = "graph"
        backend_ref["mgp_state"] = row["state"]

        memory: dict[str, Any] = {
            "memory_id": row["memory_id"],
            "subject": {"kind": row["subject_kind"], "id": row["subject_id"]},
            "scope": row["scope"],
            "type": row["type"],
            "content": json.loads(row["content_json"]),
            "source": {"kind": row["source_kind"], "ref": row["source_ref"]},
            "created_at": row["created_at"],
            "backend_ref": backend_ref,
            "extensions": json.loads(row["extensions_json"]),
        }

        optional_fields = {
            "confidence": row["confidence"],
            "sensitivity": row["sensitivity"],
            "retention_policy": row["retention_policy"],
            "ttl_seconds": row["ttl_seconds"],
            "updated_at": row["updated_at"],
            "valid_from": row["valid_from"],
            "valid_to": row["valid_to"],
        }
        for key, value in optional_fields.items():
            if value is not None:
                memory[key] = value

        return memory

    def _normalize_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        return normalize_mgp_memory(memory, adapter_name="graph")
