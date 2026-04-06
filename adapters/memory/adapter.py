from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

from adapters.base import BaseAdapter
from adapters.memory_utils import apply_memory_patch, matches_memory_filters, normalize_mgp_memory
from adapters.search_utils import lexical_search_result, recall_terms


class InMemoryAdapter(BaseAdapter):
    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}
        self._manifest_path = Path(__file__).with_name("manifest.json")

    def write(self, memory: dict[str, Any]) -> dict[str, Any]:
        record = {
            "memory": self._normalize_memory(memory),
            "state": "active",
            "expired_at": None,
            "revoked_at": None,
            "deleted_at": None,
            "reason": None,
        }
        self._records[memory["memory_id"]] = record
        return copy.deepcopy(cast(dict[str, Any], record["memory"]))

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

        results: list[dict[str, Any]] = []

        for record in self._records.values():
            memory = record["memory"]
            if record["state"] in {"expired", "revoked", "deleted"}:
                continue
            if not matches_memory_filters(memory, subject=subject, scope=scope, types=types):
                continue

            result = lexical_search_result(
                memory,
                terms,
                retrieval_mode="lexical",
                explanation="Matched lexical terms against normalized memory content.",
            )
            if result is None:
                continue
            results.append(result)

        results.sort(key=lambda item: (item["score"], item["memory"]["memory_id"]), reverse=True)
        return results[:limit]

    def get(self, memory_id: str) -> dict[str, Any] | None:
        record = self._records.get(memory_id)
        if not record:
            return None
        return copy.deepcopy(record["memory"])

    def update(self, memory_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        record = self._records.get(memory_id)
        if not record:
            return None
        if record["state"] == "deleted":
            return None

        record["memory"] = self._normalize_memory(apply_memory_patch(record["memory"], patch))
        return copy.deepcopy(record["memory"])

    def expire(
        self,
        memory_id: str,
        expired_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        record = self._records.get(memory_id)
        if not record:
            return None
        record["state"] = "expired"
        record["expired_at"] = expired_at
        record["reason"] = reason
        record["memory"].setdefault("backend_ref", {})["mgp_state"] = "expired"
        return {"memory_id": memory_id, "state": "expired"}

    def revoke(
        self,
        memory_id: str,
        revoked_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        record = self._records.get(memory_id)
        if not record:
            return None
        record["state"] = "revoked"
        record["revoked_at"] = revoked_at
        record["reason"] = reason
        record["memory"].setdefault("backend_ref", {})["mgp_state"] = "revoked"
        return {"memory_id": memory_id, "state": "revoked"}

    def delete(
        self,
        memory_id: str,
        deleted_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        record = self._records.get(memory_id)
        if not record:
            return None
        record["state"] = "deleted"
        record["deleted_at"] = deleted_at
        record["reason"] = reason
        record["memory"].setdefault("backend_ref", {})["mgp_state"] = "deleted"
        return {"memory_id": memory_id, "state": "deleted"}

    def purge(
        self,
        memory_id: str,
        purged_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        if memory_id not in self._records:
            return None
        self._records.pop(memory_id, None)
        return {"memory_id": memory_id, "state": "purged", "purged_at": purged_at, "reason": reason}

    def list_memories(
        self,
        *,
        include_inactive: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        memories: list[dict[str, Any]] = []
        for record in self._records.values():
            if not include_inactive and record["state"] != "active":
                continue
            memories.append(copy.deepcopy(record["memory"]))
        memories.sort(key=lambda item: item["memory_id"])
        return memories if limit is None else memories[:limit]

    def get_manifest(self) -> dict[str, Any]:
        with self._manifest_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _normalize_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        return normalize_mgp_memory(memory, adapter_name="memory")
