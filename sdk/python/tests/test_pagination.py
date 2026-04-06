from __future__ import annotations

import json

import httpx

from .conftest import mgp_ok


def test_iter_search_results_consumes_next_token(sync_client_factory):
    requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        requests.append(payload)
        token = payload["payload"].get("pagination_token")
        if token == "page_2":
            return httpx.Response(
                200,
                json=mgp_ok({"results": [{"memory": {"memory_id": "mem_2"}}]}),
            )
        return httpx.Response(
            200,
            json=mgp_ok({"results": [{"memory": {"memory_id": "mem_1"}}], "next_token": "page_2"}),
        )

    client = sync_client_factory(handler)
    items = list(
        client.iter_search_results(
            {
                "actor_agent": "agent/test",
                "acting_for_subject": {"kind": "user", "id": "user_1"},
                "requested_action": "search",
            },
            {"query": "theme"},
        )
    )

    assert [item["memory"]["memory_id"] for item in items] == ["mem_1", "mem_2"]
    assert requests[0]["payload"].get("pagination_token") is None
    assert requests[1]["payload"]["pagination_token"] == "page_2"
