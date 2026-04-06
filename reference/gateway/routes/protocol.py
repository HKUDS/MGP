from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gateway.http import (
    build_ok_response,
    enforce_tenant_binding,
    json_error,
    json_validated_ok,
    request_id_from_payload,
    validate_action_request,
)
from gateway.operations import (
    build_initialize_response,
    create_async_task,
    export_memories_data,
    import_memories_data,
    negotiate_profiles,
    negotiate_protocol_version,
    negotiate_runtime_capabilities,
    protocol_capabilities,
    supported_protocol_versions,
    sync_memories_data,
    task_data,
    validate_requested_protocol_capabilities,
)
from gateway.state import (
    TRANSPORT_PROFILE,
    audit_sink,
    task_store,
)
from gateway.state import (
    router as adapter_router,
)
from gateway.validation import (
    GatewayValidationError,
    validate_adapter_manifest,
    validate_audit_query_request,
    validate_audit_query_response,
    validate_cancel_task_request,
    validate_cancel_task_response,
    validate_capabilities_response,
    validate_export_request,
    validate_export_response,
    validate_get_task_request,
    validate_get_task_response,
    validate_import_request,
    validate_import_response,
    validate_initialize_request,
    validate_runtime_capabilities,
    validate_sync_request,
    validate_sync_response,
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


@router.post("/mgp/initialize")
async def initialize_protocol(payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        validate_initialize_request(payload)
        request_id = payload["request_id"]

        manifest = adapter_router.get_manifest()
        validate_adapter_manifest(manifest)
        supported_versions = supported_protocol_versions(manifest)
        chosen_version = negotiate_protocol_version(payload, supported_versions)

        requested_transport = payload.get("transport_profile")
        if requested_transport and requested_transport != TRANSPORT_PROFILE:
            raise GatewayValidationError(
                "MGP_UNSUPPORTED_CAPABILITY",
                "requested transport profile is not supported by this gateway",
                {
                    "requested_transport_profile": requested_transport,
                    "supported_transport_profiles": [TRANSPORT_PROFILE],
                },
            )

        protocol_caps = protocol_capabilities()
        validate_requested_protocol_capabilities(payload.get("requested_capabilities"), protocol_caps)

        runtime_capabilities = payload.get("runtime_capabilities")
        if runtime_capabilities is not None:
            validate_runtime_capabilities(runtime_capabilities)

        accepted_transport_profiles = (runtime_capabilities or {}).get("accepted_transport_profiles")
        if accepted_transport_profiles is not None and TRANSPORT_PROFILE not in accepted_transport_profiles:
            raise GatewayValidationError(
                "MGP_UNSUPPORTED_CAPABILITY",
                "runtime does not accept the selected transport profile",
                {
                    "accepted_transport_profiles": accepted_transport_profiles,
                    "selected_transport_profile": TRANSPORT_PROFILE,
                },
            )

        negotiated_profiles = negotiate_profiles(
            payload.get("requested_profiles"),
            protocol_caps["supported_profiles"],
            runtime_capabilities,
        )
        negotiated_capabilities = negotiate_runtime_capabilities(
            runtime_capabilities,
            manifest,
            protocol_caps,
        )

        return JSONResponse(
            status_code=200,
            content=build_initialize_response(
                request_id,
                chosen_version=chosen_version,
                supported_versions=supported_versions,
                negotiated_profiles=negotiated_profiles,
                protocol_capabilities=protocol_caps,
                negotiated_capabilities=negotiated_capabilities,
            ),
        )
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))


@router.post("/mgp/export")
async def export_memories(request: Request, payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        request_id, policy_context, body, tenant_error = _prepare_request(
            request,
            payload,
            action="read",
            request_validator=validate_export_request,
        )
        if tenant_error:
            return tenant_error
        if body.get("execution_mode") == "async":
            task = create_async_task(
                operation="export",
                request_id=request_id,
                runner=lambda: export_memories_data(request_id, policy_context, body),
            )
            return json_validated_ok(request_id, task_data(task), validate_export_response, status_code=202)
        return json_validated_ok(
            request_id,
            export_memories_data(request_id, policy_context, body),
            validate_export_response,
        )
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))


@router.post("/mgp/import")
async def import_memories(request: Request, payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        request_id, policy_context, body, tenant_error = _prepare_request(
            request,
            payload,
            action="write",
            request_validator=validate_import_request,
        )
        if tenant_error:
            return tenant_error
        if body.get("execution_mode") == "async":
            task = create_async_task(
                operation="import",
                request_id=request_id,
                runner=lambda: import_memories_data(policy_context, body),
            )
            return json_validated_ok(request_id, task_data(task), validate_import_response, status_code=202)
        return json_validated_ok(request_id, import_memories_data(policy_context, body), validate_import_response)
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))


@router.post("/mgp/sync")
async def sync_memories(request: Request, payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        request_id, policy_context, body, tenant_error = _prepare_request(
            request,
            payload,
            action="read",
            request_validator=validate_sync_request,
        )
        if tenant_error:
            return tenant_error
        if body.get("execution_mode") == "async":
            task = create_async_task(
                operation="sync",
                request_id=request_id,
                runner=lambda: sync_memories_data(body),
            )
            return json_validated_ok(request_id, task_data(task), validate_sync_response, status_code=202)
        return json_validated_ok(request_id, sync_memories_data(body), validate_sync_response)
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))


@router.post("/mgp/tasks/get")
async def get_task(payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        validate_get_task_request(payload)
        request_id = payload["request_id"]
        task = task_store.get(payload["task_id"])
        if task is None:
            return json_error(request_id, "MGP_TASK_NOT_FOUND", "task not found")

        response = build_ok_response(request_id, task_data(task))
        validate_get_task_response(response)
        return JSONResponse(status_code=200, content=response)
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))


@router.post("/mgp/tasks/cancel")
async def cancel_task(payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        validate_cancel_task_request(payload)
        request_id = payload["request_id"]
        task = task_store.cancel(payload["task_id"], payload.get("reason"))
        if task is None:
            return json_error(request_id, "MGP_TASK_NOT_FOUND", "task not found")

        response = build_ok_response(request_id, task_data(task))
        validate_cancel_task_response(response)
        return JSONResponse(status_code=200, content=response)
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))


@router.get("/mgp/capabilities")
async def get_capabilities() -> JSONResponse:
    try:
        manifest = adapter_router.get_manifest()
        validate_adapter_manifest(manifest)
        payload = {
            "manifest": manifest,
            "protocol_capabilities": protocol_capabilities(),
        }
        validate_capabilities_response(payload)
        return JSONResponse(status_code=200, content=payload)
    except GatewayValidationError as error:
        return json_error("capabilities", error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error("capabilities", "MGP_BACKEND_ERROR", str(error))


@router.post("/mgp/audit/query")
async def query_audit_events(request: Request, payload: dict[str, Any]) -> JSONResponse:
    request_id = request_id_from_payload(payload)
    try:
        request_id, policy_context, body, tenant_error = _prepare_request(
            request,
            payload,
            action="read",
            request_validator=validate_audit_query_request,
        )
        if tenant_error:
            return tenant_error
        events, next_token = audit_sink.query(
            action=body.get("action"),
            target_memory_id=body.get("target_memory_id"),
            actor_id=body.get("actor_id"),
            request_id=body.get("request_id"),
            correlation_id=body.get("correlation_id"),
            pagination_token=body.get("pagination_token"),
            limit=body.get("limit", 50),
        )
        data: dict[str, Any] = {"events": events}
        if next_token:
            data["next_token"] = next_token
        return json_validated_ok(request_id, data, validate_audit_query_response)
    except GatewayValidationError as error:
        return json_error(request_id, error.code, error.message, error.details)
    except Exception as error:  # pragma: no cover - defensive path
        return json_error(request_id, "MGP_BACKEND_ERROR", str(error))
