from __future__ import annotations

import json
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

from gateway.config import ensure_repo_root_on_path, project_root

ensure_repo_root_on_path()


class GatewayValidationError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


_ROOT = project_root()
_SCHEMA_DIR = _ROOT / "schemas"


def _schema_files() -> list[Any]:
    try:
        package_root = resources.files("schemas")
        return sorted(
            (item for item in package_root.iterdir() if item.name.endswith(".json")),
            key=lambda item: item.name,
        )
    except Exception:
        return sorted(_SCHEMA_DIR.glob("*.json"), key=lambda item: item.name)


def _read_json(path_like: Any) -> dict[str, Any]:
    return json.loads(path_like.read_text(encoding="utf-8"))


def _load_registry() -> Registry:
    registry = Registry()
    for schema_path in _schema_files():
        contents = _read_json(schema_path)
        resource = Resource.from_contents(contents)
        schema_id = contents.get("$id")
        if schema_id:
            registry = registry.with_resource(schema_id, resource)
        registry = registry.with_resource(schema_path.name, resource)
    return registry


_REGISTRY = _load_registry()


def load_schema(schema_name: str) -> dict[str, Any]:
    try:
        package_path = resources.files("schemas").joinpath(schema_name)
        return _read_json(package_path)
    except Exception:
        path = _SCHEMA_DIR / schema_name
        return _read_json(path)


def validate_against_schema(instance: Any, schema_name: str) -> None:
    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema, registry=_REGISTRY)
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if not errors:
        return

    first = errors[0]
    field = ".".join(str(part) for part in first.path) or "root"
    raise GatewayValidationError(
        "MGP_INVALID_OBJECT",
        first.message,
        {"field": field, "schema": schema_name},
    )


def validate_request_envelope(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "request-envelope.schema.json")


def validate_response_envelope(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "response-envelope.schema.json")


def validate_memory_object(memory: dict[str, Any]) -> None:
    validate_against_schema(memory, "memory-object.schema.json")


def validate_policy_context(policy_context: dict[str, Any]) -> None:
    validate_against_schema(policy_context, "policy-context.schema.json")


def validate_audit_event(event: dict[str, Any]) -> None:
    validate_against_schema(event, "audit-event.schema.json")


def validate_adapter_manifest(manifest: dict[str, Any]) -> None:
    validate_against_schema(manifest, "adapter-manifest.schema.json")


def validate_capabilities_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "capabilities.response.schema.json")


def validate_protocol_capabilities(capabilities: dict[str, Any]) -> None:
    validate_against_schema(capabilities, "protocol-capabilities.schema.json")


def validate_runtime_capabilities(capabilities: dict[str, Any]) -> None:
    validate_against_schema(capabilities, "runtime-capabilities.schema.json")


def validate_negotiated_capabilities(capabilities: dict[str, Any]) -> None:
    validate_against_schema(capabilities, "negotiated-capabilities.schema.json")


def validate_async_task(task: dict[str, Any]) -> None:
    validate_against_schema(task, "async-task.schema.json")


def validate_get_task_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "get-task.request.schema.json")


def validate_get_task_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "get-task.response.schema.json")


def validate_cancel_task_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "cancel-task.request.schema.json")


def validate_cancel_task_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "cancel-task.response.schema.json")


def validate_initialize_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "initialize.request.schema.json")


def validate_initialize_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "initialize.response.schema.json")


def validate_memory_candidate(candidate: dict[str, Any]) -> None:
    validate_against_schema(candidate, "memory-candidate.schema.json")


def validate_memory_merge_hint(merge_hint: dict[str, Any]) -> None:
    validate_against_schema(merge_hint, "memory-merge-hint.schema.json")


def validate_recall_intent(intent: dict[str, Any]) -> None:
    validate_against_schema(intent, "recall-intent.schema.json")


def validate_search_result_item(item: dict[str, Any]) -> None:
    validate_against_schema(item, "search-result-item.schema.json")


def validate_write_memory_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "write-memory.request.schema.json")


def validate_write_memory_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "write-memory.response.schema.json")


def validate_search_memory_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "search-memory.request.schema.json")


def validate_search_memory_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "search-memory.response.schema.json")


def validate_get_memory_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "get-memory.request.schema.json")


def validate_get_memory_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "get-memory.response.schema.json")


def validate_update_memory_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "update-memory.request.schema.json")


def validate_update_memory_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "update-memory.response.schema.json")


def validate_expire_memory_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "expire-memory.request.schema.json")


def validate_expire_memory_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "expire-memory.response.schema.json")


def validate_revoke_memory_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "revoke-memory.request.schema.json")


def validate_revoke_memory_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "revoke-memory.response.schema.json")


def validate_delete_memory_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "delete-memory.request.schema.json")


def validate_delete_memory_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "delete-memory.response.schema.json")


def validate_purge_memory_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "purge-memory.request.schema.json")


def validate_purge_memory_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "purge-memory.response.schema.json")


def validate_audit_query_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "audit-query.request.schema.json")


def validate_audit_query_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "audit-query.response.schema.json")


def validate_write_batch_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "write-batch.request.schema.json")


def validate_write_batch_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "write-batch.response.schema.json")


def validate_export_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "export.request.schema.json")


def validate_export_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "export.response.schema.json")


def validate_import_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "import.request.schema.json")


def validate_import_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "import.response.schema.json")


def validate_sync_request(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "sync.request.schema.json")


def validate_sync_response(payload: dict[str, Any]) -> None:
    validate_against_schema(payload, "sync.response.schema.json")


def format_validation_error(error: ValidationError) -> dict[str, Any]:
    field = ".".join(str(part) for part in error.path) or "root"
    return {"field": field, "message": error.message}
