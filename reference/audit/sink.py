from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class AuditSink:
    def __init__(self, file_path: str | None = None) -> None:
        configured_path = file_path or os.getenv("MGP_AUDIT_LOG")
        self._path = Path(configured_path or Path(__file__).with_name("audit.jsonl"))
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, event: dict[str, Any]) -> None:
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def query(
        self,
        *,
        action: str | None = None,
        target_memory_id: str | None = None,
        actor_id: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
        pagination_token: str | None = None,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], str | None]:
        events = self._read_all()

        filtered: list[dict[str, Any]] = []
        for event in events:
            if action and event.get("action") != action:
                continue
            if target_memory_id and event.get("target_memory_id") != target_memory_id:
                continue
            if actor_id and event.get("actor", {}).get("id") != actor_id:
                continue
            if request_id and event.get("request_id") != request_id:
                continue
            if correlation_id and event.get("correlation_id") != correlation_id:
                continue
            filtered.append(event)

        offset = int(pagination_token or 0)
        page = filtered[offset : offset + limit]
        next_token = str(offset + limit) if offset + limit < len(filtered) else None
        return page, next_token

    def _read_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []

        events: list[dict[str, Any]] = []
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))
        return events
