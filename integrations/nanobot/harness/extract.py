from __future__ import annotations

import re
from typing import Any

from integrations.nanobot.sidecar import MemoryCandidate

_RUNTIME_CONTEXT_TAG = "[Runtime Context"
_TRAILING_PUNCTUATION = " \t\r\n.!?;,:"
_RECALL_PATTERNS = (
    r"^\s*what did i say about\b",
    r"^\s*what do you remember about\b",
    r"^\s*do you remember\b",
    r"^\s*what is my\b",
    r"^\s*remind me\b",
    r"^\s*can you recall\b",
)


def _strip_runtime_context(text: str) -> str:
    if text.startswith(_RUNTIME_CONTEXT_TAG):
        parts = text.split("\n\n", 1)
        if len(parts) == 2:
            return parts[1].strip()
        return ""
    return text.strip()


def _text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return _strip_runtime_context(content)

    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                text = _strip_runtime_context(item["text"])
                if text:
                    chunks.append(text)
        return "\n".join(chunks).strip()

    return ""


def _looks_like_preference(text: str) -> bool:
    lowered = text.lower()
    keywords = (
        "i prefer",
        "prefer ",
        "my preference",
        "i like",
        "i usually",
        "always use",
        "remember that i",
        "remember i",
    )
    return any(keyword in lowered for keyword in keywords)


def _looks_like_recall_request(text: str) -> bool:
    lowered = text.lower().strip()
    return any(re.match(pattern, lowered) for pattern in _RECALL_PATTERNS)


def _clean_fact(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip(_TRAILING_PUNCTUATION)
    return cleaned


def _extract_preference_value(text: str) -> str | None:
    patterns = (
        r"\b(?:please\s+)?remember(?:\s+that)?\s+i\s+prefer\s+(?P<value>.+)$",
        r"\bi\s+prefer\s+(?P<value>.+)$",
        r"\bmy\s+preference\s+is\s+(?P<value>.+)$",
        r"\bi\s+usually\s+(?P<value>.+)$",
        r"\bi\s+like\s+(?P<value>.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = _clean_fact(match.group("value"))
            if value:
                return value
    return None


def _extract_semantic_fact(text: str) -> str | None:
    patterns = (
        r"\b(?:please\s+)?remember(?:\s+that)?\s+(?P<fact>.+)$",
        r"\bmy\s+name\s+is\s+(?P<fact>.+)$",
        r"\bi\s+am\s+from\s+(?P<fact>.+)$",
        r"\bi\s+work\s+on\s+(?P<fact>.+)$",
        r"\bthe\s+project\s+is\s+called\s+(?P<fact>.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fact = _clean_fact(match.group("fact"))
            if fact:
                return fact
    return None


def _keywords_for_statement(statement: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", statement.lower())
    stopwords = {
        "a",
        "about",
        "an",
        "and",
        "assistant",
        "fact",
        "for",
        "i",
        "is",
        "it",
        "my",
        "of",
        "on",
        "or",
        "preference",
        "replied",
        "said",
        "that",
        "the",
        "to",
        "user",
        "you",
    }
    filtered = [word for word in words if word not in stopwords and len(word) > 2]
    keywords: list[str] = []
    for word in filtered:
        if word not in keywords:
            keywords.append(word)
    return keywords[:8]


def _summarize(user_text: str, assistant_text: str) -> str:
    assistant_clean = assistant_text.replace("\n", " ").strip()
    if len(assistant_clean) > 240:
        assistant_clean = assistant_clean[:237] + "..."
    return f"User said: {user_text} | Assistant replied: {assistant_clean}"


def extract_memory_candidate(
    messages: list[dict[str, Any]],
    *,
    source_ref: str | None = None,
) -> MemoryCandidate | None:
    user_text = ""
    assistant_text = ""

    for message in reversed(messages):
        role = message.get("role")
        message_text = _text_from_content(message.get("content"))
        if not message_text:
            continue
        if not assistant_text and role == "assistant":
            assistant_text = message_text
            continue
        if not user_text and role == "user":
            user_text = message_text
            continue
        if user_text and assistant_text:
            break

    if not user_text or not assistant_text:
        return None

    if _looks_like_recall_request(user_text):
        return None

    preference_value = _extract_preference_value(user_text) if _looks_like_preference(user_text) else None
    semantic_fact = _extract_semantic_fact(user_text) if preference_value is None else None

    if preference_value is not None:
        memory_type = "preference"
        statement = f"User prefers {preference_value}."
    elif semantic_fact is not None:
        memory_type = "semantic_fact"
        statement = f"Remember this fact: {semantic_fact}."
    else:
        return None

    content: dict[str, Any] = {
        "statement": statement,
        "keywords": _keywords_for_statement(statement),
        "user_message": user_text,
        "assistant_response": assistant_text,
        "summary": _summarize(user_text, assistant_text),
    }
    if preference_value is not None:
        content["preference"] = preference_value
    if semantic_fact is not None:
        content["fact"] = semantic_fact

    return MemoryCandidate(
        memory_type=memory_type,
        scope="user",
        sensitivity="internal",
        source_kind="chat",
        source_ref=source_ref,
        content=content,
        confidence=0.85 if memory_type == "preference" else 0.7,
        extensions={"nanobot:harness_extracted": True},
    )
