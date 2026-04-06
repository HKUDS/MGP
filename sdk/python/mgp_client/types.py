from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from .auth import AuthConfig, TLSConfig
from .models import ErrorObject, PolicyContext
from .retry import RetryConfig

ResponseDataT = TypeVar("ResponseDataT")


@dataclass
class MGPResponse(Generic[ResponseDataT]):
    request_id: str
    status: str
    data: ResponseDataT | None
    error: ErrorObject | None = None


@dataclass
class AuditQuery:
    action: str | None = None
    target_memory_id: str | None = None
    actor_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    limit: int = 50
    pagination_token: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"limit": self.limit}
        if self.action is not None:
            payload["action"] = self.action
        if self.target_memory_id is not None:
            payload["target_memory_id"] = self.target_memory_id
        if self.actor_id is not None:
            payload["actor_id"] = self.actor_id
        if self.request_id is not None:
            payload["request_id"] = self.request_id
        if self.correlation_id is not None:
            payload["correlation_id"] = self.correlation_id
        if self.pagination_token is not None:
            payload["pagination_token"] = self.pagination_token
        return payload


@dataclass
class SearchQuery:
    query: str | None = None
    query_text: str | None = None
    intent_type: str | None = None
    keywords: list[str] | None = None
    target_memory_types: list[str] | None = None
    subject: dict[str, Any] | None = None
    scope: str | None = None
    types: list[str] | None = None
    time_scope: dict[str, Any] | None = None
    limit: int = 10
    top_k: int | None = None
    pagination_token: str | None = None
    timeout_ms: int | None = None

    def to_payload(self) -> dict[str, Any]:
        query_text = self.query_text or self.query or ""
        target_types = self.target_memory_types or self.types
        top_k = self.top_k or self.limit
        payload: dict[str, Any] = {
            "query": query_text,
            "limit": top_k,
        }
        if self.subject is not None:
            payload["subject"] = self.subject
        if self.scope is not None:
            payload["scope"] = self.scope
        if target_types is not None:
            payload["types"] = target_types
        if self.pagination_token is not None:
            payload["pagination_token"] = self.pagination_token
        if self.timeout_ms is not None:
            payload["timeout_ms"] = self.timeout_ms

        intent: dict[str, Any] = {
            "query_text": query_text,
            "intent_type": self.intent_type or "free_text",
            "top_k": top_k,
        }
        if self.keywords:
            intent["keywords"] = self.keywords
        if target_types is not None:
            intent["target_memory_types"] = target_types
        if self.subject is not None:
            intent["subject"] = self.subject
        if self.scope is not None:
            intent["scope"] = self.scope
        if self.time_scope is not None:
            intent["time_scope"] = self.time_scope
        if self.pagination_token is not None:
            intent["pagination_token"] = self.pagination_token
        if self.timeout_ms is not None:
            intent["timeout_ms"] = self.timeout_ms
        payload["intent"] = intent
        return payload


@dataclass
class MemoryCandidate:
    candidate_kind: str
    subject: dict[str, Any]
    scope: str
    proposed_type: str
    statement: str
    source: dict[str, Any]
    content: dict[str, Any] = field(default_factory=dict)
    source_evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: float | None = None
    sensitivity: str | None = None
    retention_policy: str | None = None
    ttl_seconds: int | None = None
    merge_hint: dict[str, Any] | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "candidate_kind": self.candidate_kind,
            "subject": self.subject,
            "scope": self.scope,
            "proposed_type": self.proposed_type,
            "statement": self.statement,
            "source": self.source,
            "content": self.content,
            "source_evidence": self.source_evidence,
            "extensions": self.extensions,
        }
        if self.confidence is not None:
            payload["confidence"] = self.confidence
        if self.sensitivity is not None:
            payload["sensitivity"] = self.sensitivity
        if self.retention_policy is not None:
            payload["retention_policy"] = self.retention_policy
        if self.ttl_seconds is not None:
            payload["ttl_seconds"] = self.ttl_seconds
        if self.merge_hint is not None:
            payload["merge_hint"] = self.merge_hint
        return payload


@dataclass
class ClientOptions:
    base_url: str
    timeout: float = 10.0
    headers: dict[str, str] = field(default_factory=dict)
    auth: AuthConfig | None = None
    tls: TLSConfig | None = None
    retry: RetryConfig = field(default_factory=RetryConfig)


__all__ = [
    "AuditQuery",
    "ClientOptions",
    "MGPResponse",
    "MemoryCandidate",
    "PolicyContext",
    "ResponseDataT",
    "SearchQuery",
]
