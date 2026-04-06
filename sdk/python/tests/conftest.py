from __future__ import annotations

from typing import Any

import httpx
import pytest
from mgp_client import AsyncMGPClient, MGPClient


def mgp_ok(data: dict[str, Any] | None = None, request_id: str = "req_test") -> dict[str, Any]:
    return {
        "request_id": request_id,
        "status": "ok",
        "error": None,
        "data": data or {},
    }


def mgp_error(code: str, message: str = "failure", request_id: str = "req_test") -> dict[str, Any]:
    return {
        "request_id": request_id,
        "status": "error",
        "error": {
            "code": code,
            "message": message,
            "details": {},
        },
        "data": None,
    }


@pytest.fixture
def sync_client_factory():
    def factory(handler):
        transport = httpx.MockTransport(handler)
        return MGPClient("http://testserver", transport=transport)

    return factory


@pytest.fixture
def async_client_factory():
    def factory(handler):
        transport = httpx.MockTransport(handler)
        return AsyncMGPClient("http://testserver", transport=transport)

    return factory
