from __future__ import annotations

import copy
import os
from typing import Any


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def apply_memory_patch(memory: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(memory)
    for key, value in patch.items():
        if key == "backend_ref" and isinstance(value, dict):
            merged.setdefault("backend_ref", {}).update(value)
        elif key == "extensions" and isinstance(value, dict):
            merged.setdefault("extensions", {}).update(value)
        elif key == "content" and isinstance(value, dict) and isinstance(merged.get("content"), dict):
            merged.setdefault("content", {}).update(value)
        else:
            merged[key] = value
    return merged


def normalize_mgp_memory(
    memory: dict[str, Any],
    *,
    adapter_name: str,
    default_state: str = "active",
) -> dict[str, Any]:
    normalized = copy.deepcopy(memory)
    backend_ref = normalized.setdefault("backend_ref", {})
    backend_ref["adapter"] = adapter_name
    backend_ref.setdefault("mgp_state", default_state)
    normalized.setdefault("extensions", {})
    normalized.setdefault("content", {})
    return normalized


def matches_memory_filters(
    memory: dict[str, Any],
    *,
    subject: dict[str, Any] | None,
    scope: str | None,
    types: list[str] | None,
) -> bool:
    if subject and memory.get("subject") != subject:
        return False
    if scope and memory.get("scope") != scope:
        return False
    if types and memory.get("type") not in types:
        return False
    return True
