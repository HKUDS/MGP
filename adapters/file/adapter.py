from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from adapters.base import BaseAdapter
from adapters.memory_utils import apply_memory_patch, matches_memory_filters, normalize_mgp_memory
from adapters.search_utils import lexical_search_result, recall_terms


class FileAdapter(BaseAdapter):
    def __init__(self, storage_dir: str | None = None) -> None:
        configured_dir = storage_dir or os.getenv("MGP_FILE_STORAGE_DIR")
        self._storage_dir = Path(configured_dir or Path(__file__).with_name("data"))
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path = Path(__file__).with_name("manifest.json")

    def write(self, memory: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_memory(memory)
        record = {
            "memory": normalized,
            "state": "active",
            "expired_at": None,
            "revoked_at": None,
            "deleted_at": None,
            "reason": None,
        }
        self._write_record(memory["memory_id"], record)
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

        results: list[dict[str, Any]] = []

        for record in self._iter_records():
            if record["state"] in {"expired", "revoked", "deleted"}:
                continue

            memory = record["memory"]
            if not matches_memory_filters(memory, subject=subject, scope=scope, types=types):
                continue

            result = lexical_search_result(
                memory,
                terms,
                retrieval_mode="lexical",
                explanation="Matched lexical terms against serialized file-backed memory content.",
            )
            if result is None:
                continue
            results.append(result)

        results.sort(key=lambda item: (item["score"], item["memory"]["memory_id"]), reverse=True)
        return results[:limit]

    def get(self, memory_id: str) -> dict[str, Any] | None:
        record = self._read_record(memory_id)
        if not record:
            return None
        return copy.deepcopy(record["memory"])

    def update(self, memory_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        record = self._read_record(memory_id)
        if not record:
            return None
        if record["state"] == "deleted":
            return None

        record["memory"] = self._normalize_memory(apply_memory_patch(record["memory"], patch))
        self._write_record(memory_id, record)
        return copy.deepcopy(record["memory"])

    def expire(
        self,
        memory_id: str,
        expired_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        record = self._read_record(memory_id)
        if not record:
            return None
        record["state"] = "expired"
        record["expired_at"] = expired_at
        record["reason"] = reason
        record["memory"].setdefault("backend_ref", {})["mgp_state"] = "expired"
        self._write_record(memory_id, record)
        return {"memory_id": memory_id, "state": "expired"}

    def revoke(
        self,
        memory_id: str,
        revoked_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        record = self._read_record(memory_id)
        if not record:
            return None
        record["state"] = "revoked"
        record["revoked_at"] = revoked_at
        record["reason"] = reason
        record["memory"].setdefault("backend_ref", {})["mgp_state"] = "revoked"
        self._write_record(memory_id, record)
        return {"memory_id": memory_id, "state": "revoked"}

    def delete(
        self,
        memory_id: str,
        deleted_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        record = self._read_record(memory_id)
        if not record:
            return None
        record["state"] = "deleted"
        record["deleted_at"] = deleted_at
        record["reason"] = reason
        record["memory"].setdefault("backend_ref", {})["mgp_state"] = "deleted"
        self._write_record(memory_id, record)
        return {"memory_id": memory_id, "state": "deleted"}

    def purge(
        self,
        memory_id: str,
        purged_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        path = self._record_path(memory_id)
        if not path.exists():
            return None
        path.unlink()
        return {"memory_id": memory_id, "state": "purged", "purged_at": purged_at, "reason": reason}

    def list_memories(
        self,
        *,
        include_inactive: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for record in self._iter_records():
            if not include_inactive and record["state"] != "active":
                continue
            items.append(copy.deepcopy(record["memory"]))
        items.sort(key=lambda item: item["memory_id"])
        return items if limit is None else items[:limit]

    def get_manifest(self) -> dict[str, Any]:
        with self._manifest_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _record_path(self, memory_id: str) -> Path:
        return self._storage_dir / f"{memory_id}.json"

    def _write_record(self, memory_id: str, record: dict[str, Any]) -> None:
        path = self._record_path(memory_id)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, indent=2)

    def _read_record(self, memory_id: str) -> dict[str, Any] | None:
        path = self._record_path(memory_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _iter_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for path in sorted(self._storage_dir.glob("*.json")):
            with path.open("r", encoding="utf-8") as handle:
                records.append(json.load(handle))
        return records

    def _normalize_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        return normalize_mgp_memory(memory, adapter_name="file")
