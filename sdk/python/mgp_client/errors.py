from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MGPError(Exception):
    code: str
    message: str
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class InvalidObjectError(MGPError):
    pass


class UnsupportedCapabilityError(MGPError):
    pass


class UnsupportedVersionError(MGPError):
    pass


class PolicyDeniedError(MGPError):
    pass


class MemoryNotFoundError(MGPError):
    pass


class TaskNotFoundError(MGPError):
    pass


class ScopeViolationError(MGPError):
    pass


class ConflictUnresolvedError(MGPError):
    pass


class BackendError(MGPError):
    pass


ERROR_MAP = {
    "MGP_INVALID_OBJECT": InvalidObjectError,
    "MGP_UNSUPPORTED_VERSION": UnsupportedVersionError,
    "MGP_UNSUPPORTED_CAPABILITY": UnsupportedCapabilityError,
    "MGP_POLICY_DENIED": PolicyDeniedError,
    "MGP_MEMORY_NOT_FOUND": MemoryNotFoundError,
    "MGP_TASK_NOT_FOUND": TaskNotFoundError,
    "MGP_SCOPE_VIOLATION": ScopeViolationError,
    "MGP_CONFLICT_UNRESOLVED": ConflictUnresolvedError,
    "MGP_BACKEND_ERROR": BackendError,
}


def raise_for_error(error: dict[str, Any] | None) -> None:
    if not error:
        raise BackendError(code="MGP_BACKEND_ERROR", message="unknown MGP error", details={})
    code = error.get("code", "MGP_BACKEND_ERROR")
    message = error.get("message", "unknown MGP error")
    details = error.get("details")
    error_cls = ERROR_MAP.get(code, MGPError)
    raise error_cls(code=code, message=message, details=details)
