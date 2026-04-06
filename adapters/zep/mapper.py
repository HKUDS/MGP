from __future__ import annotations

import json
import re
from typing import Any

from adapters.search_utils import consumable_text


def zep_metadata(memory: dict[str, Any], *, operation: str) -> dict[str, Any]:
    subject = memory.get("subject", {})
    source = memory.get("source", {})
    content = memory.get("content", {})
    backend_ref = memory.get("backend_ref", {})
    scope = memory.get("scope")
    session_id = backend_ref.get("session_id")
    task_id = backend_ref.get("task_id")
    if session_id is None and scope == "session":
        session_id = subject.get("id")
    if task_id is None and scope == "task":
        task_id = subject.get("id")

    metadata: dict[str, Any] = {
        "memory_id": memory.get("memory_id"),
        "scope": scope,
        "type": memory.get("type"),
        "subject_kind": subject.get("kind"),
        "subject_id": subject.get("id"),
        "source_kind": source.get("kind"),
        "source_ref": source.get("ref"),
        "created_at": memory.get("created_at"),
        "updated_at": memory.get("updated_at"),
        "valid_from": memory.get("valid_from"),
        "valid_to": memory.get("valid_to"),
        "confidence": memory.get("confidence"),
        "sensitivity": memory.get("sensitivity"),
        "retention_policy": memory.get("retention_policy"),
        "ttl_seconds": memory.get("ttl_seconds"),
        "assertion_mode": memory.get("assertion_mode"),
        "confirmed_by_user": memory.get("confirmed_by_user"),
        "operation": operation,
        "mgp_state": backend_ref.get("mgp_state"),
        "content_statement": content.get("statement"),
        "keywords": content.get("keywords"),
        "fact_key": content.get("fact_key"),
        "preference_key": content.get("preference_key"),
        "relation": content.get("relation"),
        "subject_entity": content.get("subject_entity"),
        "object_entity": content.get("object_entity"),
        "session_id": session_id,
        "task_id": task_id,
    }
    return {key: _metadata_value(value) for key, value in metadata.items() if value is not None}


def zep_identity_from_memory(memory: dict[str, Any]) -> dict[str, str]:
    subject = memory.get("subject", {})
    scope = memory.get("scope")
    backend_ref = memory.get("backend_ref", {})
    user_id = str(subject.get("id") or _normalized_subject_value(subject))
    thread_id = str(backend_ref.get("thread_id") or backend_ref.get("session_id") or user_id)
    group_id = str(backend_ref.get("group_id") or backend_ref.get("org_id") or "")

    identity = {
        "user_id": user_id,
        "thread_id": thread_id,
    }
    if scope in {"org", "shared_team"} and group_id:
        identity["group_id"] = group_id
    return identity


def zep_identity_for_search(subject: dict[str, Any] | None, scope: str | None) -> dict[str, str]:
    if not subject:
        return {}
    user_id = str(subject.get("id") or _normalized_subject_value(subject))
    identity = {
        "user_id": user_id,
        "thread_id": user_id,
    }
    if scope in {"org", "shared_team"}:
        identity["group_id"] = str(subject.get("id") or user_id)
    return identity


def zep_search_filters(subject: dict[str, Any] | None, scope: str | None) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    if scope:
        filters["scope"] = scope
    if subject:
        filters["subject_kind"] = subject.get("kind")
        filters["subject_id"] = subject.get("id")
    return filters


def zep_thread_messages(memory: dict[str, Any]) -> list[dict[str, str]]:
    content = memory.get("content", {})
    user_message = content.get("user_message")
    assistant_response = content.get("assistant_response")
    if isinstance(user_message, str) and user_message.strip():
        messages = [{"role": "user", "content": user_message.strip()}]
        if isinstance(assistant_response, str) and assistant_response.strip():
            messages.append({"role": "assistant", "content": assistant_response.strip()})
        return messages

    statement = consumable_text(memory).strip()
    if not statement:
        return []
    return [{"role": "user", "content": statement}]


def zep_graph_payload(memory: dict[str, Any]) -> dict[str, Any]:
    content = memory.get("content", {})
    text = consumable_text(memory).strip()
    if memory.get("type") == "relationship":
        subject_entity = content.get("subject_entity")
        relation = content.get("relation")
        object_entity = content.get("object_entity")
        if all(isinstance(value, str) and value.strip() for value in (subject_entity, relation, object_entity)):
            text = f"{subject_entity.strip()} {relation.strip()} {object_entity.strip()}. {text}"
    return {
        "text": text,
        "metadata": zep_metadata(memory, operation="write"),
    }


def zep_relation_extension(hit: dict[str, Any]) -> list[Any]:
    relations = hit.get("relations")
    if isinstance(relations, list):
        return relations
    if isinstance(hit, dict) and (
        hit.get("source_node_uuid")
        or hit.get("target_node_uuid")
        or (isinstance(hit.get("attributes"), dict) and hit["attributes"].get("edge_type"))
    ):
        return [hit]
    return []


def zep_hit_text(hit: dict[str, Any]) -> str:
    for key in ("text", "content", "memory", "summary", "fact", "name"):
        value = hit.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    attributes = hit.get("attributes")
    if isinstance(attributes, dict):
        for key in ("fact", "edge_type"):
            value = attributes.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def zep_hit_metadata(hit: dict[str, Any]) -> dict[str, Any]:
    for key in ("metadata", "payload"):
        value = hit.get(key)
        if isinstance(value, dict):
            return value
    return {}


def zep_hit_memory_id(hit: dict[str, Any]) -> str | None:
    metadata = zep_hit_metadata(hit)
    memory_id = metadata.get("memory_id") or metadata.get("mgp_memory_id")
    if isinstance(memory_id, str) and memory_id.strip():
        return memory_id.strip()
    return None


def zep_hit_explanation(hit: dict[str, Any], memory: dict[str, Any]) -> str:
    if zep_relation_extension(hit) or memory.get("type") == "relationship":
        return "Enriched with Zep graph and fact-aware recall while preserving the canonical MGP memory shape."
    if hit.get("facts") or hit.get("summary"):
        return "Enriched with Zep facts and summaries while preserving the canonical MGP memory shape."
    return "Enriched with Zep retrieval while preserving the canonical MGP memory shape."


def zep_hit_retrieval_mode(hit: dict[str, Any], memory: dict[str, Any]) -> str:
    if zep_relation_extension(hit) or memory.get("type") == "relationship":
        return "graph"
    return "semantic"


def zep_context_hits(context_block: str | None) -> list[dict[str, Any]]:
    if not isinstance(context_block, str) or not context_block.strip():
        return []

    hits: list[dict[str, Any]] = []
    facts_text = _extract_tag_block(context_block, "FACTS")
    if facts_text:
        for line in facts_text.splitlines():
            line = line.strip()
            if not line.startswith("- "):
                continue
            fact = _strip_fact_date_range(line[2:].strip())
            if not fact:
                continue
            hits.append(
                {
                    "memory_id": None,
                    "text": fact,
                    "metadata": {},
                    "relations": [],
                    "summary": None,
                    "facts": [fact],
                    "context_block": context_block,
                    "score": 0.72,
                }
            )

    summary_text = _extract_tag_block(context_block, "USER_SUMMARY")
    summary_text = _normalize_summary(summary_text)
    if summary_text:
        hits.append(
            {
                "memory_id": None,
                "text": summary_text,
                "metadata": {},
                "relations": [],
                "summary": summary_text,
                "facts": None,
                "context_block": context_block,
                "score": 0.55,
            }
        )

    return hits


def _metadata_value(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _normalized_subject_value(subject: dict[str, Any]) -> str:
    kind = str(subject.get("kind") or "custom").strip()
    value = str(subject.get("id") or "").strip()
    if kind == "user":
        return value or "unknown-user"
    return f"{kind}:{value}" if value else kind


def _extract_tag_block(text: str, tag: str) -> str:
    pattern = re.compile(rf"<{tag}>\s*(.*?)\s*</{tag}>", re.DOTALL)
    match = pattern.search(text)
    if not match:
        return ""
    return match.group(1).strip()


def _strip_fact_date_range(text: str) -> str:
    stripped = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()
    return stripped


def _normalize_summary(text: str) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " ".join(lines)
