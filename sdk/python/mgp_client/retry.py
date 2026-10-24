from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

import httpx

_RETRY_SAFE_GET_PATHS = frozenset({"/mgp/capabilities"})
_RETRY_SAFE_POST_PATHS = frozenset(
    {
        "/mgp/initialize",
        "/mgp/search",
        "/mgp/get",
        "/mgp/update",
        "/mgp/expire",
        "/mgp/revoke",
        "/mgp/delete",
        "/mgp/purge",
        "/mgp/audit/query",
        "/mgp/tasks/get",
    }
)


def is_retry_safe(method: str, path: str) -> bool:
    normalized_method = method.upper()
    return (normalized_method == "GET" and path in _RETRY_SAFE_GET_PATHS) or (
        normalized_method == "POST" and path in _RETRY_SAFE_POST_PATHS
    )


@dataclass
class RetryConfig:
    max_attempts: int = 1
    backoff_seconds: float = 0.25
    retry_status_codes: set[int] = field(default_factory=lambda: {429, 500, 502, 503, 504})
    retry_on_request_errors: bool = True
    # Opt in only when the caller has established duplicate-safety for the operation.
    retry_non_idempotent: bool = False

    def normalized_attempts(self) -> int:
        return max(self.max_attempts, 1)


def should_retry_response(response: httpx.Response, config: RetryConfig, attempt: int) -> bool:
    return attempt < config.normalized_attempts() and response.status_code in config.retry_status_codes


def should_retry_exception(error: Exception, config: RetryConfig, attempt: int) -> bool:
    return (
        config.retry_on_request_errors
        and attempt < config.normalized_attempts()
        and isinstance(error, httpx.RequestError)
    )


def backoff_sleep(config: RetryConfig, attempt: int) -> None:
    time.sleep(config.backoff_seconds * attempt)


async def async_backoff_sleep(config: RetryConfig, attempt: int) -> None:
    await asyncio.sleep(config.backoff_seconds * attempt)
