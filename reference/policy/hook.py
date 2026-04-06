from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from typing import Any


class PolicyHook:
    """Minimal policy hook for the MGP reference implementation."""

    def evaluate(
        self,
        policy_context: dict[str, Any],
        memory: dict[str, Any] | None = None,
        action: str | None = None,
    ) -> dict[str, Any]:
        action_name = action or policy_context.get("requested_action", "read")

        if memory and self._tenant_mismatch(policy_context, memory):
            return {
                "decision": "deny",
                "reason_code": "tenant_mismatch",
                "applied_rules": ["tenant_mismatch_deny"],
                "return_mode": "metadata_only",
            }

        if memory and memory.get("backend_ref", {}).get("mgp_state") == "deleted":
            if action_name in {"search", "update"}:
                return {
                    "decision": "deny",
                    "reason_code": "soft_deleted",
                    "applied_rules": ["soft_delete_deny"],
                    "return_mode": "metadata_only",
                }
            if action_name == "read":
                return {
                    "decision": "redact",
                    "reason_code": "soft_deleted",
                    "applied_rules": ["soft_delete_metadata_only"],
                    "return_mode": "metadata_only",
                }

        if memory and action_name in {"read", "search", "update"} and self.is_expired(memory):
            return {
                "decision": "deny",
                "reason_code": "ttl_expired",
                "applied_rules": ["ttl_expiration_deny"],
                "return_mode": "metadata_only",
            }

        sensitivity = memory.get("sensitivity") if memory else None
        if sensitivity == "restricted":
            return {
                "decision": "redact",
                "reason_code": "restricted_sensitivity",
                "applied_rules": ["sensitivity_to_metadata_only"],
                "return_mode": "metadata_only",
            }

        if sensitivity == "confidential":
            return {
                "decision": "redact",
                "reason_code": "confidential_sensitivity",
                "applied_rules": ["sensitivity_to_masked"],
                "return_mode": "masked",
            }

        return {
            "decision": "allow",
            "reason_code": "allowed",
            "applied_rules": [],
            "return_mode": "raw",
        }

    def transform_memory(
        self,
        memory: dict[str, Any],
        decision: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        mode = decision["return_mode"]
        transformed = copy.deepcopy(memory)

        if mode == "raw":
            return transformed, {"policy_view": "raw"}

        if mode == "metadata_only":
            safe_text = f"{transformed.get('type', 'memory')} metadata only"
            transformed["content"] = {
                "statement": safe_text,
                "summary": safe_text,
            }
            transformed["extensions"] = {}
            transformed["evidence"] = []
            transformed["evidence_refs"] = []
            transformed.setdefault("backend_ref", {})["policy_view"] = "metadata_only"
            return (
                transformed,
                {
                    "policy_view": "metadata_only",
                    "reason_code": decision["reason_code"],
                    "masked_fields": ["content", "extensions", "evidence", "evidence_refs"],
                    "transformed_fields": ["content", "extensions", "evidence", "evidence_refs"],
                    "explanation": "Returned only metadata because policy denied semantic content access.",
                },
            )

        if mode == "masked":
            transformed["content"] = self._mask_value(transformed.get("content", {}))
            transformed.setdefault("backend_ref", {})["policy_view"] = "masked"
            return (
                transformed,
                {
                    "policy_view": "masked",
                    "reason_code": decision["reason_code"],
                    "masked_fields": ["content"],
                    "transformed_fields": ["content"],
                    "explanation": "Masked sensitive content according to policy.",
                },
            )

        if mode == "summary":
            safe_summary = self._summary_text(transformed)
            transformed["content"] = {
                "statement": safe_summary,
                "summary": safe_summary,
            }
            return transformed, {
                "policy_view": "summary",
                "reason_code": decision["reason_code"],
                "summary_generated": True,
                "transformed_fields": ["content"],
                "explanation": "Returned a summarized memory view according to policy.",
            }

        return transformed, None

    def _summary_text(self, memory: dict[str, Any]) -> str:
        content = memory.get("content", {})
        if isinstance(content, dict):
            for key in ("summary", "statement", "preference", "fact"):
                value = content.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return f"{memory.get('type', 'memory')} summary"

    def is_expired(self, memory: dict[str, Any]) -> bool:
        ttl_seconds = memory.get("ttl_seconds")
        created_at = memory.get("created_at")
        if not ttl_seconds or not created_at:
            return False

        created = self._parse_datetime(created_at)
        if not created:
            return False

        expires_at = created + timedelta(seconds=int(ttl_seconds))
        return datetime.now(timezone.utc) >= expires_at

    def _tenant_mismatch(self, policy_context: dict[str, Any], memory: dict[str, Any]) -> bool:
        requested_tenant = policy_context.get("tenant_id")
        if not requested_tenant:
            return False

        backend_ref = memory.get("backend_ref", {})
        extension_tenant = memory.get("extensions", {}).get("mgp:tenant_id")
        memory_tenant = backend_ref.get("tenant_id") or extension_tenant
        if not memory_tenant:
            return False

        return requested_tenant != memory_tenant

    def _mask_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._mask_value(inner) for key, inner in value.items()}
        if isinstance(value, list):
            return [self._mask_value(item) for item in value]
        if isinstance(value, str):
            return "***"
        return value

    def _parse_datetime(self, value: str) -> datetime | None:
        try:
            normalized = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
