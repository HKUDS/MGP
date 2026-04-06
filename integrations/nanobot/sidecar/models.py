from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

Mode = Literal["off", "shadow", "primary"]


def _first(mapping: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


@dataclass
class NanobotSidecarConfig:
    gateway_url: str
    mode: Mode = "shadow"
    timeout: float = 5.0
    fail_open: bool = True
    workspace_as_tenant: bool = True
    reuse_client: bool = True
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mode not in {"off", "shadow", "primary"}:
            raise ValueError("mode must be one of: off, shadow, primary")


@dataclass
class NanobotRuntimeState:
    actor_agent: str
    user_id: str
    session_key: str
    workspace_id: str
    channel: str
    chat_id: str | None = None
    subject_kind: str = "user"
    tenant_id: str | None = None
    task_type: str | None = None
    data_zone: str | None = None
    risk_level: str | None = None
    correlation_id: str | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "NanobotRuntimeState":
        return cls(
            actor_agent=_first(payload, "actor_agent", "actorAgent"),
            user_id=_first(payload, "user_id", "userId"),
            session_key=_first(payload, "session_key", "sessionKey"),
            workspace_id=_first(payload, "workspace_id", "workspaceId"),
            channel=_first(payload, "channel"),
            chat_id=_first(payload, "chat_id", "chatId"),
            subject_kind=_first(payload, "subject_kind", "subjectKind", default="user"),
            tenant_id=_first(payload, "tenant_id", "tenantId"),
            task_type=_first(payload, "task_type", "taskType"),
            data_zone=_first(payload, "data_zone", "dataZone"),
            risk_level=_first(payload, "risk_level", "riskLevel"),
            correlation_id=_first(payload, "correlation_id", "correlationId"),
        )


@dataclass
class RecallIntent:
    query: str
    limit: int = 5
    scope: str = "user"
    types: list[str] | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "RecallIntent":
        types = _first(payload, "types", default=None)
        return cls(
            query=str(_first(payload, "query")),
            limit=int(_first(payload, "limit", default=5)),
            scope=str(_first(payload, "scope", default="user")),
            types=list(types) if types is not None else None,
        )


@dataclass
class MemoryCandidate:
    content: dict[str, Any]
    memory_type: str = "semantic_fact"
    scope: str = "user"
    sensitivity: str = "internal"
    source_kind: str = "chat"
    source_ref: str | None = None
    memory_id: str | None = None
    created_at: str | None = None
    ttl_seconds: int | None = None
    retention_policy: str | None = None
    confidence: float | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "MemoryCandidate":
        return cls(
            content=dict(_first(payload, "content", default={})),
            memory_type=str(_first(payload, "memory_type", "type", default="semantic_fact")),
            scope=str(_first(payload, "scope", default="user")),
            sensitivity=str(_first(payload, "sensitivity", default="internal")),
            source_kind=str(_first(payload, "source_kind", "sourceKind", default="chat")),
            source_ref=_first(payload, "source_ref", "sourceRef"),
            memory_id=_first(payload, "memory_id", "memoryId"),
            created_at=_first(payload, "created_at", "createdAt"),
            ttl_seconds=_first(payload, "ttl_seconds", "ttlSeconds"),
            retention_policy=_first(payload, "retention_policy", "retentionPolicy"),
            confidence=_first(payload, "confidence"),
            extensions=dict(_first(payload, "extensions", default={})),
        )


@dataclass
class RecallItem:
    memory: dict[str, Any]
    score: float | None = None
    score_kind: str | None = None
    retrieval_mode: str | None = None
    return_mode: str = "raw"
    redaction_info: dict[str, Any] | None = None
    backend_origin: str | None = None
    consumable_text: str | None = None
    matched_terms: list[str] | None = None
    explanation: str | None = None


@dataclass
class RecallOutcome:
    mode: Mode
    executed: bool
    degraded: bool
    prompt_context: str
    results: list[RecallItem]
    request_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    fallback: str | None = None
    used_prompt: bool = False


@dataclass
class CommitOutcome:
    mode: Mode
    executed: bool
    written: bool
    memory_id: str | None = None
    request_id: str | None = None
    degraded: bool = False
    error_code: str | None = None
    error_message: str | None = None
    fallback: str | None = None
