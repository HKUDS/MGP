from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from mgp_client import AsyncMGPClient, MGPClient, RetryConfig
from mgp_client.errors import BackendError
from mgp_client.retry import is_retry_safe

from .conftest import mgp_error, mgp_ok


@pytest.mark.parametrize(
    ("method", "path", "expected"),
    [
        ("GET", "/mgp/capabilities", True),
        ("GET", "/mgp/future-write", False),
        ("POST", "/mgp/update", True),
        ("POST", "/mgp/write", False),
        ("POST", "/mgp/export", False),
    ],
)
def test_retry_safety_is_limited_to_known_operations(method: str, path: str, expected: bool):
    assert is_retry_safe(method, path) is expected


def test_client_retries_retryable_status_codes_for_safe_operation():
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(502, json=mgp_error("MGP_BACKEND_ERROR", "temporary failure"))
        return httpx.Response(200, json=mgp_ok({"results": []}))

    client = MGPClient(
        "http://testserver",
        retry=RetryConfig(max_attempts=2, backoff_seconds=0.0),
        transport=httpx.MockTransport(handler),
    )
    response = client.search_memory(
        {
            "actor_agent": "agent/test",
            "acting_for_subject": {"kind": "user", "id": "user_1"},
            "requested_action": "search",
        },
        {"query": "dark mode"},
    )

    assert attempts["count"] == 2
    assert response.data["results"] == []
    client.close()


def test_client_does_not_retry_write_after_ambiguous_request_error():
    attempts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        attempts.append(body["request_id"])
        raise httpx.ReadTimeout("synthetic response loss after possible commit")

    client = MGPClient(
        "http://testserver",
        retry=RetryConfig(max_attempts=2, backoff_seconds=0.0),
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(BackendError):
        client.write_memory(
            {
                "actor_agent": "agent/test",
                "acting_for_subject": {"kind": "user", "id": "user_1"},
                "requested_action": "write",
            },
            {"memory_id": "mem_ambiguous"},
        )

    assert len(attempts) == 1
    client.close()


def test_client_retries_write_when_duplicate_safety_is_explicitly_enabled():
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(502, json=mgp_error("MGP_BACKEND_ERROR", "temporary failure"))
        return httpx.Response(200, json=mgp_ok({"memory": {"memory_id": "mem_retry"}}))

    client = MGPClient(
        "http://testserver",
        retry=RetryConfig(max_attempts=2, backoff_seconds=0.0, retry_non_idempotent=True),
        transport=httpx.MockTransport(handler),
    )
    response = client.write_memory(
        {
            "actor_agent": "agent/test",
            "acting_for_subject": {"kind": "user", "id": "user_1"},
            "requested_action": "write",
        },
        {"memory_id": "mem_retry"},
    )

    assert attempts["count"] == 2
    assert response.data["memory"]["memory_id"] == "mem_retry"
    client.close()


def test_async_client_retries_retryable_status_codes_for_safe_operation():
    async def run() -> None:
        attempts = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["count"] += 1
            if attempts["count"] == 1:
                return httpx.Response(503, json=mgp_error("MGP_BACKEND_ERROR", "temporary failure"))
            return httpx.Response(200, json=mgp_ok({"results": []}))

        client = AsyncMGPClient(
            "http://testserver",
            retry=RetryConfig(max_attempts=2, backoff_seconds=0.0),
            transport=httpx.MockTransport(handler),
        )
        response = await client.search_memory(
            {
                "actor_agent": "agent/test",
                "acting_for_subject": {"kind": "user", "id": "user_1"},
                "requested_action": "search",
            },
            {"query": "dark mode"},
        )

        assert attempts["count"] == 2
        assert response.data["results"] == []
        await client.close()

    asyncio.run(run())


def test_async_client_does_not_retry_write_after_ambiguous_request_error():
    async def run() -> None:
        attempts: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            attempts.append(body["request_id"])
            raise httpx.ReadTimeout("synthetic response loss after possible commit")

        client = AsyncMGPClient(
            "http://testserver",
            retry=RetryConfig(max_attempts=2, backoff_seconds=0.0),
            transport=httpx.MockTransport(handler),
        )
        with pytest.raises(BackendError):
            await client.write_memory(
                {
                    "actor_agent": "agent/test",
                    "acting_for_subject": {"kind": "user", "id": "user_1"},
                    "requested_action": "write",
                },
                {"memory_id": "mem_ambiguous"},
            )

        assert len(attempts) == 1
        await client.close()

    asyncio.run(run())
