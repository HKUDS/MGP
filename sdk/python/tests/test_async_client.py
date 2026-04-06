from __future__ import annotations

import asyncio
import json

import httpx

from .conftest import mgp_ok


def test_async_search_memory(async_client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert request.url.path == "/mgp/search"
        assert payload["payload"]["query"] == "dark mode"
        return httpx.Response(200, json=mgp_ok({"results": [{"consumable_text": "dark mode"}]}))

    async def _run() -> None:
        client = async_client_factory(handler)
        response = await client.search_memory(
            {
                "actor_agent": "agent/test",
                "acting_for_subject": {"kind": "user", "id": "user_1"},
                "requested_action": "search",
            },
            {"query": "dark mode", "limit": 5},
        )
        assert response.data["results"][0]["consumable_text"] == "dark mode"
        await client.close()

    asyncio.run(_run())
