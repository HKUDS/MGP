from __future__ import annotations

import copy
import json
import re
from typing import Any


def recall_terms(query: str, intent: dict[str, Any] | None = None) -> list[str]:
    terms: list[str] = []
    normalized_query = query.strip().lower()
    if normalized_query:
        terms.append(normalized_query)

    if intent:
        query_text = str(intent.get("query_text") or "").strip().lower()
        if query_text and query_text not in terms:
            terms.append(query_text)
        for keyword in intent.get("keywords") or []:
            value = str(keyword).strip().lower()
            if value and value not in terms:
                terms.append(value)

    split_terms = []
    for term in list(terms):
        split_terms.extend(re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", term))
    for term in split_terms:
        if len(term) > 2 and term not in terms:
            terms.append(term)
    return terms


def search_blob(memory: dict[str, Any]) -> str:
    content = json.dumps(memory.get("content", {}), ensure_ascii=False).lower()
    extras = " ".join(
        str(part).lower()
        for part in [
            memory.get("memory_id", ""),
            memory.get("type", ""),
            memory.get("scope", ""),
            memory.get("content", {}).get("statement", ""),
            memory.get("content", {}).get("summary", ""),
        ]
        if part
    )
    return f"{content} {extras}".strip()


def matched_terms(blob: str, terms: list[str]) -> list[str]:
    matches: list[str] = []
    for term in terms:
        if term and term in blob and term not in matches:
            matches.append(term)
    return matches


def memory_matches_terms(memory: dict[str, Any], terms: list[str]) -> list[str]:
    return matched_terms(search_blob(memory), terms)


def search_score(matches: list[str], terms: list[str]) -> float:
    if not terms:
        return 0.0
    if not matches:
        return 0.0
    return round(len(matches) / len(terms), 4)


def consumable_text(memory: dict[str, Any]) -> str:
    content = memory.get("content", {})
    if isinstance(content, dict):
        for key in ("statement", "summary", "preference", "fact"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return json.dumps(content, ensure_ascii=False, sort_keys=True)


def build_search_result_item(
    memory: dict[str, Any],
    *,
    score: float,
    retrieval_mode: str,
    term_matches: list[str],
    explanation: str,
    score_kind: str = "backend_local",
    copy_memory: bool = True,
) -> dict[str, Any]:
    result_memory = copy.deepcopy(memory) if copy_memory else memory
    return {
        "memory": result_memory,
        "score": score,
        "score_kind": score_kind,
        "retrieval_mode": retrieval_mode,
        "matched_terms": term_matches,
        "explanation": explanation,
        "consumable_text": consumable_text(result_memory),
    }


def lexical_search_result(
    memory: dict[str, Any],
    terms: list[str],
    *,
    retrieval_mode: str,
    explanation: str,
    score_kind: str = "backend_local",
    copy_memory: bool = True,
) -> dict[str, Any] | None:
    term_matches = memory_matches_terms(memory, terms)
    if not term_matches:
        return None
    return build_search_result_item(
        memory,
        score=search_score(term_matches, terms),
        retrieval_mode=retrieval_mode,
        term_matches=term_matches,
        explanation=explanation,
        score_kind=score_kind,
        copy_memory=copy_memory,
    )
