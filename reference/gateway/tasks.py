from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable
from uuid import uuid4

from gateway.time_utils import utc_now_iso


def error_payload(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": details or {},
    }


class TaskStore:
    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}

    def create(self, *, operation: str, request_id: str, runner: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        task_id = f"task_{uuid4().hex}"
        now = utc_now_iso()
        task = {
            "task_id": task_id,
            "operation": operation,
            "status": "pending",
            "request_id": request_id,
            "created_at": now,
            "updated_at": now,
            "progress": 0.0,
            "total": 1.0,
            "message": "accepted",
            "result": None,
            "error": None,
        }
        self._tasks[task_id] = {
            "task": task,
            "runner": runner,
        }
        return deepcopy(task)

    def get(self, task_id: str) -> dict[str, Any] | None:
        record = self._tasks.get(task_id)
        if record is None:
            return None

        task = record["task"]
        if task["status"] in {"pending", "running"}:
            self._advance(record)
        return deepcopy(record["task"])

    def cancel(self, task_id: str, reason: str | None = None) -> dict[str, Any] | None:
        record = self._tasks.get(task_id)
        if record is None:
            return None

        task = record["task"]
        if task["status"] in {"completed", "failed", "cancelled"}:
            return deepcopy(task)

        task["status"] = "cancelled"
        task["updated_at"] = utc_now_iso()
        task["message"] = reason or "cancelled"
        return deepcopy(task)

    def _advance(self, record: dict[str, Any]) -> None:
        task = record["task"]
        if task["status"] == "cancelled":
            return

        task["status"] = "running"
        task["progress"] = 0.5
        task["updated_at"] = utc_now_iso()
        task["message"] = "running"

        try:
            result = record["runner"]()
            task["status"] = "completed"
            task["progress"] = 1.0
            task["updated_at"] = utc_now_iso()
            task["message"] = "completed"
            task["result"] = result
            task["error"] = None
        except Exception as error:  # pragma: no cover - defensive path
            task["status"] = "failed"
            task["progress"] = 1.0
            task["updated_at"] = utc_now_iso()
            task["message"] = "failed"
            task["result"] = None
            task["error"] = error_payload("MGP_BACKEND_ERROR", str(error))
