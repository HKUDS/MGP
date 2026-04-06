from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from adapters.base import BaseAdapter
from adapters.memory_utils import (
    apply_memory_patch,
    env_flag,
    matches_memory_filters,
    normalize_mgp_memory,
)
from adapters.search_utils import (
    build_search_result_item,
    consumable_text,
    memory_matches_terms,
    recall_terms,
    search_score,
)

try:  # pragma: no cover - optional dependency
    from mem0 import MemoryClient as Mem0ClientSdk
except Exception:  # pragma: no cover - optional dependency
    Mem0ClientSdk = None

try:  # pragma: no cover - optional dependency
    from mem0 import Memory as Mem0LegacySdk
except Exception:  # pragma: no cover - optional dependency
    Mem0LegacySdk = None

def _parse_json_object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return copy.deepcopy(value)
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


class Mem0Adapter(BaseAdapter):
    """Mem0-backed adapter with Mem0 as the source of truth."""

    def __init__(self) -> None:
        self._manifest_path = Path(__file__).with_name("manifest.json")
        self._app_id = os.getenv("MGP_MEM0_APP_ID", "mgp")
        self._org_id = os.getenv("MGP_MEM0_ORG_ID")
        self._project_id = os.getenv("MGP_MEM0_PROJECT_ID")
        self._enable_graph = env_flag("MGP_MEM0_ENABLE_GRAPH", True)
        self._graph_enabled = self._enable_graph
        self._client = self._build_client()

    def write(self, memory: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_memory(memory)
        existing = self._find_record(normalized["memory_id"])
        metadata = self._metadata_for_memory(normalized)
        payload = self._mem0_payload(normalized)
        if not payload:
            raise RuntimeError("Mem0 write requires non-empty memory content.")

        if existing is None:
            try:
                raw = self._client.add(
                    payload,
                    app_id=self._app_id,
                    metadata=metadata,
                    infer=False,
                    async_mode=False,
                    enable_graph=self._graph_enabled,
                    version="v2",
                    output_format="v1.1",
                )
            except Exception as error:
                if self._graph_enabled and self._should_retry_without_graph(error):
                    self._graph_enabled = False
                    raw = self._client.add(
                        payload,
                        app_id=self._app_id,
                        metadata=metadata,
                        infer=False,
                        async_mode=False,
                        enable_graph=False,
                        version="v2",
                        output_format="v1.1",
                    )
                else:
                    raise
            service_id = self._extract_record_id(raw)
        else:
            service_id = existing["id"]
            self._client.update(
                memory_id=service_id,
                text=consumable_text(normalized),
                metadata=metadata,
            )

        if service_id:
            normalized.setdefault("backend_ref", {})["mem0_id"] = service_id
        return normalized

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
        effective_query = self._effective_search_query(query, intent)
        if not terms or not effective_query:
            return []

        filters = self._search_filters(subject=subject, scope=scope, types=types)
        raw = self._client.search(
            effective_query,
            filters=filters,
            top_k=limit,
            version="v2",
            rerank=True,
        )
        results: list[dict[str, Any]] = []
        for record in self._extract_records(raw):
            memory = self._to_mgp_memory(record)
            if memory is None:
                continue
            if memory.get("backend_ref", {}).get("mgp_state") != "active":
                continue
            if not matches_memory_filters(memory, subject=subject, scope=scope, types=types):
                continue

            relations = record.get("relations") or []
            retrieval_mode = "graph" if relations or memory.get("type") == "relationship" else "semantic"
            matches = memory_matches_terms(memory, terms)
            score = self._coerce_score(record.get("score"), fallback=search_score(matches, terms))
            item = build_search_result_item(
                memory,
                score=score,
                retrieval_mode=retrieval_mode,
                term_matches=matches,
                explanation=self._explanation(retrieval_mode),
            )
            if relations:
                item["memory"].setdefault("extensions", {})["mem0:relations"] = relations
            results.append(item)

        results.sort(key=lambda item: (item["score"], item["memory"]["memory_id"]), reverse=True)
        return results[:limit]

    def get(self, memory_id: str) -> dict[str, Any] | None:
        record = self._find_record(memory_id)
        if record is None:
            return None
        return self._to_mgp_memory(record)

    def update(self, memory_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        record = self._find_record(memory_id)
        if record is None:
            return None

        current = self._to_mgp_memory(record)
        if current is None or current.get("backend_ref", {}).get("mgp_state") == "deleted":
            return None

        merged = apply_memory_patch(current, patch)
        normalized = self._normalize_memory(merged)
        self._client.update(
            memory_id=record["id"],
            text=consumable_text(normalized),
            metadata=self._metadata_for_memory(normalized),
        )
        normalized.setdefault("backend_ref", {})["mem0_id"] = record["id"]
        return normalized

    def expire(
        self,
        memory_id: str,
        expired_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        return self._transition_state(memory_id, "expired", "expired_at", expired_at, reason)

    def revoke(
        self,
        memory_id: str,
        revoked_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        return self._transition_state(memory_id, "revoked", "revoked_at", revoked_at, reason)

    def delete(
        self,
        memory_id: str,
        deleted_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        return self._transition_state(memory_id, "deleted", "deleted_at", deleted_at, reason)

    def purge(
        self,
        memory_id: str,
        purged_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        record = self._find_record(memory_id)
        if record is None:
            return None
        self._client.delete(memory_id=record["id"])
        return {"memory_id": memory_id, "state": "purged", "purged_at": purged_at, "reason": reason}

    def list_memories(
        self,
        *,
        include_inactive: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        records = self._get_all_records(limit=limit)
        memories: list[dict[str, Any]] = []
        for record in records:
            memory = self._to_mgp_memory(record)
            if memory is None:
                continue
            if not include_inactive and memory.get("backend_ref", {}).get("mgp_state") != "active":
                continue
            memories.append(memory)
        memories.sort(key=lambda item: item["memory_id"])
        return memories if limit is None else memories[:limit]

    def get_manifest(self) -> dict[str, Any]:
        with self._manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        manifest["capabilities"]["search_modes"] = ["semantic", "graph"] if self._graph_enabled else ["semantic"]
        manifest["capabilities"]["supports_graph_relations"] = self._graph_enabled
        manifest["capabilities"]["score_kind"] = "backend_local"
        return manifest

    def _build_client(self):  # pragma: no cover - external dependency
        api_key = os.getenv("MGP_MEM0_API_KEY") or os.getenv("MEM0_API_KEY")
        if not api_key:
            raise RuntimeError("Mem0 adapter requires MGP_MEM0_API_KEY or MEM0_API_KEY.")

        kwargs: dict[str, Any] = {"api_key": api_key}
        if self._org_id:
            kwargs["org_id"] = self._org_id
        if self._project_id:
            kwargs["project_id"] = self._project_id

        if Mem0ClientSdk is not None:
            return Mem0ClientSdk(**kwargs)
        if Mem0LegacySdk is not None:
            return Mem0LegacySdk(**kwargs)
        raise RuntimeError('Mem0 SDK is not installed. Install it with: pip install "mem0ai"')

    def _find_record(self, memory_id: str) -> dict[str, Any] | None:
        filtered = self._get_all_records(filters=self._memory_id_filters(memory_id), limit=10)
        for record in filtered:
            metadata = record.get("metadata") or {}
            if metadata.get("mgp_memory_id") == memory_id:
                return record

        for record in self._get_all_records(limit=1000):
            metadata = record.get("metadata") or {}
            if metadata.get("mgp_memory_id") == memory_id:
                return record
        return None

    def _get_all_records(
        self,
        *,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        payload_filters = filters or {"app_id": self._app_id}
        raw = self._client.get_all(
            filters=payload_filters,
            version="v2",
            page=1,
            page_size=limit or 1000,
            output_format="v1.1",
        )
        return self._extract_records(raw)

    def _memory_id_filters(self, memory_id: str) -> dict[str, Any]:
        return {
            "AND": [
                {"app_id": self._app_id},
                {"metadata": {"mgp_memory_id": memory_id}},
            ]
        }

    def _search_filters(
        self,
        *,
        subject: dict[str, Any] | None,
        scope: str | None,
        types: list[str] | None,
    ) -> dict[str, Any]:
        filters: list[dict[str, Any]] = [{"app_id": self._app_id}]
        if subject is not None:
            filters.append({"metadata": {"mgp_subject_kind": subject.get("kind")}})
            filters.append({"metadata": {"mgp_subject_id": subject.get("id")}})
        if scope is not None:
            filters.append({"metadata": {"mgp_scope": scope}})
        if types:
            if len(types) == 1:
                filters.append({"metadata": {"mgp_type": types[0]}})
            else:
                filters.append({"metadata": {"mgp_type": {"in": types}}})
        return filters[0] if len(filters) == 1 else {"AND": filters}

    def _metadata_for_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        payload = copy.deepcopy(memory)
        payload.setdefault("backend_ref", {}).pop("mem0_id", None)
        subject = payload.get("subject", {})
        return {
            "mgp_memory_id": payload["memory_id"],
            "mgp_state": payload.get("backend_ref", {}).get("mgp_state", "active"),
            "mgp_scope": payload.get("scope"),
            "mgp_type": payload.get("type"),
            "mgp_subject_kind": subject.get("kind"),
            "mgp_subject_id": subject.get("id"),
            "mgp_memory": payload,
        }

    def _to_mgp_memory(self, record: dict[str, Any]) -> dict[str, Any] | None:
        metadata = record.get("metadata") or {}
        memory = _parse_json_object(metadata.get("mgp_memory"))
        if memory is None:
            memory = {
                "memory_id": metadata.get("mgp_memory_id") or record.get("id"),
                "subject": {
                    "kind": metadata.get("mgp_subject_kind") or "user",
                    "id": metadata.get("mgp_subject_id") or "unknown",
                },
                "scope": metadata.get("mgp_scope") or "user",
                "type": metadata.get("mgp_type") or "semantic_fact",
                "content": {"statement": str(record.get("memory") or "")},
                "source": {"kind": "external", "ref": f"mem0:{record.get('id', 'unknown')}"},
                "created_at": record.get("created_at") or "",
                "backend_ref": {"tenant_id": None},
                "extensions": {},
            }
        backend_ref = memory.setdefault("backend_ref", {})
        backend_ref["adapter"] = "mem0"
        backend_ref["mgp_state"] = metadata.get("mgp_state") or backend_ref.get("mgp_state") or "active"
        if record.get("id"):
            backend_ref["mem0_id"] = record["id"]
        memory.setdefault("extensions", {})
        if record.get("relations"):
            memory["extensions"]["mem0:relations"] = record["relations"]
        return memory

    def _mem0_payload(self, memory: dict[str, Any]) -> str | list[dict[str, str]]:
        content = memory.get("content", {})
        user_message = content.get("user_message")
        assistant_response = content.get("assistant_response")
        if isinstance(user_message, str) and user_message.strip():
            messages = [{"role": "user", "content": user_message.strip()}]
            if isinstance(assistant_response, str) and assistant_response.strip():
                messages.append({"role": "assistant", "content": assistant_response.strip()})
            return messages
        return consumable_text(memory)

    def _extract_records(self, raw: Any) -> list[dict[str, Any]]:
        if isinstance(raw, dict):
            items = raw.get("results") or raw.get("memories") or raw.get("data") or []
            shared_relations = raw.get("relations") or []
            if isinstance(items, dict):
                items = items.get("results") or items.get("memories") or items.get("data") or []
        elif isinstance(raw, list):
            items = raw
            shared_relations = []
        else:
            return []

        records: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            record = copy.deepcopy(item)
            if not record.get("relations") and shared_relations:
                record["relations"] = shared_relations
            records.append(record)
        return records

    def _extract_record_id(self, raw: Any) -> str | None:
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and item.get("id"):
                    return str(item["id"])
        if isinstance(raw, dict):
            if raw.get("id"):
                return str(raw["id"])
            for key in ("results", "memories", "data"):
                items = raw.get(key)
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and item.get("id"):
                            return str(item["id"])
        return None

    def _transition_state(
        self,
        memory_id: str,
        state: str,
        timestamp_key: str,
        timestamp_value: str | None,
        reason: str | None,
    ) -> dict[str, Any] | None:
        record = self._find_record(memory_id)
        if record is None:
            return None

        memory = self._to_mgp_memory(record)
        if memory is None:
            return None

        backend_ref = memory.setdefault("backend_ref", {})
        backend_ref["mgp_state"] = state
        if record.get("id"):
            backend_ref["mem0_id"] = record["id"]
        memory.setdefault("extensions", {})["mgp:last_state_reason"] = reason
        if timestamp_value is not None:
            memory[timestamp_key] = timestamp_value

        self._client.update(
            memory_id=record["id"],
            text=consumable_text(memory),
            metadata=self._metadata_for_memory(memory),
        )
        return {"memory_id": memory_id, "state": state}

    def _normalize_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        return normalize_mgp_memory(memory, adapter_name="mem0")

    def _effective_search_query(self, query: str, intent: dict[str, Any] | None) -> str:
        if query.strip():
            return query.strip()
        if intent and str(intent.get("query_text") or "").strip():
            return str(intent["query_text"]).strip()
        keywords = [str(keyword).strip() for keyword in (intent or {}).get("keywords") or [] if str(keyword).strip()]
        return " ".join(keywords)

    def _explanation(self, retrieval_mode: str) -> str:
        if retrieval_mode == "graph":
            return "Retrieved from Mem0 graph-aware search while preserving the canonical MGP memory shape."
        return "Retrieved from Mem0 semantic search while preserving the canonical MGP memory shape."

    def _should_retry_without_graph(self, error: Exception) -> bool:
        message = str(error).lower()
        return "graph memories feature is not available" in message or "upgrade to pro" in message

    def _coerce_score(self, value: Any, *, fallback: float) -> float:
        try:
            if value is None:
                return fallback
            return float(value)
        except (TypeError, ValueError):
            return fallback
