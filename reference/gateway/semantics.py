from __future__ import annotations

import copy
from typing import Any
from uuid import uuid4

from adapters.search_utils import consumable_text
from gateway.time_utils import utc_now_iso
from gateway.validation import GatewayValidationError


def normalize_recall_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("intent"):
        intent = copy.deepcopy(payload["intent"])
        query = str(intent.get("query_text") or payload.get("query") or "").strip()
        types = intent.get("target_memory_types") or payload.get("types")
        limit = intent.get("top_k", payload.get("limit", 10))
        return {
            "query": query,
            "intent": intent,
            "subject": payload.get("subject") or intent.get("subject"),
            "scope": payload.get("scope") or intent.get("scope"),
            "types": types,
            "limit": limit,
        }

    query = str(payload.get("query", "")).strip()
    intent = {
        "query_text": query,
        "intent_type": "free_text",
        "keywords": [],
        "top_k": payload.get("limit", 10),
    }
    if payload.get("types") is not None:
        intent["target_memory_types"] = payload.get("types")
    if payload.get("subject") is not None:
        intent["subject"] = payload.get("subject")
    if payload.get("scope") is not None:
        intent["scope"] = payload.get("scope")
    return {
        "query": query,
        "intent": intent,
        "subject": payload.get("subject"),
        "scope": payload.get("scope"),
        "types": payload.get("types"),
        "limit": payload.get("limit", 10),
    }


def memory_from_candidate(candidate: dict[str, Any], policy_context: dict[str, Any]) -> dict[str, Any]:
    content = copy.deepcopy(candidate.get("content", {}))
    content.setdefault("statement", candidate["statement"])
    if candidate["proposed_type"] == "preference":
        content.setdefault("preference", candidate["statement"])
    if candidate["proposed_type"] == "semantic_fact":
        content.setdefault("fact", candidate["statement"])

    evidence = copy.deepcopy(candidate.get("source_evidence", []))
    evidence_refs = [item.get("ref") for item in evidence if item.get("ref")]
    merge_hint = candidate.get("merge_hint") or {}
    extensions = copy.deepcopy(candidate.get("extensions", {}))
    if merge_hint.get("dedupe_key"):
        extensions.setdefault("mgp:dedupe_key", merge_hint["dedupe_key"])

    assertion_mode_map = {
        "assertion": "asserted",
        "confirmation": "confirmed",
        "correction": "asserted",
        "derived": "derived",
    }

    memory: dict[str, Any] = {
        "memory_id": f"mem_{uuid4().hex}",
        "subject": candidate["subject"],
        "scope": candidate["scope"],
        "type": candidate["proposed_type"],
        "content": content,
        "source": candidate["source"],
        "created_at": utc_now_iso(seconds_precision=True, z_suffix=True),
        "backend_ref": {"tenant_id": policy_context.get("tenant_id")} if policy_context.get("tenant_id") else {},
        "extensions": extensions,
        "assertion_mode": assertion_mode_map.get(candidate["candidate_kind"], "asserted"),
        "asserted_by": {"kind": "agent", "id": policy_context["actor_agent"]},
        "confirmed_by_user": candidate["candidate_kind"] in {"assertion", "confirmation"}
        and candidate["subject"].get("kind") == "user",
        "evidence_refs": evidence_refs,
        "evidence": evidence,
        "derived_from": [],
    }
    for key in ("confidence", "sensitivity", "retention_policy", "ttl_seconds"):
        if key in candidate and candidate[key] is not None:
            memory[key] = candidate[key]
    return memory


def merge_memory(
    existing: dict[str, Any],
    incoming: dict[str, Any],
    merge_hint: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    strategy = merge_hint.get("strategy", "create")
    if strategy == "create":
        raise GatewayValidationError("MGP_CONFLICT_UNRESOLVED", "create strategy does not allow existing memory")
    if strategy == "manual_review_required":
        raise GatewayValidationError("MGP_CONFLICT_UNRESOLVED", "manual review required for conflicting memory")

    merged = copy.deepcopy(existing)
    merged["updated_at"] = utc_now_iso(seconds_precision=True, z_suffix=True)

    if strategy in {"upsert", "replace"}:
        replacement = copy.deepcopy(incoming)
        replacement["memory_id"] = existing["memory_id"]
        replacement.setdefault("created_at", existing["created_at"])
        replacement["updated_at"] = utc_now_iso(seconds_precision=True, z_suffix=True)
        return replacement, "replaced"

    if strategy == "merge":
        merged["content"] = _deep_merge(existing.get("content", {}), incoming.get("content", {}))
        merged["extensions"] = _deep_merge(existing.get("extensions", {}), incoming.get("extensions", {}))
        merged["evidence_refs"] = _merge_unique(existing.get("evidence_refs", []), incoming.get("evidence_refs", []))
        merged["derived_from"] = _merge_unique(existing.get("derived_from", []), incoming.get("derived_from", []))
        merged["evidence"] = _merge_evidence(existing.get("evidence", []), incoming.get("evidence", []))
        if incoming.get("confidence") is not None:
            merged["confidence"] = max(existing.get("confidence") or 0, incoming["confidence"])
        return merged, "merged"

    if strategy in {"reinforce", "dedupe"}:
        merged["evidence_refs"] = _merge_unique(existing.get("evidence_refs", []), incoming.get("evidence_refs", []))
        merged["derived_from"] = _merge_unique(existing.get("derived_from", []), incoming.get("derived_from", []))
        merged["evidence"] = _merge_evidence(existing.get("evidence", []), incoming.get("evidence", []))
        if incoming.get("confidence") is not None:
            merged["confidence"] = max(existing.get("confidence") or 0, incoming["confidence"])
        return merged, "reinforced" if strategy == "reinforce" else "deduped"

    raise GatewayValidationError("MGP_CONFLICT_UNRESOLVED", f"unsupported merge strategy: {strategy}")


def locate_existing_memory(
    list_memories: list[dict[str, Any]],
    incoming: dict[str, Any],
    merge_hint: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    hint = merge_hint or {}
    target_memory_id = hint.get("if_match_memory_id")
    if target_memory_id:
        for memory in list_memories:
            if memory.get("memory_id") == target_memory_id:
                return memory

    dedupe_key = hint.get("dedupe_key")
    incoming_dedupe_key = incoming.get("extensions", {}).get("mgp:dedupe_key")
    incoming_statement = incoming.get("content", {}).get("statement")

    for memory in list_memories:
        if memory.get("subject") != incoming.get("subject"):
            continue
        if memory.get("type") != incoming.get("type"):
            continue
        if dedupe_key and memory.get("extensions", {}).get("mgp:dedupe_key") == dedupe_key:
            return memory
        if incoming_dedupe_key and memory.get("extensions", {}).get("mgp:dedupe_key") == incoming_dedupe_key:
            return memory
        if incoming_statement and memory.get("content", {}).get("statement") == incoming_statement:
            return memory
    return None


def build_result_item(
    *,
    memory: dict[str, Any],
    backend_origin: str,
    decision: dict[str, Any],
    redaction_info: dict[str, Any] | None,
    adapter_item: dict[str, Any],
) -> dict[str, Any]:
    policy_view = decision["return_mode"]
    view_memory = copy.deepcopy(memory)
    if redaction_info is None:
        redaction_info = None
    else:
        redaction_info = copy.deepcopy(redaction_info)
        redaction_info.setdefault("policy_view", policy_view)

    text = adapter_item.get("consumable_text") or consumable_text(view_memory)
    if policy_view == "metadata_only":
        text = f"{view_memory.get('type', 'memory')} metadata only"
        view_memory["content"] = {"statement": text}
        matched = []
        explanation = "Result metadata only due to policy."
    elif policy_view == "summary":
        content = view_memory.get("content")
        if isinstance(content, dict) and "summary" in content and "statement" not in content:
            view_memory["content"]["statement"] = str(content["summary"])
        matched = adapter_item.get("matched_terms", [])
        explanation = adapter_item.get("explanation", "")
    else:
        matched = adapter_item.get("matched_terms", [])
        explanation = adapter_item.get("explanation", "")

    return {
        "memory": view_memory,
        "score": adapter_item.get("score", 0.0),
        "score_kind": adapter_item.get("score_kind", "backend_local"),
        "backend_origin": adapter_item.get("backend_origin", backend_origin),
        "retrieval_mode": adapter_item.get("retrieval_mode", "lexical"),
        "return_mode": policy_view,
        "redaction_info": redaction_info,
        "consumable_text": text,
        "matched_terms": matched,
        "explanation": explanation,
    }


def _deep_merge(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(left)
    for key, value in right.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _merge_unique(left: list[str], right: list[str]) -> list[str]:
    merged: list[str] = []
    for item in [*left, *right]:
        if item and item not in merged:
            merged.append(item)
    return merged


def _merge_evidence(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in [*left, *right]:
        key = (str(item.get("kind", "")), str(item.get("ref", "")))
        if key in seen:
            continue
        seen.add(key)
        merged.append(copy.deepcopy(item))
    return merged
