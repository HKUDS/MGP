from __future__ import annotations

import httpx
from mgp_client import MGPClient, RetryConfig

from .conftest import mgp_error, mgp_ok


def test_client_retries_retryable_status_codes():
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(502, json=mgp_error("MGP_BACKEND_ERROR", "temporary failure"))
        return httpx.Response(200, json=mgp_ok({"memory": {"memory_id": "mem_retry"}}))

    client = MGPClient(
        "http://testserver",
        retry=RetryConfig(max_attempts=2, backoff_seconds=0.0),
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
