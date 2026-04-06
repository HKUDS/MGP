from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SDK_PATH = ROOT / "sdk" / "python"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

_async_service = importlib.import_module(".async_service", __name__)
_mappers = importlib.import_module(".mappers", __name__)
_models = importlib.import_module(".models", __name__)
_service = importlib.import_module(".service", __name__)
_telemetry = importlib.import_module(".telemetry", __name__)

AsyncNanobotMGPSidecar = _async_service.AsyncNanobotMGPSidecar
build_memory_candidate = _mappers.build_memory_candidate
build_policy_context = _mappers.build_policy_context
build_search_query = _mappers.build_search_query
format_prompt_context = _mappers.format_prompt_context
CommitOutcome = _models.CommitOutcome
MemoryCandidate = _models.MemoryCandidate
NanobotRuntimeState = _models.NanobotRuntimeState
NanobotSidecarConfig = _models.NanobotSidecarConfig
RecallIntent = _models.RecallIntent
RecallItem = _models.RecallItem
RecallOutcome = _models.RecallOutcome
NanobotMGPSidecar = _service.NanobotMGPSidecar
LoggingTelemetry = _telemetry.LoggingTelemetry
NullTelemetry = _telemetry.NullTelemetry

__all__ = [
    "AsyncNanobotMGPSidecar",
    "CommitOutcome",
    "LoggingTelemetry",
    "MemoryCandidate",
    "NanobotMGPSidecar",
    "NanobotRuntimeState",
    "NanobotSidecarConfig",
    "NullTelemetry",
    "RecallIntent",
    "RecallItem",
    "RecallOutcome",
    "build_memory_candidate",
    "build_policy_context",
    "build_search_query",
    "format_prompt_context",
]
