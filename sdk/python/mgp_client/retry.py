from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

import httpx


@dataclass
class RetryConfig:
    max_attempts: int = 1
    backoff_seconds: float = 0.25
    retry_status_codes: set[int] = field(default_factory=lambda: {429, 500, 502, 503, 504})
    retry_on_request_errors: bool = True

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
