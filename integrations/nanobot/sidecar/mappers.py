from __future__ import annotations

import re
from typing import Any

from mgp_client import MemoryCandidate as ProtocolMemoryCandidate
from mgp_client import PolicyContextBuilder, SearchQuery
from mgp_client.models import PolicyContext

from .models import MemoryCandidate, NanobotRuntimeState, RecallIntent, RecallItem


def build_policy_context(
    runtime: NanobotRuntimeState,
    requested_action: str,
    *,
    workspace_as_tenant: bool = True,
) -> PolicyContext:
    tenant_id = runtime.tenant_id
    if tenant_id is None and workspace_as_tenant:
        tenant_id = runtime.workspace_id

    builder = PolicyContextBuilder(
        actor_agent=runtime.actor_agent,
        subject_kind=runtime.subject_kind,
        subject_id=runtime.user_id,
        tenant_id=tenant_id,
        data_zone=runtime.data_zone,
        task_id=runtime.session_key,
        session_id=runtime.session_key,
        task_type=runtime.task_type or f"nanobot:{runtime.channel}",
        risk_level=runtime.risk_level,
        channel=runtime.channel,
        chat_id=runtime.chat_id,
        runtime_id="nanobot",
        correlation_id=runtime.correlation_id,
    )
    return builder.build(requested_action)


def normalize_recall_query(query: str) -> str:
    text = re.sub(r"\s+", " ", query).strip()
    lowered = text.lower()

    patterns = (
        r"^\s*what did i say about (?P<phrase>.+?)[\?\.\!]*$",
        r"^\s*what do you remember about (?P<phrase>.+?)[\?\.\!]*$",
        r"^\s*what is my (?P<phrase>.+?)[\?\.\!]*$",
        r"^\s*remind me about (?P<phrase>.+?)[\?\.\!]*$",
    )
    for pattern in patterns:
        match = re.match(pattern, lowered)
        if match:
            phrase = match.group("phrase").strip(" .!?")
            if phrase:
                return phrase

    if '"' in text:
        quoted = re.findall(r'"([^"]+)"', text)
        if quoted:
            phrase = quoted[0].strip()
            if phrase:
                return phrase

    stopwords = {
        "a",
        "about",
        "an",
        "and",
        "did",
        "i",
        "is",
        "me",
        "my",
        "of",
        "please",
        "recall",
        "remember",
        "remind",
        "say",
        "that",
        "the",
        "what",
        "you",
    }
    tokens = [
        token
        for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", lowered)
        if token not in stopwords
    ]
    candidate = " ".join(tokens[:6]).strip()
    return candidate or text


def build_search_query(runtime: NanobotRuntimeState, intent: RecallIntent) -> SearchQuery:
    normalized = normalize_recall_query(intent.query)
    keywords = [token for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", normalized.lower()) if len(token) > 2]
    return SearchQuery(
        query=normalized,
        query_text=normalized,
        intent_type="preference_lookup" if intent.types and "preference" in intent.types else "free_text",
        keywords=keywords,
        subject={"kind": runtime.subject_kind, "id": runtime.user_id},
        scope=intent.scope,
        target_memory_types=intent.types,
        types=intent.types,
        top_k=intent.limit,
        limit=intent.limit,
    )


def build_memory_candidate(
    runtime: NanobotRuntimeState,
    candidate: MemoryCandidate,
    *,
    workspace_as_tenant: bool = True,
) -> ProtocolMemoryCandidate:
    source_ref = candidate.source_ref or f"nanobot:{runtime.channel}:{runtime.session_key}"

    extensions = dict(candidate.extensions)
    extensions.setdefault("nanobot:channel", runtime.channel)
    extensions.setdefault("nanobot:workspace", runtime.workspace_id)
    extensions.setdefault("nanobot:session_key", runtime.session_key)
    if runtime.chat_id:
        extensions.setdefault("nanobot:chat_id", runtime.chat_id)
    if runtime.correlation_id:
        extensions.setdefault("nanobot:correlation_id", runtime.correlation_id)

    content = dict(candidate.content)
    content.setdefault("statement", content.get("statement") or str(content.get("summary") or "Remember this fact."))
    if candidate.memory_type == "preference":
        content.setdefault("preference", content["statement"])
    if candidate.memory_type == "semantic_fact":
        content.setdefault("fact", content["statement"])

    return ProtocolMemoryCandidate(
        candidate_kind="assertion",
        subject={"kind": runtime.subject_kind, "id": runtime.user_id},
        scope=candidate.scope,
        proposed_type=candidate.memory_type,
        statement=content["statement"],
        source={"kind": candidate.source_kind, "ref": source_ref},
        content=content,
        source_evidence=[
            {
                "kind": "chat_message",
                "ref": source_ref,
                "excerpt": content.get("user_message") or content["statement"],
            }
        ],
        confidence=candidate.confidence,
        sensitivity=candidate.sensitivity,
        retention_policy=candidate.retention_policy,
        ttl_seconds=candidate.ttl_seconds,
        merge_hint={
            "strategy": "dedupe",
            "dedupe_key": f"{runtime.user_id}:{candidate.memory_type}:{content['statement'].lower()}",
        },
        extensions=extensions,
    )


def normalize_search_results(data: dict[str, Any] | None) -> list[RecallItem]:
    if not data:
        return []

    items: list[RecallItem] = []
    for entry in data.get("results", []):
        items.append(
            RecallItem(
                memory=entry.get("memory", {}),
                score=entry.get("score"),
                score_kind=entry.get("score_kind"),
                retrieval_mode=entry.get("retrieval_mode"),
                return_mode=entry.get("return_mode", "raw"),
                redaction_info=entry.get("redaction_info"),
                backend_origin=entry.get("backend_origin"),
                consumable_text=entry.get("consumable_text"),
                matched_terms=entry.get("matched_terms"),
                explanation=entry.get("explanation"),
            )
        )
    return items


def format_prompt_context(items: list[RecallItem]) -> str:
    prompt_lines: list[str] = []
    seen_lines: set[str] = set()
    for item in items:
        if item.return_mode == "metadata_only":
            continue

        memory = item.memory
        memory_type = memory.get("type", "memory")
        content_text = item.consumable_text or str(memory.get("content", ""))

        line = f"- {memory_type}: {content_text}"
        if line in seen_lines:
            continue
        seen_lines.add(line)
        prompt_lines.append(line)

    if not prompt_lines:
        return ""

    return "\n".join(["# Governed Memory Recall", *prompt_lines])
