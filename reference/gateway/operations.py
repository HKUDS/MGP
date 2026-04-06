from __future__ import annotations

from typing import Any
from uuid import uuid4

from gateway.http import build_ok_response
from gateway.semantics import locate_existing_memory, memory_from_candidate, merge_memory
from gateway.state import (
    APP_VERSION,
    CANONICAL_RETURN_MODES,
    PROTOCOL_PROFILE_ORDER,
    SESSION_MODE,
    TRANSPORT_PROFILE,
    audit_sink,
    policy_hook,
    router,
    settings,
    task_store,
)
from gateway.time_utils import utc_now_iso
from gateway.validation import (
    GatewayValidationError,
    validate_async_task,
    validate_audit_event,
    validate_initialize_response,
    validate_memory_candidate,
    validate_memory_merge_hint,
    validate_memory_object,
    validate_negotiated_capabilities,
    validate_protocol_capabilities,
)
from gateway.version import APP_NAME, APP_TITLE, PROTOCOL_VERSION


def server_info(*, include_runtime_fields: bool = False) -> dict[str, Any]:
    payload = {
        "name": APP_NAME,
        "title": APP_TITLE,
        "version": APP_VERSION,
        "description": "Reference stateless HTTP gateway for governed memory operations.",
    }
    if include_runtime_fields:
        payload["protocol_version"] = PROTOCOL_VERSION
        payload["adapter"] = router.adapter_name
        payload["environment"] = settings.environment
    return payload


def protocol_capabilities() -> dict[str, Any]:
    capabilities = {
        "supports_discovery": True,
        "supports_initialize": True,
        "supports_runtime_capability_negotiation": True,
        "supports_negotiated_capabilities": True,
        "requires_initialize": False,
        "supports_stateless_http": True,
        "supports_streamable_http": False,
        "supports_sessions": False,
        "supports_async_operations": True,
        "supports_notifications": False,
        "supports_subscriptions": False,
        "supports_ping": False,
        "transport_profiles": [TRANSPORT_PROFILE],
        "supported_profiles": PROTOCOL_PROFILE_ORDER,
        "default_profile": "core-memory",
        "session_mode": SESSION_MODE,
    }
    validate_protocol_capabilities(capabilities)
    return capabilities


def current_protocol_version(manifest: dict[str, Any]) -> str:
    return str(manifest.get("mgp_version") or APP_VERSION)


def supported_protocol_versions(manifest: dict[str, Any]) -> list[str]:
    return [current_protocol_version(manifest)]


def bool_intersection(server_value: bool, runtime_value: bool | None) -> bool:
    return server_value if runtime_value is None else server_value and runtime_value


def negotiate_protocol_version(payload: dict[str, Any], supported_versions: list[str]) -> str:
    requested_single = payload.get("protocol_version")
    requested_versions = payload.get("supported_versions") or ([requested_single] if requested_single else [])
    preferred_version = payload.get("preferred_version") or requested_single

    if preferred_version and preferred_version not in requested_versions:
        raise GatewayValidationError(
            "MGP_INVALID_OBJECT",
            "preferred_version must also appear in supported_versions",
            {"field": "preferred_version"},
        )

    if preferred_version and preferred_version in supported_versions:
        return preferred_version

    for version in requested_versions:
        if version in supported_versions:
            return version

    raise GatewayValidationError(
        "MGP_UNSUPPORTED_VERSION",
        "no mutually supported protocol version was found",
        {"requested_versions": requested_versions, "supported_versions": supported_versions},
    )


def negotiate_profiles(
    requested_profiles: list[str] | None,
    supported_profiles: list[str],
    runtime_capabilities: dict[str, Any] | None,
) -> list[str]:
    runtime_supported_profiles = (runtime_capabilities or {}).get("supported_profiles")
    effective_request = requested_profiles or runtime_supported_profiles or supported_profiles

    unsupported = [profile for profile in effective_request if profile not in supported_profiles]
    if unsupported:
        raise GatewayValidationError(
            "MGP_UNSUPPORTED_CAPABILITY",
            "requested lifecycle profile is not supported",
            {"unsupported_profiles": unsupported, "supported_profiles": supported_profiles},
        )

    if runtime_supported_profiles is not None:
        negotiated = [profile for profile in effective_request if profile in runtime_supported_profiles]
        if not negotiated:
            raise GatewayValidationError(
                "MGP_UNSUPPORTED_CAPABILITY",
                "no mutually supported lifecycle profile was found",
                {"requested_profiles": effective_request, "runtime_supported_profiles": runtime_supported_profiles},
            )
        return negotiated

    return effective_request


def validate_requested_protocol_capabilities(
    requested_capabilities: dict[str, Any] | None,
    available_capabilities: dict[str, Any],
) -> None:
    if requested_capabilities is None:
        return

    validate_protocol_capabilities(requested_capabilities)
    unsupported_keys: list[str] = []

    for key, value in requested_capabilities.items():
        available = available_capabilities.get(key)
        if isinstance(value, bool):
            if value and available is not True:
                unsupported_keys.append(key)
        elif isinstance(value, str):
            if value != available:
                unsupported_keys.append(key)
        elif isinstance(value, list):
            if not set(value).issubset(set(available or [])):
                unsupported_keys.append(key)

    if unsupported_keys:
        raise GatewayValidationError(
            "MGP_UNSUPPORTED_CAPABILITY",
            "requested protocol capabilities are not supported",
            {"unsupported_capabilities": unsupported_keys},
        )


def negotiate_effective_return_modes(runtime_capabilities: dict[str, Any] | None) -> list[str]:
    preferred_modes = (runtime_capabilities or {}).get("preferred_return_modes")
    if preferred_modes:
        return [mode for mode in CANONICAL_RETURN_MODES if mode in preferred_modes]
    return CANONICAL_RETURN_MODES


def negotiate_runtime_capabilities(
    runtime_capabilities: dict[str, Any] | None,
    manifest: dict[str, Any],
    protocol_capabilities: dict[str, Any],
) -> dict[str, Any]:
    backend_capabilities = manifest["capabilities"]
    negotiated = {
        "runtime_capabilities_received": runtime_capabilities is not None,
        "supports_consumable_text": bool_intersection(
            True,
            (runtime_capabilities or {}).get("supports_consumable_text"),
        ),
        "supports_redaction_info": bool_intersection(
            True,
            (runtime_capabilities or {}).get("supports_redaction_info"),
        ),
        "supports_mixed_return_modes": bool_intersection(
            True,
            (runtime_capabilities or {}).get("supports_mixed_return_modes"),
        ),
        "supports_partial_failure": bool_intersection(
            True,
            (runtime_capabilities or {}).get("supports_partial_failure"),
        ),
        "supports_search_explanations": bool_intersection(
            backend_capabilities["supports_retrieval_explanations"],
            (runtime_capabilities or {}).get("supports_search_explanations"),
        ),
        "supports_prompt_view": bool_intersection(
            backend_capabilities["supports_prompt_view"],
            (runtime_capabilities or {}).get("supports_prompt_view"),
        ),
        "supports_delete": backend_capabilities["supports_delete"],
        "supports_purge": backend_capabilities["supports_purge"],
        "supports_async_operations": bool_intersection(
            protocol_capabilities["supports_async_operations"],
            (runtime_capabilities or {}).get("supports_async_operations"),
        ),
        "supports_subscriptions": bool_intersection(
            protocol_capabilities["supports_subscriptions"],
            (runtime_capabilities or {}).get("supports_subscriptions"),
        ),
        "effective_return_modes": negotiate_effective_return_modes(runtime_capabilities),
    }
    validate_negotiated_capabilities(negotiated)
    return negotiated


def create_async_task(
    *,
    operation: str,
    request_id: str,
    runner: Any,
) -> dict[str, Any]:
    task = task_store.create(operation=operation, request_id=request_id, runner=runner)
    validate_async_task(task)
    return task


def task_data(task: dict[str, Any]) -> dict[str, Any]:
    validate_async_task(task)
    return {"task": task}


def build_initialize_response(
    request_id: str,
    *,
    chosen_version: str,
    supported_versions: list[str],
    negotiated_profiles: list[str],
    protocol_capabilities: dict[str, Any],
    negotiated_capabilities: dict[str, Any],
) -> dict[str, Any]:
    payload = build_ok_response(
        request_id,
        {
            "chosen_version": chosen_version,
            "supported_versions": supported_versions,
            "minimum_supported_version": supported_versions[-1],
            "lifecycle_phase": "ready",
            "session_mode": SESSION_MODE,
            "transport_profile": TRANSPORT_PROFILE,
            "protocol_capabilities": protocol_capabilities,
            "negotiated_capabilities": negotiated_capabilities,
            "negotiated_profiles": negotiated_profiles,
            "server_info": server_info(),
            "discovery": {"capabilities_uri": "/mgp/capabilities"},
            "deprecation_warnings": [],
        },
    )
    validate_initialize_response(payload)
    return payload


def emit_audit_event(
    *,
    request_id: str,
    action: str,
    target_memory_id: str,
    policy_context: dict[str, Any],
    decision: dict[str, Any],
    backend: str,
    result_count: int | None = None,
    lineage_refs: list[str] | None = None,
) -> None:
    event: dict[str, Any] = {
        "event_id": f"evt_{uuid4().hex}",
        "timestamp": utc_now_iso(),
        "request_id": request_id,
        "actor": {"kind": "agent", "id": policy_context["actor_agent"]},
        "action": action,
        "target_memory_id": target_memory_id,
        "policy_context": policy_context,
        "decision": decision,
        "backend": backend,
        "lineage_refs": lineage_refs or [],
    }
    if result_count is not None:
        event["result_count"] = result_count
    if policy_context.get("correlation_id"):
        event["correlation_id"] = policy_context["correlation_id"]
    validate_audit_event(event)
    audit_sink.append(event)


def resolve_write_payload(
    body: dict[str, Any],
    policy_context: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if "memory" in body:
        memory = body["memory"]
        validate_memory_object(memory)
    elif "candidate" in body:
        candidate = body["candidate"]
        validate_memory_candidate(candidate)
        memory = memory_from_candidate(candidate, policy_context)
        validate_memory_object(memory)
    else:
        raise GatewayValidationError(
            "MGP_INVALID_OBJECT",
            "WriteMemory payload must include either memory or candidate",
            {"field": "payload"},
        )

    merge_hint = body.get("merge_hint") or body.get("candidate", {}).get("merge_hint")
    if merge_hint is not None:
        validate_memory_merge_hint(merge_hint)
        if merge_hint.get("dedupe_key"):
            memory.setdefault("extensions", {})["mgp:dedupe_key"] = merge_hint["dedupe_key"]
    return memory, merge_hint


def execute_write(
    policy_context: dict[str, Any],
    body: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None, str]:
    memory, merge_hint = resolve_write_payload(body, policy_context)
    existing = router.dispatch("get", {"memory_id": memory["memory_id"]})
    if not existing and merge_hint:
        existing = locate_existing_memory(
            router.dispatch("list_memories", {"include_inactive": False}),
            memory,
            merge_hint,
        )

    decision = policy_hook.evaluate(policy_context, memory, "write")
    if decision["decision"] == "deny":
        raise GatewayValidationError("MGP_POLICY_DENIED", decision["reason_code"])

    resolution = "created"
    if existing:
        if merge_hint is None:
            raise GatewayValidationError(
                "MGP_CONFLICT_UNRESOLVED",
                "memory already exists and no merge_hint was provided",
                {"memory_id": existing["memory_id"]},
            )
        merged, resolution = merge_memory(existing, memory, merge_hint)
        validate_memory_object(merged)
        memory = router.dispatch("write", {"memory": merged})
    else:
        memory = router.dispatch("write", {"memory": memory})

    transformed, redaction_info = policy_hook.transform_memory(memory, decision)
    return transformed, decision, redaction_info, resolution


def paginate(
    items: list[dict[str, Any]],
    pagination_token: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], str | None]:
    offset = int(pagination_token or 0)
    page = items[offset : offset + limit]
    next_token = str(offset + limit) if offset + limit < len(items) else None
    return page, next_token


def export_memories_data(request_id: str, policy_context: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    all_memories = router.dispatch(
        "list_memories",
        {"include_inactive": body.get("include_inactive", False)},
    )
    limit = body.get("limit", 100)
    page, next_token = paginate(all_memories, body.get("pagination_token"), limit)
    emit_audit_event(
        request_id=request_id,
        action="read",
        target_memory_id="__export__",
        policy_context=policy_context,
        decision={
            "decision": "allow",
            "reason_code": "export_completed",
            "applied_rules": [],
            "return_mode": "raw",
        },
        backend=router.adapter_name,
        result_count=len(page),
    )
    data: dict[str, Any] = {"memories": page}
    if next_token:
        data["next_token"] = next_token
    return data


def import_memories_data(policy_context: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    imported: list[str] = []
    for memory in body.get("memories", []):
        transformed, _, _, _ = execute_write(policy_context, {"memory": memory, "merge_hint": body.get("merge_hint")})
        imported.append(transformed["memory_id"])
    return {"memory_ids": imported, "written_count": len(imported)}


def sync_memories_data(body: dict[str, Any]) -> dict[str, Any]:
    all_memories = router.dispatch(
        "list_memories",
        {"include_inactive": body.get("include_inactive", False)},
    )
    limit = body.get("limit", 100)
    page, next_token = paginate(all_memories, body.get("cursor") or body.get("pagination_token"), limit)
    data: dict[str, Any] = {"memories": page}
    if next_token:
        data["next_token"] = next_token
        data["cursor"] = next_token
    return data
