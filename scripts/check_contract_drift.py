from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "openapi" / "mgp-openapi.yaml"
APP_PATH = ROOT / "reference" / "gateway" / "app.py"
HTTP_PATH = ROOT / "reference" / "gateway" / "http.py"
ROUTES_DIR = ROOT / "reference" / "gateway" / "routes"
VERSION_MODULE_PATH = ROOT / "reference" / "gateway" / "version.py"
README_PATH = ROOT / "README.md"
README_ZH_PATH = ROOT / "README.zh.md"
ERROR_CODE_SCHEMA_PATH = ROOT / "schemas" / "error-code.schema.json"
README_VERSION_RE = re.compile(r"protocol version[^0-9`]*`?v?([0-9]+\.[0-9]+\.[0-9]+)`?", re.IGNORECASE)
README_ZH_VERSION_RE = re.compile(r"协议版本[^0-9`]*`?v?([0-9]+\.[0-9]+\.[0-9]+)`?")

SCHEMA_COMPONENT_REFS = {
    "ProtocolCapabilities": "../schemas/protocol-capabilities.schema.json",
    "RuntimeCapabilities": "../schemas/runtime-capabilities.schema.json",
    "NegotiatedCapabilities": "../schemas/negotiated-capabilities.schema.json",
    "AsyncTask": "../schemas/async-task.schema.json",
    "ProgressEvent": "../schemas/progress-event.schema.json",
    "GetTaskRequest": "../schemas/get-task.request.schema.json",
    "GetTaskResponse": "../schemas/get-task.response.schema.json",
    "CancelTaskRequest": "../schemas/cancel-task.request.schema.json",
    "CancelTaskResponse": "../schemas/cancel-task.response.schema.json",
    "InitializeRequest": "../schemas/initialize.request.schema.json",
    "InitializeResponse": "../schemas/initialize.response.schema.json",
    "MemoryObject": "../schemas/memory-object.schema.json",
    "MemoryCandidate": "../schemas/memory-candidate.schema.json",
    "RecallIntent": "../schemas/recall-intent.schema.json",
    "PolicyContext": "../schemas/policy-context.schema.json",
    "RequestEnvelope": "../schemas/request-envelope.schema.json",
    "ResponseEnvelope": "../schemas/response-envelope.schema.json",
    "AuditEvent": "../schemas/audit-event.schema.json",
    "BackendCapabilities": "../schemas/backend-capabilities.schema.json",
    "AdapterManifest": "../schemas/adapter-manifest.schema.json",
    "RedactionInfo": "../schemas/redaction-info.schema.json",
    "SearchResultItem": "../schemas/search-result-item.schema.json",
    "PartialFailure": "../schemas/partial-failure.schema.json",
    "WriteMemoryRequest": "../schemas/write-memory.request.schema.json",
    "WriteMemoryResponse": "../schemas/write-memory.response.schema.json",
    "SearchMemoryRequest": "../schemas/search-memory.request.schema.json",
    "SearchMemoryResponse": "../schemas/search-memory.response.schema.json",
    "GetMemoryRequest": "../schemas/get-memory.request.schema.json",
    "GetMemoryResponse": "../schemas/get-memory.response.schema.json",
    "UpdateMemoryRequest": "../schemas/update-memory.request.schema.json",
    "UpdateMemoryResponse": "../schemas/update-memory.response.schema.json",
    "ExpireMemoryRequest": "../schemas/expire-memory.request.schema.json",
    "ExpireMemoryResponse": "../schemas/expire-memory.response.schema.json",
    "RevokeMemoryRequest": "../schemas/revoke-memory.request.schema.json",
    "RevokeMemoryResponse": "../schemas/revoke-memory.response.schema.json",
    "DeleteMemoryRequest": "../schemas/delete-memory.request.schema.json",
    "DeleteMemoryResponse": "../schemas/delete-memory.response.schema.json",
    "PurgeMemoryRequest": "../schemas/purge-memory.request.schema.json",
    "PurgeMemoryResponse": "../schemas/purge-memory.response.schema.json",
    "BatchWriteRequest": "../schemas/write-batch.request.schema.json",
    "BatchWriteResponse": "../schemas/write-batch.response.schema.json",
    "ExportRequest": "../schemas/export.request.schema.json",
    "ExportResponse": "../schemas/export.response.schema.json",
    "ImportRequest": "../schemas/import.request.schema.json",
    "ImportResponse": "../schemas/import.response.schema.json",
    "SyncRequest": "../schemas/sync.request.schema.json",
    "SyncResponse": "../schemas/sync.response.schema.json",
    "CapabilitiesResponse": "../schemas/capabilities.response.schema.json",
    "AuditQueryRequest": "../schemas/audit-query.request.schema.json",
    "AuditQueryResponse": "../schemas/audit-query.response.schema.json",
}

OPERATION_COMPONENTS = {
    ("/mgp/initialize", "post"): {
        "request": "InitializeRequest",
        "response": "InitializeResponse",
        "errors": {
            "400": "BadRequest",
            "500": "InternalError",
            "501": "UnsupportedCapability",
            "502": "BackendError",
        },
    },
    ("/mgp/write", "post"): {
        "request": "WriteMemoryRequest",
        "response": "WriteMemoryResponse",
        "errors": {
            "400": "BadRequest",
            "403": "Forbidden",
            "409": "Conflict",
            "500": "InternalError",
            "502": "BackendError",
        },
    },
    ("/mgp/search", "post"): {
        "request": "SearchMemoryRequest",
        "response": "SearchMemoryResponse",
        "errors": {
            "400": "BadRequest",
            "403": "Forbidden",
            "500": "InternalError",
            "502": "BackendError",
        },
    },
    ("/mgp/get", "post"): {
        "request": "GetMemoryRequest",
        "response": "GetMemoryResponse",
        "errors": {
            "400": "BadRequest",
            "403": "Forbidden",
            "404": "NotFound",
            "500": "InternalError",
            "502": "BackendError",
        },
    },
    ("/mgp/update", "post"): {
        "request": "UpdateMemoryRequest",
        "response": "UpdateMemoryResponse",
        "errors": {
            "400": "BadRequest",
            "403": "Forbidden",
            "404": "NotFound",
            "409": "Conflict",
            "500": "InternalError",
            "502": "BackendError",
        },
    },
    ("/mgp/expire", "post"): {
        "request": "ExpireMemoryRequest",
        "response": "ExpireMemoryResponse",
        "errors": {
            "400": "BadRequest",
            "403": "Forbidden",
            "404": "NotFound",
            "500": "InternalError",
            "502": "BackendError",
        },
    },
    ("/mgp/revoke", "post"): {
        "request": "RevokeMemoryRequest",
        "response": "RevokeMemoryResponse",
        "errors": {
            "400": "BadRequest",
            "403": "Forbidden",
            "404": "NotFound",
            "500": "InternalError",
            "502": "BackendError",
        },
    },
    ("/mgp/delete", "post"): {
        "request": "DeleteMemoryRequest",
        "response": "DeleteMemoryResponse",
        "errors": {
            "400": "BadRequest",
            "403": "Forbidden",
            "404": "NotFound",
            "500": "InternalError",
            "502": "BackendError",
        },
    },
    ("/mgp/purge", "post"): {
        "request": "PurgeMemoryRequest",
        "response": "PurgeMemoryResponse",
        "errors": {
            "400": "BadRequest",
            "403": "Forbidden",
            "404": "NotFound",
            "500": "InternalError",
            "502": "BackendError",
        },
    },
    ("/mgp/write/batch", "post"): {
        "request": "BatchWriteRequest",
        "response": "BatchWriteResponse",
        "errors": {"400": "BadRequest", "403": "Forbidden", "500": "InternalError", "502": "BackendError"},
    },
    ("/mgp/export", "post"): {
        "request": "ExportRequest",
        "response": "ExportResponse",
        "errors": {"400": "BadRequest", "403": "Forbidden", "500": "InternalError", "502": "BackendError"},
    },
    ("/mgp/import", "post"): {
        "request": "ImportRequest",
        "response": "ImportResponse",
        "errors": {"400": "BadRequest", "403": "Forbidden", "500": "InternalError", "502": "BackendError"},
    },
    ("/mgp/sync", "post"): {
        "request": "SyncRequest",
        "response": "SyncResponse",
        "errors": {"400": "BadRequest", "403": "Forbidden", "500": "InternalError", "502": "BackendError"},
    },
    ("/mgp/tasks/get", "post"): {
        "request": "GetTaskRequest",
        "response": "GetTaskResponse",
        "errors": {"400": "BadRequest", "404": "NotFound", "500": "InternalError", "502": "BackendError"},
    },
    ("/mgp/tasks/cancel", "post"): {
        "request": "CancelTaskRequest",
        "response": "CancelTaskResponse",
        "errors": {"400": "BadRequest", "404": "NotFound", "500": "InternalError", "502": "BackendError"},
    },
    ("/mgp/capabilities", "get"): {
        "response": "CapabilitiesResponse",
        "errors": {"500": "InternalError", "502": "BackendError"},
    },
    ("/mgp/audit/query", "post"): {
        "request": "AuditQueryRequest",
        "response": "AuditQueryResponse",
        "errors": {"400": "BadRequest", "403": "Forbidden", "500": "InternalError", "502": "BackendError"},
    },
}

REQUEST_ID_VERSION_PATHS = {
    "/mgp/write",
    "/mgp/search",
    "/mgp/get",
    "/mgp/update",
    "/mgp/expire",
    "/mgp/revoke",
    "/mgp/delete",
    "/mgp/purge",
    "/mgp/write/batch",
    "/mgp/export",
    "/mgp/import",
    "/mgp/sync",
    "/mgp/audit/query",
}


class ContractDriftError(Exception):
    pass


def _load_openapi() -> dict[str, Any]:
    return yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))


def _load_error_codes() -> list[str]:
    schema = json.loads(ERROR_CODE_SCHEMA_PATH.read_text(encoding="utf-8"))
    return list(schema["enum"])


def _extract_protocol_version() -> str:
    module = ast.parse(VERSION_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(module):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "PROTOCOL_VERSION":
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    return node.value.value
    raise ContractDriftError("Could not determine PROTOCOL_VERSION from reference/gateway/version.py")


def _extract_app_metadata() -> tuple[set[tuple[str, str]], set[str]]:
    error_status_codes: set[str] = set()
    routes: set[tuple[str, str]] = set()

    http_module = ast.parse(HTTP_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(http_module):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ERROR_STATUS":
                    if not isinstance(node.value, ast.Dict):
                        raise ContractDriftError("ERROR_STATUS must remain a literal dictionary.")
                    for key in node.value.keys:
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            error_status_codes.add(key.value)

    route_sources = [APP_PATH, *sorted(ROUTES_DIR.glob("*.py"))]
    for route_path in route_sources:
        module = ast.parse(route_path.read_text(encoding="utf-8"))
        for node in ast.walk(module):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                func = decorator.func
                if not isinstance(func, ast.Attribute):
                    continue
                if not isinstance(func.value, ast.Name) or func.value.id not in {"app", "router"}:
                    continue
                if func.attr not in {"get", "post"}:
                    continue
                if (
                    not decorator.args
                    or not isinstance(decorator.args[0], ast.Constant)
                    or not isinstance(decorator.args[0].value, str)
                ):
                    continue
                routes.add((decorator.args[0].value, func.attr))

    return routes, error_status_codes


def _extract_readme_version(path: Path, pattern: re.Pattern[str]) -> str:
    contents = path.read_text(encoding="utf-8")
    match = pattern.search(contents)
    if not match:
        raise ContractDriftError(f"Could not find protocol version marker in {path.relative_to(ROOT)}")
    return match.group(1)


def _schema_ref(component_name: str) -> str:
    return f"#/components/schemas/{component_name}"


def _response_ref(response_name: str) -> str:
    return f"#/components/responses/{response_name}"


def _assert_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        raise ContractDriftError(f"{message}: expected {expected!r}, got {actual!r}")


def _validate_schema_component_refs(openapi: dict[str, Any]) -> None:
    components = openapi["components"]["schemas"]
    for component_name, ref_path in SCHEMA_COMPONENT_REFS.items():
        component = components.get(component_name)
        if not isinstance(component, dict):
            raise ContractDriftError(f"Missing OpenAPI component schema: {component_name}")
        _assert_equal(component.get("$ref"), ref_path, f"Unexpected schema ref for component {component_name}")


def _validate_operation_contracts(openapi: dict[str, Any]) -> None:
    paths = openapi["paths"]
    for (path_name, method), expectations in OPERATION_COMPONENTS.items():
        if path_name not in paths:
            raise ContractDriftError(f"Missing OpenAPI path: {path_name}")
        operation = paths[path_name].get(method)
        if not isinstance(operation, dict):
            raise ContractDriftError(f"Missing {method.upper()} operation for {path_name}")

        if "request" in expectations:
            request_schema_ref = (
                operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
            )
            _assert_equal(
                request_schema_ref,
                _schema_ref(cast(str, expectations["request"])),
                f"Unexpected request schema for {method.upper()} {path_name}",
            )

        response_schema_ref = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        _assert_equal(
            response_schema_ref,
            _schema_ref(cast(str, expectations["response"])),
            f"Unexpected 200 response schema for {method.upper()} {path_name}",
        )

        if path_name in {"/mgp/export", "/mgp/import", "/mgp/sync"}:
            accepted_response_ref = operation["responses"]["202"]["content"]["application/json"]["schema"]["$ref"]
            _assert_equal(
                accepted_response_ref,
                _schema_ref(cast(str, expectations["response"])),
                f"Unexpected 202 response schema for {method.upper()} {path_name}",
            )

        for status_code, response_name in cast(dict[str, str], expectations["errors"]).items():
            response_ref = operation["responses"][status_code]["$ref"]
            _assert_equal(
                response_ref,
                _response_ref(response_name),
                f"Unexpected error response mapping for {method.upper()} {path_name} status {status_code}",
            )

        if path_name in REQUEST_ID_VERSION_PATHS:
            parameter_refs = {entry["$ref"] for entry in operation.get("parameters", [])}
            expected_parameter_refs = {
                "#/components/parameters/MgpRequestId",
                "#/components/parameters/MgpVersion",
            }
            _assert_equal(
                parameter_refs,
                expected_parameter_refs,
                f"Unexpected shared parameters for {method.upper()} {path_name}",
            )


def _validate_error_contract(openapi: dict[str, Any], error_status_codes: set[str]) -> None:
    schema_codes = set(_load_error_codes())
    _assert_equal(error_status_codes, schema_codes, "Gateway ERROR_STATUS keys drifted from error-code.schema.json")

    components = openapi["components"]["schemas"]
    error_code_ref = components["ErrorObject"]["properties"]["code"]["$ref"]
    _assert_equal(error_code_ref, "../schemas/error-code.schema.json", "ErrorObject.code ref drifted")

    partial_failure_ref = components["PartialFailure"]["$ref"]
    _assert_equal(partial_failure_ref, "../schemas/partial-failure.schema.json", "PartialFailure component ref drifted")

    envelope_required = set(components["ErrorEnvelope"]["required"])
    _assert_equal(
        envelope_required,
        {"request_id", "status", "error", "data"},
        "ErrorEnvelope required fields drifted",
    )


def main() -> int:
    openapi = _load_openapi()
    protocol_version = _extract_protocol_version()
    app_routes, error_status_codes = _extract_app_metadata()
    governed_routes = {route for route in app_routes if route[0].startswith("/mgp/")}

    readme_version = _extract_readme_version(README_PATH, README_VERSION_RE)
    readme_zh_version = _extract_readme_version(README_ZH_PATH, README_ZH_VERSION_RE)
    openapi_version = openapi["info"]["version"]

    _assert_equal(openapi_version, protocol_version, "OpenAPI version drifted from protocol version")
    _assert_equal(readme_version, protocol_version, "README protocol version drifted from protocol version")
    _assert_equal(readme_zh_version, protocol_version, "README.zh protocol version drifted from protocol version")

    expected_routes = set(OPERATION_COMPONENTS.keys())
    _assert_equal(
        governed_routes,
        expected_routes,
        "Reference gateway MGP routes drifted from expected contract routes",
    )
    openapi_routes = {
        (path_name, method)
        for path_name, methods in openapi["paths"].items()
        for method in methods
        if method in {"get", "post"}
    }
    _assert_equal(
        openapi_routes,
        expected_routes,
        "OpenAPI routes drifted from expected contract routes",
    )

    _validate_schema_component_refs(openapi)
    _validate_operation_contracts(openapi)
    _validate_error_contract(openapi, error_status_codes)

    print("validated contract drift checks")
    print(f"version: {protocol_version}")
    print(f"routes: {len(expected_routes)}")
    print(f"schema-backed components: {len(SCHEMA_COMPONENT_REFS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
