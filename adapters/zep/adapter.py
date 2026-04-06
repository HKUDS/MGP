from __future__ import annotations

import copy
import json
import os
import time
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
from adapters.zep.client import ZepClient


def _as_dict(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {key: _as_dict(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_as_dict(item) for item in value]
    if hasattr(value, "model_dump"):
        return _as_dict(value.model_dump())
    if hasattr(value, "dict"):
        return _as_dict(value.dict())
    return value


class ZepAdapter(BaseAdapter):
    """Zep-backed adapter with Zep episodes as the source of truth."""

    def __init__(self) -> None:
        self._manifest_path = Path(__file__).with_name("manifest.json")
        self._graph_user_id = os.getenv("MGP_ZEP_GRAPH_USER_ID", "mgp-global")
        self._reranker = os.getenv("MGP_ZEP_RERANKER")
        self._return_context = env_flag("MGP_ZEP_RETURN_CONTEXT", False)
        self._ignore_roles = self._parse_csv(os.getenv("MGP_ZEP_IGNORE_ROLES", "assistant"))
        self._client = self._build_client()

    def write(self, memory: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_memory(memory)
        existing = self._find_episode(normalized["memory_id"])
        episode = self._store_memory(normalized, replace_uuid=self._episode_uuid(existing) if existing else None)
        episode_uuid = self._episode_uuid(episode)
        if episode_uuid:
            normalized.setdefault("backend_ref", {})["zep_episode_uuid"] = episode_uuid
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

        raw = self._client.graph_search(
            user_id=self._graph_user_id,
            query=effective_query,
            scope="episodes",
            limit=max(limit * 3, 25),
            reranker=self._reranker,
        )
        context_block = self._load_context_block(subject=subject, scope=scope)
        results: list[dict[str, Any]] = []
        for episode in self._extract_episodes(raw):
            memory = self._episode_to_memory(episode)
            if memory is None:
                continue
            if memory.get("backend_ref", {}).get("mgp_state") != "active":
                continue
            if not matches_memory_filters(memory, subject=subject, scope=scope, types=types):
                continue

            matches = memory_matches_terms(memory, terms)
            retrieval_mode = "graph" if memory.get("type") == "relationship" else "semantic"
            score = self._coerce_score(episode.get("score"), fallback=search_score(matches, terms))
            item = build_search_result_item(
                memory,
                score=score,
                retrieval_mode=retrieval_mode,
                term_matches=matches,
                explanation=self._explanation(retrieval_mode),
            )
            if context_block:
                item["memory"].setdefault("extensions", {})["zep:context_block"] = context_block
            results.append(item)

        results.sort(key=lambda item: (item["score"], item["memory"]["memory_id"]), reverse=True)
        return results[:limit]

    def get(self, memory_id: str) -> dict[str, Any] | None:
        episode = self._find_episode(memory_id)
        if episode is None:
            return None
        return self._episode_to_memory(episode)

    def update(self, memory_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        episode = self._find_episode(memory_id)
        if episode is None:
            return None
        current = self._episode_to_memory(episode)
        if current is None or current.get("backend_ref", {}).get("mgp_state") == "deleted":
            return None

        merged = apply_memory_patch(current, patch)
        normalized = self._normalize_memory(merged)
        stored = self._store_memory(normalized, replace_uuid=self._episode_uuid(episode))
        stored_uuid = self._episode_uuid(stored)
        if stored_uuid:
            normalized.setdefault("backend_ref", {})["zep_episode_uuid"] = stored_uuid
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
        episode = self._find_episode(memory_id)
        episode_uuid = self._episode_uuid(episode)
        if episode is None or not episode_uuid:
            return None
        self._client.delete_episode(uuid_=episode_uuid)
        return {"memory_id": memory_id, "state": "purged", "purged_at": purged_at, "reason": reason}

    def list_memories(
        self,
        *,
        include_inactive: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        episodes = self._get_user_episodes(limit=limit)
        memories: list[dict[str, Any]] = []
        for episode in episodes:
            memory = self._episode_to_memory(episode)
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
        manifest["capabilities"]["search_modes"] = ["semantic", "graph"]
        manifest["capabilities"]["score_kind"] = "backend_local"
        return manifest

    def _build_client(self):  # pragma: no cover - external dependency
        api_key = os.getenv("MGP_ZEP_API_KEY") or os.getenv("ZEP_API_KEY")
        if not api_key:
            raise RuntimeError("Zep adapter requires MGP_ZEP_API_KEY or ZEP_API_KEY.")
        return ZepClient(api_key=api_key, base_url=os.getenv("MGP_ZEP_BASE_URL"))

    def _store_memory(self, memory: dict[str, Any], *, replace_uuid: str | None = None) -> dict[str, Any]:
        payload = json.dumps(
            {
                "memory": copy.deepcopy(memory),
                "consumable_text": consumable_text(memory),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        episode = _as_dict(
            self._client.graph_add(
                user_id=self._graph_user_id,
                text=payload,
                entry_type="json",
                created_at=memory.get("created_at"),
                source_description=self._source_description(memory),
            )
        )
        if memory.get("content", {}).get("user_message"):
            self._client.add_messages(
                thread_id=self._thread_id_for_memory(memory),
                user_id=self._graph_user_id,
                messages=self._thread_messages(memory),
                return_context=self._return_context,
                ignore_roles=self._ignore_roles,
            )
        episode_uuid = self._episode_uuid(episode)
        if episode_uuid:
            episode = self._await_episode_processed(episode_uuid)
        if replace_uuid:
            self._client.delete_episode(uuid_=replace_uuid)
        return episode

    def _find_episode(self, memory_id: str) -> dict[str, Any] | None:
        for episode in self._get_user_episodes(limit=1000):
            if self._episode_memory_id(episode) == memory_id:
                return episode
        return None

    def _get_user_episodes(self, *, limit: int | None) -> list[dict[str, Any]]:
        raw = self._client.get_user_episodes(user_id=self._graph_user_id, last=limit)
        return self._extract_episodes(raw)

    def _episode_to_memory(self, episode: dict[str, Any]) -> dict[str, Any] | None:
        content = episode.get("content")
        payload = None
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                payload = parsed
        memory = None
        if isinstance(payload, dict):
            payload_memory = payload.get("memory")
            if isinstance(payload_memory, dict):
                memory = copy.deepcopy(payload_memory)

        source_meta = self._parse_source_description(episode.get("source_description"))
        if memory is None:
            memory = {
                "memory_id": source_meta.get("mgp_memory_id") or self._episode_uuid(episode),
                "subject": {
                    "kind": source_meta.get("mgp_subject_kind") or "user",
                    "id": source_meta.get("mgp_subject_id") or "unknown",
                },
                "scope": source_meta.get("mgp_scope") or "user",
                "type": source_meta.get("mgp_type") or "semantic_fact",
                "content": {"statement": str(content or "")},
                "source": {"kind": "external", "ref": f"zep:{self._episode_uuid(episode) or 'unknown'}"},
                "created_at": episode.get("created_at") or "",
                "backend_ref": {},
                "extensions": {},
            }

        backend_ref = memory.setdefault("backend_ref", {})
        backend_ref["adapter"] = "zep"
        backend_ref["mgp_state"] = source_meta.get("mgp_state") or backend_ref.get("mgp_state") or "active"
        episode_uuid = self._episode_uuid(episode)
        if episode_uuid:
            backend_ref["zep_episode_uuid"] = episode_uuid
        if episode.get("thread_id"):
            backend_ref["thread_id"] = episode["thread_id"]
        if episode.get("session_id"):
            backend_ref.setdefault("session_id", episode["session_id"])
        memory.setdefault("extensions", {})
        return memory

    def _source_description(self, memory: dict[str, Any]) -> str:
        subject = memory.get("subject", {})
        payload = {
            "mgp_memory_id": memory.get("memory_id"),
            "mgp_state": memory.get("backend_ref", {}).get("mgp_state", "active"),
            "mgp_scope": memory.get("scope"),
            "mgp_type": memory.get("type"),
            "mgp_subject_kind": subject.get("kind"),
            "mgp_subject_id": subject.get("id"),
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def _parse_source_description(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, str):
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _episode_memory_id(self, episode: dict[str, Any]) -> str | None:
        source_value = self._parse_source_description(episode.get("source_description")).get("mgp_memory_id")
        if source_value:
            return source_value
        content = episode.get("content")
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, dict):
                if isinstance(parsed.get("memory"), dict) and parsed["memory"].get("memory_id"):
                    return str(parsed["memory"]["memory_id"])
                if parsed.get("memory_id"):
                    return str(parsed["memory_id"])
        return None

    def _transition_state(
        self,
        memory_id: str,
        state: str,
        timestamp_key: str,
        timestamp_value: str | None,
        reason: str | None,
    ) -> dict[str, Any] | None:
        episode = self._find_episode(memory_id)
        if episode is None:
            return None
        memory = self._episode_to_memory(episode)
        if memory is None:
            return None

        backend_ref = memory.setdefault("backend_ref", {})
        backend_ref["mgp_state"] = state
        episode_uuid = self._episode_uuid(episode)
        if episode_uuid:
            backend_ref["zep_episode_uuid"] = episode_uuid
        if timestamp_value is not None:
            memory[timestamp_key] = timestamp_value
        memory.setdefault("extensions", {})["mgp:last_state_reason"] = reason

        self._store_memory(memory, replace_uuid=episode_uuid)
        return {"memory_id": memory_id, "state": state}

    def _normalize_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        return normalize_mgp_memory(memory, adapter_name="zep")

    def _thread_messages(self, memory: dict[str, Any]) -> list[dict[str, str]]:
        content = memory.get("content", {})
        user_message = content.get("user_message")
        assistant_response = content.get("assistant_response")
        if isinstance(user_message, str) and user_message.strip():
            messages = [{"role": "user", "content": user_message.strip()}]
            if isinstance(assistant_response, str) and assistant_response.strip():
                messages.append({"role": "assistant", "content": assistant_response.strip()})
            return messages
        return [{"role": "user", "content": consumable_text(memory)}]

    def _thread_id_for_memory(self, memory: dict[str, Any]) -> str:
        backend_ref = memory.get("backend_ref", {})
        if backend_ref.get("thread_id"):
            return str(backend_ref["thread_id"])
        if backend_ref.get("session_id"):
            return str(backend_ref["session_id"])
        subject = memory.get("subject", {})
        return f"mgp:{subject.get('kind', 'user')}:{subject.get('id', 'unknown')}:{memory.get('scope', 'user')}"

    def _load_context_block(self, *, subject: dict[str, Any] | None, scope: str | None) -> str | None:
        if subject is None:
            return None
        thread_id = f"mgp:{subject.get('kind', 'user')}:{subject.get('id', 'unknown')}:{scope or 'user'}"
        try:
            raw = self._client.get_user_context(thread_id=thread_id)
        except Exception:  # pragma: no cover - optional enrichment
            return None
        payload = _as_dict(raw)
        if isinstance(payload, dict):
            for key in ("context", "context_block"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    def _extract_episodes(self, raw: Any) -> list[dict[str, Any]]:
        payload = _as_dict(raw)
        if isinstance(payload, dict):
            items = payload.get("episodes") or payload.get("results") or payload.get("data") or []
        elif isinstance(payload, list):
            items = payload
        else:
            return []
        episodes: list[dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict):
                episodes.append(item)
        return episodes

    def _await_episode_processed(self, uuid_: str) -> dict[str, Any]:
        deadline = time.time() + 5.0
        latest = _as_dict(self._client.get_episode(uuid_=uuid_))
        while isinstance(latest, dict) and latest.get("processed") is False and time.time() < deadline:
            time.sleep(0.25)
            latest = _as_dict(self._client.get_episode(uuid_=uuid_))
        return latest if isinstance(latest, dict) else {"uuid": uuid_}

    def _episode_uuid(self, episode: dict[str, Any] | None) -> str | None:
        if not isinstance(episode, dict):
            return None
        value = episode.get("uuid") or episode.get("uuid_")
        return str(value) if value else None

    def _effective_search_query(self, query: str, intent: dict[str, Any] | None) -> str:
        if query.strip():
            return query.strip()
        if intent and str(intent.get("query_text") or "").strip():
            return str(intent["query_text"]).strip()
        keywords = [str(keyword).strip() for keyword in (intent or {}).get("keywords") or [] if str(keyword).strip()]
        return " ".join(keywords)

    def _explanation(self, retrieval_mode: str) -> str:
        if retrieval_mode == "graph":
            return "Retrieved from Zep graph-backed episode search while preserving the canonical MGP memory shape."
        return "Retrieved from Zep semantic episode search while preserving the canonical MGP memory shape."

    def _parse_csv(self, raw: str | None) -> list[str] | None:
        if not raw:
            return None
        values = [item.strip() for item in raw.split(",") if item.strip()]
        return values or None

    def _coerce_score(self, value: Any, *, fallback: float) -> float:
        try:
            if value is None:
                return fallback
            return float(value)
        except (TypeError, ValueError):
            return fallback
