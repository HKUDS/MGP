from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from gateway.middleware import validate_tenant_binding
from gateway.state import settings
from gateway.validation import (
    GatewayValidationError,
    validate_policy_context,
    validate_request_envelope,
    validate_response_envelope,
)

ERROR_STATUS = {
    "MGP_INVALID_OBJECT": 400,
    "MGP_UNSUPPORTED_VERSION": 400,
    "MGP_POLICY_DENIED": 403,
    "MGP_SCOPE_VIOLATION": 403,
    "MGP_MEMORY_NOT_FOUND": 404,
    "MGP_TASK_NOT_FOUND": 404,
    "MGP_CONFLICT_UNRESOLVED": 409,
    "MGP_UNSUPPORTED_CAPABILITY": 501,
    "MGP_BACKEND_ERROR": 502,
}


def status_for_error(code: str) -> int:
    return ERROR_STATUS.get(code, 500)


def build_ok_response(request_id: str, data: dict[str, Any] | None) -> dict[str, Any]:
    payload = {
        "request_id": request_id,
        "status": "ok",
        "error": None,
        "data": data,
    }
    validate_response_envelope(payload)
    return payload


def build_error_response(
    request_id: str,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "request_id": request_id,
        "status": "error",
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "data": None,
    }
    validate_response_envelope(payload)
    return payload


def json_ok(request_id: str, data: dict[str, Any] | None) -> JSONResponse:
    return JSONResponse(status_code=200, content=build_ok_response(request_id, data))


def json_validated_ok(
    request_id: str,
    data: dict[str, Any] | None,
    response_validator: Any,
    status_code: int = 200,
) -> JSONResponse:
    payload = build_ok_response(request_id, data)
    response_validator(payload)
    return JSONResponse(status_code=status_code, content=payload)


def json_error(
    request_id: str,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_for_error(code),
        content=build_error_response(request_id, code, message, details),
    )


def request_id_from_payload(payload: dict[str, Any]) -> str:
    return payload.get("request_id") or f"req_{uuid4().hex}"


def validate_action_request(
    payload: dict[str, Any],
    action: str,
    request_validator: Any,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    request_validator(payload)
    validate_request_envelope(payload)
    validate_policy_context(payload["policy_context"])

    if payload["policy_context"].get("requested_action") != action:
        raise GatewayValidationError(
            "MGP_INVALID_OBJECT",
            f"requested_action must be {action}",
            {"field": "policy_context.requested_action"},
        )

    return payload["request_id"], payload["policy_context"], payload["payload"]


def enforce_tenant_binding(
    request: Request,
    request_id: str,
    policy_context: dict[str, Any],
) -> JSONResponse | None:
    allowed, message = validate_tenant_binding(request, policy_context, settings)
    if allowed:
        return None
    return json_error(request_id, "MGP_SCOPE_VIOLATION", message or "tenant binding failed")
