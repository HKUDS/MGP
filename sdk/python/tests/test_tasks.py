from __future__ import annotations

import httpx

from .conftest import mgp_ok


def test_wait_for_task_polls_until_completion(sync_client_factory):
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(
                200,
                json=mgp_ok({"task": {"task_id": "task_1", "status": "running"}}),
            )
        return httpx.Response(
            200,
            json=mgp_ok({"task": {"task_id": "task_1", "status": "completed", "result": {"written_count": 1}}}),
        )

    client = sync_client_factory(handler)
    task = client.wait_for_task("task_1", timeout_seconds=1.0, poll_interval_seconds=0.0)
    assert task["status"] == "completed"
    assert task["result"]["written_count"] == 1
