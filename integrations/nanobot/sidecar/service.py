from __future__ import annotations

from typing import Any, Callable, Protocol

import httpx
from mgp_client import MGPClient
from mgp_client.errors import MGPError
from mgp_client.models import PolicyContext

from ._core import (
    build_commit_failure_outcome,
    build_commit_success_outcome,
    build_off_commit_outcome,
    build_off_recall_outcome,
    build_recall_failure_outcome,
    build_recall_success_outcome,
    commit_completed_fields,
    commit_failed_fields,
    commit_started_fields,
    recall_completed_fields,
    recall_failed_fields,
    recall_started_fields,
)
from .mappers import (
    build_memory_candidate,
    build_policy_context,
    build_search_query,
    normalize_search_results,
)
from .models import (
    CommitOutcome,
    MemoryCandidate,
    NanobotRuntimeState,
    NanobotSidecarConfig,
    RecallIntent,
    RecallOutcome,
)
from .telemetry import LoggingTelemetry, SidecarTelemetry


class SupportsMGPClient(Protocol):
    def search_memory(
        self,
        policy_context: PolicyContext | dict[str, Any],
        search: Any,
        request_id: str | None = None,
    ) -> Any:
        ...

    def write_memory(
        self,
        policy_context: PolicyContext | dict[str, Any],
        memory: dict[str, Any],
        request_id: str | None = None,
    ) -> Any:
        ...

    def write_candidate(
        self,
        policy_context: PolicyContext | dict[str, Any],
        candidate: Any,
        *,
        merge_hint: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> Any:
        ...

    def close(self) -> None:
        ...


ClientFactory = Callable[[str, float, dict[str, str]], SupportsMGPClient]


def _default_client_factory(base_url: str, timeout: float, headers: dict[str, str]) -> SupportsMGPClient:
    return MGPClient(base_url, timeout=timeout, headers=headers)


class NanobotMGPSidecar:
    def __init__(
        self,
        config: NanobotSidecarConfig,
        *,
        client_factory: ClientFactory | None = None,
        telemetry: SidecarTelemetry | None = None,
    ) -> None:
        self.config = config
        self._client_factory = client_factory or _default_client_factory
        self._telemetry = telemetry or LoggingTelemetry()
        self._shared_client: SupportsMGPClient | None = None

    def recall(self, runtime: NanobotRuntimeState, intent: RecallIntent) -> RecallOutcome:
        if self.config.mode == "off":
            return build_off_recall_outcome(self.config.mode)

        self._telemetry.emit("recall_started", **recall_started_fields(self.config.mode, runtime))
        client = self._get_client()
        try:
            policy_context = build_policy_context(
                runtime,
                "search",
                workspace_as_tenant=self.config.workspace_as_tenant,
            )
            search_query = build_search_query(runtime, intent)
            response = client.search_memory(policy_context, search_query)
            items = normalize_search_results(response.data)
            outcome = build_recall_success_outcome(self.config.mode, items, response.request_id)
            self._telemetry.emit("recall_completed", **recall_completed_fields(self.config.mode, outcome))
            return outcome
        except (MGPError, httpx.HTTPError, ValueError) as error:
            if not self.config.fail_open:
                raise
            outcome = build_recall_failure_outcome(self.config.mode, error)
            self._telemetry.emit(
                "recall_failed",
                **recall_failed_fields(self.config.mode, outcome, fail_open=self.config.fail_open),
            )
            return outcome
        finally:
            self._release_client(client)

    def commit(self, runtime: NanobotRuntimeState, candidate: MemoryCandidate) -> CommitOutcome:
        if self.config.mode == "off":
            return build_off_commit_outcome(self.config.mode, candidate.memory_id)

        self._telemetry.emit("commit_started", **commit_started_fields(self.config.mode, runtime, candidate.memory_id))
        client = self._get_client()
        try:
            policy_context = build_policy_context(
                runtime,
                "write",
                workspace_as_tenant=self.config.workspace_as_tenant,
            )
            protocol_candidate = build_memory_candidate(
                runtime,
                candidate,
                workspace_as_tenant=self.config.workspace_as_tenant,
            )
            response = client.write_candidate(
                policy_context,
                protocol_candidate,
                merge_hint=protocol_candidate.merge_hint,
            )
            returned_memory = (response.data or {}).get("memory", {})
            outcome = build_commit_success_outcome(
                self.config.mode,
                returned_memory=returned_memory,
                request_id=response.request_id,
            )
            self._telemetry.emit("commit_completed", **commit_completed_fields(self.config.mode, outcome))
            return outcome
        except (MGPError, httpx.HTTPError, ValueError) as error:
            if not self.config.fail_open:
                raise
            outcome = build_commit_failure_outcome(self.config.mode, candidate.memory_id, error)
            self._telemetry.emit(
                "commit_failed",
                **commit_failed_fields(self.config.mode, outcome, fail_open=self.config.fail_open),
            )
            return outcome
        finally:
            self._release_client(client)

    def close(self) -> None:
        if self._shared_client is None:
            return
        self._close_client(self._shared_client)
        self._shared_client = None

    def _get_client(self) -> SupportsMGPClient:
        if self.config.reuse_client:
            if self._shared_client is None:
                self._shared_client = self._make_client()
            return self._shared_client
        return self._make_client()

    def _make_client(self) -> SupportsMGPClient:
        return self._client_factory(
            self.config.gateway_url,
            self.config.timeout,
            dict(self.config.headers),
        )

    def _release_client(self, client: SupportsMGPClient) -> None:
        if self.config.reuse_client and client is self._shared_client:
            return
        self._close_client(client)

    @staticmethod
    def _close_client(client: SupportsMGPClient) -> None:
        close = getattr(client, "close", None)
        if callable(close):
            close()
