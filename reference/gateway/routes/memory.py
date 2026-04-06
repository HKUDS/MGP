from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from adapters.memory_utils import apply_memory_patch
from adapters.search_utils import consumable_text
from gateway.http import (
    enforce_tenant_binding,
    json_error,
    json_validated_ok,
    request_id_from_payload,
    validate_action_request,
)
from gateway.operations import emit_audit_event, execute_write
from gateway.semantics import build_result_item, normalize_recall_payload
from gateway.state import policy_hook
from gateway.state import router as adapter_router
from gateway.validation import (
    GatewayValidationError,
    validate_delete_memory_request,
    validate_delete_memory_response,
    validate_expire_memory_request,
    validate_expire_memory_response,
    validate_get_memory_request,
    validate_get_memory_response,
    validate_memory_object,
    validate_purge_memory_request,
    validate_purge_memory_response,
    validate_recall_intent,
    validate_revoke_memory_request,
    validate_revoke_memory_response,
    validate_search_memory_request,
    validate_search_memory_response,
    validate_search_result_item,
    validate_update_memory_request,
    validate_update_memory_response,
    validate_write_batch_request,
    validate_write_batch_response,
    validate_write_memory_request,
    validate_write_memory_response,
)

router = APIRouter()


def _prepare_request(
    request: Request,
    payload: dict[str, Any],
    *,
    action: str,
    request_validator: Any,
) -> tuple[str, dict[str, Any], dict[str, Any], JSONResponse | None]:
    request_id, policy_context, body = validate_action_request(payload, action, request_validator)
    return request_id, policy_context, body, enforce_tenant_binding(request, request_id, policy_context)


def _memory_lifecycle_response(
    *,
    request_id: str,
    policy_context: dict[str, Any],
    body: dict[str, Any],
    action: str,
    dispatch_action: str,
    response_validator: Any,
) -> JSONResponse:
    existing = adapter_router.dispatch("get", {"memory_id": body["memory_id"]})
    if not existing:
        return json_error(request_id, "MGP_MEMORY_NOT_FOUND", "memory not found")

    decision = policy_hook.evaluate(policy_context, existing, action)
    if decision["decision"] == "deny":
        return json_error(request_id, "MGP_POLICY_DENIED", decision["reason_code"])

    result = adapter_router.dispatch(dispatch_action, body)
    emit_audit_event(
        request_id=request_id,
        action=action,
        target_memory_id=body["memory_id"],
        policy_context=policy_context,
        decision=decision,
        backend=adapter_router.adapter_name,
    )
    return json_validated_ok(request_id, result, response_validator)


@router.post("/mgp/write")
async def write_memory(request: Request, payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        request_id, policy_context, body, tenant_error = _prepare_request(
            request,
            payload,
            action="write",
            request_validator=validate_write_memory_request,
        )
        if tenant_error:
            return tenant_error

        transformed, decision, redaction_info, resolution = execute_write(policy_context, body)
        emit_audit_event(
            request_id=request_id,
            action="write",
            target_memory_id=transformed["memory_id"],
            policy_context=policy_context,
            decision=decision,
            backend=adapter_router.adapter_name,
            lineage_refs=transformed.get("derived_from"),
        )
        return json_validated_ok(
            request_id,
            {
                "memory": transformed,
                "return_mode": decision["return_mode"],
                "redaction_info": redaction_info,
                "consumable_text": consumable_text(transformed),
                "resolution": resolution,
            },
            validate_write_memory_response,
        )
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))


@router.post("/mgp/search")
async def search_memory(request: Request, payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        request_id, policy_context, body, tenant_error = _prepare_request(
            request,
            payload,
            action="search",
            request_validator=validate_search_memory_request,
        )
        if tenant_error:
            return tenant_error
        if body.get("intent") is not None:
            validate_recall_intent(body["intent"])
        normalized_body = normalize_recall_payload(body)
        raw_results = adapter_router.dispatch("search", normalized_body)
        results: list[dict[str, Any]] = []

        for item in raw_results:
            memory = item["memory"]
            decision = policy_hook.evaluate(policy_context, memory, "search")
            if decision["decision"] == "deny":
                continue

            transformed, redaction_info = policy_hook.transform_memory(memory, decision)
            result_item = build_result_item(
                memory=transformed,
                backend_origin=adapter_router.adapter_name,
                decision=decision,
                redaction_info=redaction_info,
                adapter_item=item,
            )
            validate_search_result_item(result_item)
            results.append(result_item)

        emit_audit_event(
            request_id=request_id,
            action="search",
            target_memory_id="__search__",
            policy_context=policy_context,
            decision={
                "decision": "allow",
                "reason_code": "search_completed",
                "applied_rules": [],
                "return_mode": "raw",
            },
            backend=adapter_router.adapter_name,
            result_count=len(results),
        )
        data: dict[str, Any] = {"results": results}
        effective_intent = normalized_body.get("intent")
        if effective_intent and effective_intent.get("query_text"):
            data["effective_intent"] = effective_intent
        return json_validated_ok(request_id, data, validate_search_memory_response)
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))


@router.post("/mgp/get")
async def get_memory(request: Request, payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        request_id, policy_context, body, tenant_error = _prepare_request(
            request,
            payload,
            action="read",
            request_validator=validate_get_memory_request,
        )
        if tenant_error:
            return tenant_error
        memory = adapter_router.dispatch("get", body)
        if not memory:
            return json_error(request_id, "MGP_MEMORY_NOT_FOUND", "memory not found")

        decision = policy_hook.evaluate(policy_context, memory, "read")
        if decision["decision"] == "deny":
            return json_error(request_id, "MGP_POLICY_DENIED", decision["reason_code"])

        transformed, redaction_info = policy_hook.transform_memory(memory, decision)
        emit_audit_event(
            request_id=request_id,
            action="read",
            target_memory_id=body["memory_id"],
            policy_context=policy_context,
            decision=decision,
            backend=adapter_router.adapter_name,
        )
        return json_validated_ok(
            request_id,
            {
                "memory": transformed,
                "return_mode": decision["return_mode"],
                "redaction_info": redaction_info,
                "consumable_text": consumable_text(transformed),
            },
            validate_get_memory_response,
        )
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))


@router.post("/mgp/update")
async def update_memory(request: Request, payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        request_id, policy_context, body, tenant_error = _prepare_request(
            request,
            payload,
            action="update",
            request_validator=validate_update_memory_request,
        )
        if tenant_error:
            return tenant_error
        existing = adapter_router.dispatch("get", {"memory_id": body["memory_id"]})
        if not existing:
            return json_error(request_id, "MGP_MEMORY_NOT_FOUND", "memory not found")

        decision = policy_hook.evaluate(policy_context, existing, "update")
        if decision["decision"] == "deny":
            return json_error(request_id, "MGP_POLICY_DENIED", decision["reason_code"])

        merged = apply_memory_patch(existing, body["patch"])
        validate_memory_object(merged)
        updated = adapter_router.dispatch("update", body)
        transformed, redaction_info = policy_hook.transform_memory(updated, decision)
        emit_audit_event(
            request_id=request_id,
            action="update",
            target_memory_id=body["memory_id"],
            policy_context=policy_context,
            decision=decision,
            backend=adapter_router.adapter_name,
        )
        return json_validated_ok(
            request_id,
            {
                "memory": transformed,
                "return_mode": decision["return_mode"],
                "redaction_info": redaction_info,
                "consumable_text": consumable_text(transformed),
            },
            validate_update_memory_response,
        )
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))


@router.post("/mgp/expire")
async def expire_memory(request: Request, payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        request_id, policy_context, body, tenant_error = _prepare_request(
            request,
            payload,
            action="expire",
            request_validator=validate_expire_memory_request,
        )
        if tenant_error:
            return tenant_error
        return _memory_lifecycle_response(
            request_id=request_id,
            policy_context=policy_context,
            body=body,
            action="expire",
            dispatch_action="expire",
            response_validator=validate_expire_memory_response,
        )
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))


@router.post("/mgp/revoke")
async def revoke_memory(request: Request, payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        request_id, policy_context, body, tenant_error = _prepare_request(
            request,
            payload,
            action="revoke",
            request_validator=validate_revoke_memory_request,
        )
        if tenant_error:
            return tenant_error
        return _memory_lifecycle_response(
            request_id=request_id,
            policy_context=policy_context,
            body=body,
            action="revoke",
            dispatch_action="revoke",
            response_validator=validate_revoke_memory_response,
        )
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))


@router.post("/mgp/delete")
async def delete_memory(request: Request, payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        request_id, policy_context, body, tenant_error = _prepare_request(
            request,
            payload,
            action="delete",
            request_validator=validate_delete_memory_request,
        )
        if tenant_error:
            return tenant_error
        return _memory_lifecycle_response(
            request_id=request_id,
            policy_context=policy_context,
            body=body,
            action="delete",
            dispatch_action="delete",
            response_validator=validate_delete_memory_response,
        )
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))


@router.post("/mgp/purge")
async def purge_memory(request: Request, payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        request_id, policy_context, body, tenant_error = _prepare_request(
            request,
            payload,
            action="purge",
            request_validator=validate_purge_memory_request,
        )
        if tenant_error:
            return tenant_error
        return _memory_lifecycle_response(
            request_id=request_id,
            policy_context=policy_context,
            body=body,
            action="purge",
            dispatch_action="purge",
            response_validator=validate_purge_memory_response,
        )
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))


@router.post("/mgp/write/batch")
async def batch_write_memory(request: Request, payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        request_id, policy_context, body, tenant_error = _prepare_request(
            request,
            payload,
            action="write",
            request_validator=validate_write_batch_request,
        )
        if tenant_error:
            return tenant_error
        items = body.get("items", [])
        results: list[dict[str, Any]] = []
        for item in items:
            try:
                transformed, decision, redaction_info, resolution = execute_write(policy_context, item)
                emit_audit_event(
                    request_id=request_id,
                    action="write",
                    target_memory_id=transformed["memory_id"],
                    policy_context=policy_context,
                    decision=decision,
                    backend=adapter_router.adapter_name,
                    lineage_refs=transformed.get("derived_from"),
                )
                results.append(
                    {
                        "status": "ok",
                        "memory": transformed,
                        "return_mode": decision["return_mode"],
                        "redaction_info": redaction_info,
                        "consumable_text": consumable_text(transformed),
                        "resolution": resolution,
                    }
                )
            except GatewayValidationError as error:
                results.append(
                    {
                        "status": "error",
                        "error": {
                            "code": error.code,
                            "message": error.message,
                            "details": error.details,
                        },
                    }
                )
        return json_validated_ok(request_id, {"results": results}, validate_write_batch_response)
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))
