from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, cast

from .errors import MGPError, raise_for_error
from .models import AsyncTask

if TYPE_CHECKING:
    from .async_client import AsyncMGPClient
    from .client import MGPClient


TERMINAL_TASK_STATES = {"completed", "failed", "cancelled"}


def _raise_task_error(task: AsyncTask) -> None:
    error = cast(dict[str, Any] | None, task.get("error"))
    if error:
        raise_for_error(error)
    raise MGPError(
        code="MGP_BACKEND_ERROR",
        message=f"task ended in state {task.get('status', 'unknown')}",
        details={"task_id": task.get("task_id"), "status": task.get("status")},
    )


def wait_for_task_completion(
    client: "MGPClient",
    task_id: str,
    *,
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.5,
) -> AsyncTask:
    deadline = time.monotonic() + timeout_seconds
    while True:
        task = client.get_task(task_id)
        status = task.get("status")
        if status == "completed":
            return task
        if status in TERMINAL_TASK_STATES:
            _raise_task_error(task)
        if time.monotonic() >= deadline:
            raise TimeoutError(f"timed out waiting for task {task_id}")
        time.sleep(poll_interval_seconds)


async def wait_for_task_completion_async(
    client: "AsyncMGPClient",
    task_id: str,
    *,
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.5,
) -> AsyncTask:
    deadline = time.monotonic() + timeout_seconds
    while True:
        task = await client.get_task(task_id)
        status = task.get("status")
        if status == "completed":
            return task
        if status in TERMINAL_TASK_STATES:
            _raise_task_error(task)
        if time.monotonic() >= deadline:
            raise TimeoutError(f"timed out waiting for task {task_id}")
        await asyncio.sleep(poll_interval_seconds)
