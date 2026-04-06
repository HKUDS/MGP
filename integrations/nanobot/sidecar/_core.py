from __future__ import annotations

from typing import Any

from .mappers import format_prompt_context
from .models import CommitOutcome, Mode, NanobotRuntimeState, RecallItem, RecallOutcome

NATIVE_FALLBACK = "nanobot-native"


def build_off_recall_outcome(mode: Mode) -> RecallOutcome:
    return RecallOutcome(
        mode=mode,
        executed=False,
        degraded=False,
        prompt_context="",
        results=[],
        fallback=NATIVE_FALLBACK,
    )


def build_recall_success_outcome(mode: Mode, items: list[RecallItem], request_id: str | None) -> RecallOutcome:
    prompt_context = format_prompt_context(items) if mode == "primary" else ""
    return RecallOutcome(
        mode=mode,
        executed=True,
        degraded=False,
        prompt_context=prompt_context,
        results=items,
        request_id=request_id,
        used_prompt=bool(prompt_context),
    )


def build_recall_failure_outcome(mode: Mode, error: Exception) -> RecallOutcome:
    return RecallOutcome(
        mode=mode,
        executed=False,
        degraded=True,
        prompt_context="",
        results=[],
        error_code=getattr(error, "code", "MGP_BACKEND_ERROR"),
        error_message=str(error),
        fallback=NATIVE_FALLBACK,
    )


def build_off_commit_outcome(mode: Mode, memory_id: str | None) -> CommitOutcome:
    return CommitOutcome(
        mode=mode,
        executed=False,
        written=False,
        memory_id=memory_id,
        fallback=NATIVE_FALLBACK,
    )


def build_commit_success_outcome(
    mode: Mode,
    *,
    returned_memory: dict[str, Any],
    request_id: str | None,
) -> CommitOutcome:
    return CommitOutcome(
        mode=mode,
        executed=True,
        written=True,
        memory_id=returned_memory.get("memory_id"),
        request_id=request_id,
    )


def build_commit_failure_outcome(mode: Mode, memory_id: str | None, error: Exception) -> CommitOutcome:
    return CommitOutcome(
        mode=mode,
        executed=False,
        written=False,
        memory_id=memory_id,
        degraded=True,
        error_code=getattr(error, "code", "MGP_BACKEND_ERROR"),
        error_message=str(error),
        fallback=NATIVE_FALLBACK,
    )


def recall_started_fields(mode: Mode, runtime: NanobotRuntimeState) -> dict[str, Any]:
    return {
        "mode": mode,
        "session_key": runtime.session_key,
    }


def recall_completed_fields(mode: Mode, outcome: RecallOutcome) -> dict[str, Any]:
    return {
        "mode": mode,
        "request_id": outcome.request_id,
        "result_count": len(outcome.results),
        "used_prompt": outcome.used_prompt,
    }


def recall_failed_fields(mode: Mode, outcome: RecallOutcome, *, fail_open: bool) -> dict[str, Any]:
    return {
        "mode": mode,
        "error_code": outcome.error_code,
        "error_message": outcome.error_message,
        "fail_open": fail_open,
    }


def commit_started_fields(mode: Mode, runtime: NanobotRuntimeState, memory_id: str | None) -> dict[str, Any]:
    return {
        "mode": mode,
        "session_key": runtime.session_key,
        "memory_id": memory_id,
    }


def commit_completed_fields(mode: Mode, outcome: CommitOutcome) -> dict[str, Any]:
    return {
        "mode": mode,
        "request_id": outcome.request_id,
        "memory_id": outcome.memory_id,
    }


def commit_failed_fields(mode: Mode, outcome: CommitOutcome, *, fail_open: bool) -> dict[str, Any]:
    return {
        "mode": mode,
        "error_code": outcome.error_code,
        "error_message": outcome.error_message,
        "fail_open": fail_open,
    }
