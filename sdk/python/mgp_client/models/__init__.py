from __future__ import annotations

from typing import Any, TypedDict


class SubjectRef(TypedDict):
    kind: str
    id: str


class SourceRef(TypedDict, total=False):
    kind: str
    ref: str


class BackendRef(TypedDict, total=False):
    adapter: str
    mgp_state: str
    tenant_id: str


class ErrorObject(TypedDict, total=False):
    code: str
    message: str
    details: dict[str, Any]


class AsyncTask(TypedDict, total=False):
    task_id: str
    operation: str
    status: str
    request_id: str
    created_at: str
    updated_at: str
    progress: float
    total: float
    message: str
    result: dict[str, Any] | None
    error: ErrorObject | None


class MemoryObject(TypedDict, total=False):
    memory_id: str
    subject: SubjectRef
    scope: str
    type: str
    content: dict[str, Any]
    source: SourceRef
    sensitivity: str
    ttl_seconds: int
    created_at: str
    updated_at: str
    backend_ref: BackendRef
    extensions: dict[str, Any]


class PolicyContext(TypedDict, total=False):
    actor_agent: str
    acting_for_subject: SubjectRef
    requested_action: str
    tenant_id: str
    data_zone: str
    task_id: str
    session_id: str
    task_type: str
    risk_level: str
    channel: str
    chat_id: str
    runtime_id: str
    runtime_instance_id: str
    correlation_id: str
    consent_basis: str
    assertion_origin: str


class SearchResultItem(TypedDict, total=False):
    memory: MemoryObject
    backend_origin: str
    score: float
    score_kind: str
    retrieval_mode: str
    matched_terms: list[str]
    explanation: str
    consumable_text: str
    return_mode: str
    redaction_info: dict[str, Any] | None


class AuditEvent(TypedDict, total=False):
    event_id: str
    timestamp: str
    request_id: str
    actor: SubjectRef
    action: str
    target_memory_id: str
    correlation_id: str
    policy_context: PolicyContext
    decision: dict[str, Any]
    backend: str
    lineage_refs: list[str]


class WriteResponseData(TypedDict, total=False):
    memory: MemoryObject
    return_mode: str
    redaction_info: dict[str, Any] | None
    consumable_text: str
    resolution: dict[str, Any] | None


class GetResponseData(TypedDict, total=False):
    memory: MemoryObject
    return_mode: str
    redaction_info: dict[str, Any] | None
    consumable_text: str


class SearchResponseData(TypedDict, total=False):
    results: list[SearchResultItem]
    effective_intent: dict[str, Any]
    next_token: str


class LifecycleResponseData(TypedDict, total=False):
    memory_id: str
    state: str
    purged_at: str
    reason: str | None


class BatchWriteItem(TypedDict, total=False):
    status: str
    memory: MemoryObject
    return_mode: str
    redaction_info: dict[str, Any] | None
    consumable_text: str
    resolution: dict[str, Any] | None
    error: ErrorObject


class BatchWriteResponseData(TypedDict, total=False):
    results: list[BatchWriteItem]


class TransferResponseData(TypedDict, total=False):
    task: AsyncTask
    memories: list[MemoryObject]
    memory_ids: list[str]
    written_count: int
    next_token: str
    cursor: str


class AuditQueryResponseData(TypedDict, total=False):
    events: list[AuditEvent]
    next_token: str


class CapabilitiesResponseData(TypedDict):
    manifest: dict[str, Any]
    protocol_capabilities: dict[str, Any]


class InitializeResponseData(TypedDict, total=False):
    chosen_version: str
    supported_versions: list[str]
    minimum_supported_version: str
    lifecycle_phase: str
    session_mode: str
    transport_profile: str
    protocol_capabilities: dict[str, Any]
    negotiated_capabilities: dict[str, Any]
    negotiated_profiles: list[str]
    server_info: dict[str, Any]
    discovery: dict[str, Any]
    deprecation_warnings: list[str]
