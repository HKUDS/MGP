from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = ROOT / "reference"
if str(REFERENCE_DIR) not in sys.path:
    sys.path.insert(0, str(REFERENCE_DIR))

from gateway.validation import GatewayValidationError, validate_against_schema

OPENAPI_PATH = ROOT / "openapi" / "mgp-openapi.yaml"


def _load_openapi() -> dict:
    return yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))


def test_memory_object_valid(make_memory):
    memory = make_memory(content={"theme": "dark"})
    validate_against_schema(memory, "memory-object.schema.json")


def test_memory_object_missing_required_field(make_memory):
    memory = make_memory()
    memory.pop("memory_id")
    with pytest.raises(GatewayValidationError):
        validate_against_schema(memory, "memory-object.schema.json")


def test_memory_object_invalid_enum(make_memory):
    memory = make_memory()
    memory["scope"] = "invalid_scope"
    with pytest.raises(GatewayValidationError):
        validate_against_schema(memory, "memory-object.schema.json")


def test_memory_object_preference_requires_statement(make_memory):
    memory = make_memory(memory_type="preference", content={"preference": "dark mode"})
    memory["content"].pop("statement", None)
    with pytest.raises(GatewayValidationError):
        validate_against_schema(memory, "memory-object.schema.json")


def test_policy_context_valid(make_policy_context):
    context = make_policy_context(action="write")
    validate_against_schema(context, "policy-context.schema.json")


def test_policy_context_missing_actor_agent(make_policy_context):
    context = make_policy_context(action="write")
    context.pop("actor_agent")
    with pytest.raises(GatewayValidationError):
        validate_against_schema(context, "policy-context.schema.json")


def test_policy_context_invalid_requested_action(make_policy_context):
    context = make_policy_context(action="write")
    context["requested_action"] = "destroy"
    with pytest.raises(GatewayValidationError):
        validate_against_schema(context, "policy-context.schema.json")


def test_policy_context_extended_fields_are_valid(make_policy_context):
    context = make_policy_context(
        action="search",
        session_id="session_1",
        channel="cli",
        chat_id="chat_1",
        correlation_id="trace_1",
    )
    context["runtime_id"] = "nanobot"
    context["runtime_instance_id"] = "nanobot-instance-1"
    context["consent_basis"] = "explicit_user"
    context["assertion_origin"] = "runtime_memory_extraction"
    validate_against_schema(context, "policy-context.schema.json")


def test_audit_event_valid(make_policy_context):
    event = {
        "event_id": "evt_1",
        "timestamp": "2026-03-17T12:00:00Z",
        "request_id": "req_1",
        "actor": {"kind": "agent", "id": "nanobot/main"},
        "action": "write",
        "target_memory_id": "mem_1",
        "policy_context": make_policy_context(action="write"),
        "decision": {
            "decision": "allow",
            "reason_code": "allowed",
            "applied_rules": [],
            "return_mode": "raw",
        },
        "backend": "memory",
        "lineage_refs": [],
    }
    validate_against_schema(event, "audit-event.schema.json")


def test_audit_event_missing_event_id(make_policy_context):
    event = {
        "timestamp": "2026-03-17T12:00:00Z",
        "request_id": "req_1",
        "actor": {"kind": "agent", "id": "nanobot/main"},
        "action": "write",
        "target_memory_id": "mem_1",
        "policy_context": make_policy_context(action="write"),
        "decision": {
            "decision": "allow",
            "reason_code": "allowed",
            "applied_rules": [],
            "return_mode": "raw",
        },
    }
    with pytest.raises(GatewayValidationError):
        validate_against_schema(event, "audit-event.schema.json")


def test_memory_candidate_valid():
    candidate = {
        "candidate_kind": "assertion",
        "subject": {"kind": "user", "id": "user_1"},
        "scope": "user",
        "proposed_type": "preference",
        "statement": "User prefers concise replies.",
        "source": {"kind": "chat", "ref": "chat:1"},
        "content": {"statement": "User prefers concise replies.", "preference": "concise replies"},
        "source_evidence": [{"kind": "chat_message", "ref": "chat:1"}],
        "merge_hint": {"strategy": "dedupe", "dedupe_key": "user_1:preference:concise"},
    }
    validate_against_schema(candidate, "memory-candidate.schema.json")


def test_memory_candidate_missing_statement():
    candidate = {
        "candidate_kind": "assertion",
        "subject": {"kind": "user", "id": "user_1"},
        "scope": "user",
        "proposed_type": "preference",
        "source": {"kind": "chat", "ref": "chat:1"},
    }
    with pytest.raises(GatewayValidationError):
        validate_against_schema(candidate, "memory-candidate.schema.json")


def test_recall_intent_valid():
    intent = {
        "query_text": "reply preference token",
        "intent_type": "fact_lookup",
        "keywords": ["reply", "token"],
        "target_memory_types": ["semantic_fact"],
        "subject": {"kind": "user", "id": "user_1"},
        "scope": "user",
        "top_k": 5,
    }
    validate_against_schema(intent, "recall-intent.schema.json")


def test_search_result_item_valid(make_memory):
    item = {
        "memory": make_memory(
            memory_type="semantic_fact",
            content={"statement": "Remember this fact: token is kiwi.", "fact": "token is kiwi."},
        ),
        "score": 1.0,
        "score_kind": "backend_local",
        "backend_origin": "memory",
        "retrieval_mode": "lexical",
        "return_mode": "raw",
        "redaction_info": None,
        "consumable_text": "Remember this fact: token is kiwi.",
        "matched_terms": ["token", "kiwi"],
        "explanation": "Matched lexical terms against normalized memory content.",
    }
    validate_against_schema(item, "search-result-item.schema.json")


def test_adapter_manifest_valid():
    manifest_path = ROOT / "adapters" / "memory" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_against_schema(manifest, "adapter-manifest.schema.json")


def test_adapter_manifest_missing_capabilities():
    manifest_path = ROOT / "adapters" / "memory" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("capabilities")
    with pytest.raises(GatewayValidationError):
        validate_against_schema(manifest, "adapter-manifest.schema.json")


def test_protocol_capabilities_valid():
    capabilities = {
        "supports_discovery": True,
        "supports_initialize": True,
        "supports_runtime_capability_negotiation": True,
        "supports_negotiated_capabilities": True,
        "requires_initialize": False,
        "supports_stateless_http": True,
        "supports_streamable_http": False,
        "supports_sessions": False,
        "supports_async_operations": False,
        "supports_notifications": False,
        "supports_subscriptions": False,
        "supports_ping": False,
        "transport_profiles": ["stateless_http"],
        "supported_profiles": ["core-memory", "governance", "interop", "lifecycle"],
        "default_profile": "core-memory",
        "session_mode": "stateless",
    }
    validate_against_schema(capabilities, "protocol-capabilities.schema.json")


def test_runtime_capabilities_valid():
    capabilities = {
        "supports_consumable_text": True,
        "supports_redaction_info": True,
        "supports_mixed_return_modes": True,
        "supports_partial_failure": True,
        "supports_search_explanations": True,
        "supports_prompt_view": True,
        "supports_async_operations": False,
        "supports_subscriptions": False,
        "preferred_return_modes": ["summary", "masked"],
        "supported_profiles": ["core-memory", "lifecycle"],
        "accepted_transport_profiles": ["stateless_http"],
    }
    validate_against_schema(capabilities, "runtime-capabilities.schema.json")


def test_negotiated_capabilities_valid():
    capabilities = {
        "runtime_capabilities_received": True,
        "supports_consumable_text": True,
        "supports_redaction_info": True,
        "supports_mixed_return_modes": True,
        "supports_partial_failure": True,
        "supports_search_explanations": True,
        "supports_prompt_view": True,
        "supports_delete": True,
        "supports_purge": True,
        "supports_async_operations": False,
        "supports_subscriptions": False,
        "effective_return_modes": ["summary", "masked"],
    }
    validate_against_schema(capabilities, "negotiated-capabilities.schema.json")


def test_async_task_valid():
    task = {
        "task_id": "task_1",
        "operation": "export",
        "status": "pending",
        "request_id": "req_1",
        "created_at": "2026-03-18T10:00:00Z",
        "updated_at": "2026-03-18T10:00:00Z",
        "progress": 0,
        "total": 1,
        "message": "accepted",
        "result": None,
        "error": None,
    }
    validate_against_schema(task, "async-task.schema.json")


def test_progress_event_valid():
    event = {
        "task_id": "task_1",
        "progress": 0.5,
        "total": 1,
        "message": "running",
        "timestamp": "2026-03-18T10:00:01Z",
    }
    validate_against_schema(event, "progress-event.schema.json")


def test_get_task_request_valid():
    payload = {
        "request_id": "req_task_get",
        "task_id": "task_1",
    }
    validate_against_schema(payload, "get-task.request.schema.json")


def test_get_task_response_valid():
    payload = {
        "request_id": "req_task_get",
        "status": "ok",
        "error": None,
        "data": {
            "task": {
                "task_id": "task_1",
                "operation": "export",
                "status": "completed",
                "request_id": "req_1",
                "created_at": "2026-03-18T10:00:00Z",
                "updated_at": "2026-03-18T10:00:02Z",
                "progress": 1,
                "total": 1,
                "message": "completed",
                "result": {"memories": []},
                "error": None,
            }
        },
    }
    validate_against_schema(payload, "get-task.response.schema.json")


def test_cancel_task_request_valid():
    payload = {
        "request_id": "req_task_cancel",
        "task_id": "task_1",
        "reason": "user_cancelled",
    }
    validate_against_schema(payload, "cancel-task.request.schema.json")


def test_cancel_task_response_valid():
    payload = {
        "request_id": "req_task_cancel",
        "status": "ok",
        "error": None,
        "data": {
            "task": {
                "task_id": "task_1",
                "operation": "import",
                "status": "cancelled",
                "request_id": "req_1",
                "created_at": "2026-03-18T10:00:00Z",
                "updated_at": "2026-03-18T10:00:01Z",
                "progress": 0,
                "total": 1,
                "message": "user_cancelled",
                "result": None,
                "error": None,
            }
        },
    }
    validate_against_schema(payload, "cancel-task.response.schema.json")


def test_initialize_request_valid():
    payload = {
        "request_id": "req_init_1",
        "protocol_version": "0.1.0",
        "client": {
            "name": "pytest-client",
            "version": "1.0.0",
            "title": "Pytest Client",
        },
        "requested_profiles": ["core-memory", "lifecycle"],
        "transport_profile": "stateless_http",
    }
    validate_against_schema(payload, "initialize.request.schema.json")


def test_initialize_request_with_supported_versions_valid():
    payload = {
        "request_id": "req_init_2",
        "supported_versions": ["0.3.0", "0.1.0"],
        "preferred_version": "0.3.0",
        "client": {
            "name": "pytest-client",
            "version": "1.0.0",
        },
    }
    validate_against_schema(payload, "initialize.request.schema.json")


def test_initialize_response_valid():
    payload = {
        "request_id": "req_init_1",
        "status": "ok",
        "error": None,
        "data": {
            "chosen_version": "0.1.0",
            "supported_versions": ["0.1.0"],
            "minimum_supported_version": "0.1.0",
            "lifecycle_phase": "ready",
            "session_mode": "stateless",
            "transport_profile": "stateless_http",
            "protocol_capabilities": {
                "supports_discovery": True,
                "supports_initialize": True,
            "supports_runtime_capability_negotiation": True,
            "supports_negotiated_capabilities": True,
                "requires_initialize": False,
                "supports_stateless_http": True,
                "supports_streamable_http": False,
                "supports_sessions": False,
                "supports_async_operations": False,
                "supports_notifications": False,
                "supports_subscriptions": False,
                "supports_ping": False,
                "transport_profiles": ["stateless_http"],
                "supported_profiles": ["core-memory", "governance", "interop", "lifecycle"],
                "default_profile": "core-memory",
                "session_mode": "stateless",
            },
            "negotiated_capabilities": {
                "runtime_capabilities_received": True,
                "supports_consumable_text": True,
                "supports_redaction_info": True,
                "supports_mixed_return_modes": True,
                "supports_partial_failure": True,
                "supports_search_explanations": True,
                "supports_prompt_view": True,
                "supports_delete": True,
                "supports_purge": True,
                "supports_async_operations": False,
                "supports_subscriptions": False,
                "effective_return_modes": ["raw", "summary"],
            },
            "negotiated_profiles": ["core-memory", "lifecycle"],
            "server_info": {
                "name": "mgp-reference-gateway",
                "version": "0.1.0",
            },
            "discovery": {
                "capabilities_uri": "/mgp/capabilities",
            },
        },
    }
    validate_against_schema(payload, "initialize.response.schema.json")


def test_capabilities_response_valid():
    payload = {
        "manifest": json.loads((ROOT / "adapters" / "memory" / "manifest.json").read_text(encoding="utf-8")),
        "protocol_capabilities": {
            "supports_discovery": True,
            "supports_initialize": True,
            "supports_runtime_capability_negotiation": True,
            "supports_negotiated_capabilities": True,
            "requires_initialize": False,
            "supports_stateless_http": True,
            "supports_streamable_http": False,
            "supports_sessions": False,
            "supports_async_operations": False,
            "supports_notifications": False,
            "supports_subscriptions": False,
            "supports_ping": False,
            "transport_profiles": ["stateless_http"],
            "supported_profiles": ["core-memory", "governance", "interop", "lifecycle"],
            "default_profile": "core-memory",
            "session_mode": "stateless",
        },
    }
    validate_against_schema(payload, "capabilities.response.schema.json")


def test_write_batch_request_valid(make_memory, make_policy_context):
    payload = {
        "request_id": "req_batch_1",
        "policy_context": make_policy_context(action="write"),
        "payload": {
            "items": [
                {"memory": make_memory(memory_type="semantic_fact")},
            ]
        },
    }
    validate_against_schema(payload, "write-batch.request.schema.json")


def test_write_batch_response_valid(make_memory):
    payload = {
        "request_id": "req_batch_1",
        "status": "ok",
        "error": None,
        "data": {
            "results": [
                {
                    "status": "ok",
                    "memory": make_memory(memory_type="semantic_fact"),
                    "return_mode": "raw",
                    "redaction_info": None,
                    "consumable_text": "Remember this fact: default fact.",
                    "resolution": "created",
                }
            ]
        },
    }
    validate_against_schema(payload, "write-batch.response.schema.json")


def test_export_request_valid(make_policy_context):
    payload = {
        "request_id": "req_export_1",
        "policy_context": make_policy_context(action="read"),
        "payload": {
            "include_inactive": False,
            "limit": 25,
            "timeout_ms": 0,
        },
    }
    validate_against_schema(payload, "export.request.schema.json")


def test_import_request_valid(make_memory, make_policy_context):
    payload = {
        "request_id": "req_import_1",
        "policy_context": make_policy_context(action="write"),
        "payload": {
            "memories": [make_memory(memory_type="semantic_fact")],
            "execution_mode": "sync",
            "timeout_ms": 0,
        },
    }
    validate_against_schema(payload, "import.request.schema.json")


def test_sync_request_valid(make_policy_context):
    payload = {
        "request_id": "req_sync_1",
        "policy_context": make_policy_context(action="read"),
        "payload": {
            "cursor": "1",
            "limit": 10,
            "timeout_ms": 0,
        },
    }
    validate_against_schema(payload, "sync.request.schema.json")


def test_docs_preference_memory_examples_are_schema_valid():
    memory = {
        "memory_id": "mem_docs_1",
        "subject": {"kind": "user", "id": "user_alice"},
        "scope": "user",
        "type": "preference",
        "content": {
            "statement": "User prefers Python.",
            "preference": "Python",
            "preference_key": "language",
            "preference_value": "python",
        },
        "source": {"kind": "human", "ref": "chat:docs"},
        "created_at": "2026-01-01T00:00:00Z",
        "backend_ref": {"tenant_id": "tenant_docs"},
        "extensions": {},
    }
    validate_against_schema(memory, "memory-object.schema.json")


def test_openapi_operation_components_reference_published_schemas():
    openapi = _load_openapi()
    components = openapi["components"]["schemas"]
    expected_refs = {
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
    for name, ref in expected_refs.items():
        assert components[name]["$ref"] == ref


def test_openapi_error_code_refs_align_with_schema():
    openapi = _load_openapi()
    components = openapi["components"]["schemas"]
    assert components["ErrorObject"]["properties"]["code"]["$ref"] == "../schemas/error-code.schema.json"
    assert components["PartialFailure"]["$ref"] == "../schemas/partial-failure.schema.json"


def test_validate_openapi_script_succeeds():
    result = subprocess.run(
        [sys.executable, "scripts/validate_openapi.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_check_contract_drift_script_succeeds():
    result = subprocess.run(
        [sys.executable, "scripts/check_contract_drift.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_lineage_link_valid():
    lineage = {
        "link_id": "lnk_1",
        "relation": "derived_from",
        "source_memory_id": "mem_a",
        "target_memory_id": "mem_b",
        "created_at": "2026-03-17T12:00:00Z",
        "metadata": {},
    }
    validate_against_schema(lineage, "lineage-link.schema.json")


def test_lineage_link_invalid_relation():
    lineage = {
        "link_id": "lnk_1",
        "relation": "invalid_relation",
        "source_memory_id": "mem_a",
        "target_memory_id": "mem_b",
        "created_at": "2026-03-17T12:00:00Z",
    }
    with pytest.raises(GatewayValidationError):
        validate_against_schema(lineage, "lineage-link.schema.json")
