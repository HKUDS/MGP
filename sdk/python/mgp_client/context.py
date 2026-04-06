from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from .models import PolicyContext


@dataclass
class PolicyContextBuilder:
    actor_agent: str
    subject_kind: str = "user"
    subject_id: str = "unknown"
    tenant_id: str | None = None
    data_zone: str | None = None
    task_id: str | None = None
    session_id: str | None = None
    task_type: str | None = None
    risk_level: str | None = None
    channel: str | None = None
    chat_id: str | None = None
    runtime_id: str | None = None
    runtime_instance_id: str | None = None
    correlation_id: str | None = None
    consent_basis: str | None = None
    assertion_origin: str | None = None

    def build(self, requested_action: str, **overrides: Any) -> PolicyContext:
        context: dict[str, Any] = {
            "actor_agent": self.actor_agent,
            "acting_for_subject": {
                "kind": self.subject_kind,
                "id": self.subject_id,
            },
            "requested_action": requested_action,
        }

        optional_fields = {
            "tenant_id": self.tenant_id,
            "data_zone": self.data_zone,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "task_type": self.task_type,
            "risk_level": self.risk_level,
            "channel": self.channel,
            "chat_id": self.chat_id,
            "runtime_id": self.runtime_id,
            "runtime_instance_id": self.runtime_instance_id,
            "correlation_id": self.correlation_id,
            "consent_basis": self.consent_basis,
            "assertion_origin": self.assertion_origin,
        }
        for key, value in optional_fields.items():
            if value is not None:
                context[key] = value

        for key, value in overrides.items():
            if value is not None:
                context[key] = value

        return cast(PolicyContext, context)
