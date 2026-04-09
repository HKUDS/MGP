from __future__ import annotations

import logging
from typing import Any, Protocol


class SidecarTelemetry(Protocol):
    def emit(self, event: str, **fields: Any) -> None: ...


class NullTelemetry:
    def emit(self, event: str, **fields: Any) -> None:
        return None


class LoggingTelemetry:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("mgp.nanobot.sidecar")

    def emit(self, event: str, **fields: Any) -> None:
        payload = {"event": event, **fields}
        self.logger.info("nanobot_sidecar", extra={"payload": payload})
