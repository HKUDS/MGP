from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

import httpx

from .auth import AuthConfig, TLSConfig, apply_auth_headers, httpx_tls_kwargs
from .errors import BackendError, raise_for_error
from .models import (
    AsyncTask,
    AuditQueryResponseData,
    BatchWriteResponseData,
    CapabilitiesResponseData,
    GetResponseData,
    InitializeResponseData,
    LifecycleResponseData,
    PolicyContext,
    SearchResponseData,
    TransferResponseData,
    WriteResponseData,
)
from .pagination import (
    iterate_audit_events_async,
    iterate_audit_pages_async,
    iterate_search_pages_async,
    iterate_search_results_async,
)
from .retry import RetryConfig, async_backoff_sleep, should_retry_exception, should_retry_response
from .tasks import wait_for_task_completion_async
from .types import AuditQuery, ClientOptions, MemoryCandidate, MGPResponse, SearchQuery


def _request_id(request_id: str | None = None) -> str:
    return request_id or f"req_{uuid4().hex}"


class AsyncMGPClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        headers: dict[str, str] | None = None,
        auth: AuthConfig | None = None,
        tls: TLSConfig | None = None,
        retry: RetryConfig | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.options = ClientOptions(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers=apply_auth_headers(headers or {}, auth),
            auth=auth,
            tls=tls,
            retry=retry or RetryConfig(),
        )
        self._client = httpx.AsyncClient(
            base_url=self.options.base_url,
            timeout=self.options.timeout,
            headers=self.options.headers,
            transport=transport,
            **httpx_tls_kwargs(self.options.tls),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncMGPClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def write_memory(
        self,
        policy_context: PolicyContext | dict[str, Any],
        memory: dict[str, Any],
        request_id: str | None = None,
    ) -> MGPResponse[WriteResponseData]:
        return await self._post("/mgp/write", policy_context, {"memory": memory}, request_id=request_id)

    async def write_candidate(
        self,
        policy_context: PolicyContext | dict[str, Any],
        candidate: MemoryCandidate | dict[str, Any],
        *,
        merge_hint: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> MGPResponse[WriteResponseData]:
        payload: dict[str, Any] = {
            "candidate": candidate.to_payload() if isinstance(candidate, MemoryCandidate) else candidate,
        }
        if merge_hint is not None:
            payload["merge_hint"] = merge_hint
        return await self._post("/mgp/write", policy_context, payload, request_id=request_id)

    async def search_memory(
        self,
        policy_context: PolicyContext | dict[str, Any],
        search: SearchQuery | dict[str, Any],
        request_id: str | None = None,
    ) -> MGPResponse[SearchResponseData]:
        payload = search.to_payload() if isinstance(search, SearchQuery) else search
        return await self._post("/mgp/search", policy_context, payload, request_id=request_id)

    async def get_memory(
        self,
        policy_context: PolicyContext | dict[str, Any],
        memory_id: str,
        request_id: str | None = None,
    ) -> MGPResponse[GetResponseData]:
        return await self._post("/mgp/get", policy_context, {"memory_id": memory_id}, request_id=request_id)

    async def update_memory(
        self,
        policy_context: PolicyContext | dict[str, Any],
        memory_id: str,
        patch: dict[str, Any],
        request_id: str | None = None,
    ) -> MGPResponse[GetResponseData]:
        return await self._post(
            "/mgp/update",
            policy_context,
            {"memory_id": memory_id, "patch": patch},
            request_id=request_id,
        )

    async def expire_memory(
        self,
        policy_context: PolicyContext | dict[str, Any],
        memory_id: str,
        *,
        expired_at: str | None = None,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> MGPResponse[LifecycleResponseData]:
        payload: dict[str, Any] = {"memory_id": memory_id}
        if expired_at is not None:
            payload["expired_at"] = expired_at
        if reason is not None:
            payload["reason"] = reason
        return await self._post("/mgp/expire", policy_context, payload, request_id=request_id)

    async def revoke_memory(
        self,
        policy_context: PolicyContext | dict[str, Any],
        memory_id: str,
        *,
        revoked_at: str | None = None,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> MGPResponse[LifecycleResponseData]:
        payload: dict[str, Any] = {"memory_id": memory_id}
        if revoked_at is not None:
            payload["revoked_at"] = revoked_at
        if reason is not None:
            payload["reason"] = reason
        return await self._post("/mgp/revoke", policy_context, payload, request_id=request_id)

    async def delete_memory(
        self,
        policy_context: PolicyContext | dict[str, Any],
        memory_id: str,
        *,
        deleted_at: str | None = None,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> MGPResponse[LifecycleResponseData]:
        payload: dict[str, Any] = {"memory_id": memory_id}
        if deleted_at is not None:
            payload["deleted_at"] = deleted_at
        if reason is not None:
            payload["reason"] = reason
        return await self._post("/mgp/delete", policy_context, payload, request_id=request_id)

    async def purge_memory(
        self,
        policy_context: PolicyContext | dict[str, Any],
        memory_id: str,
        *,
        purged_at: str | None = None,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> MGPResponse[LifecycleResponseData]:
        payload: dict[str, Any] = {"memory_id": memory_id}
        if purged_at is not None:
            payload["purged_at"] = purged_at
        if reason is not None:
            payload["reason"] = reason
        return await self._post("/mgp/purge", policy_context, payload, request_id=request_id)

    async def write_batch(
        self,
        policy_context: PolicyContext | dict[str, Any],
        items: list[dict[str, Any]],
        *,
        request_id: str | None = None,
    ) -> MGPResponse[BatchWriteResponseData]:
        return await self._post("/mgp/write/batch", policy_context, {"items": items}, request_id=request_id)

    async def export_memories(
        self,
        policy_context: PolicyContext | dict[str, Any],
        payload: dict[str, Any],
        *,
        request_id: str | None = None,
    ) -> MGPResponse[TransferResponseData]:
        return await self._post("/mgp/export", policy_context, payload, request_id=request_id)

    async def import_memories(
        self,
        policy_context: PolicyContext | dict[str, Any],
        payload: dict[str, Any],
        *,
        request_id: str | None = None,
    ) -> MGPResponse[TransferResponseData]:
        return await self._post("/mgp/import", policy_context, payload, request_id=request_id)

    async def sync_memories(
        self,
        policy_context: PolicyContext | dict[str, Any],
        payload: dict[str, Any],
        *,
        request_id: str | None = None,
    ) -> MGPResponse[TransferResponseData]:
        return await self._post("/mgp/sync", policy_context, payload, request_id=request_id)

    async def get_capabilities(self) -> CapabilitiesResponseData:
        response_body = await self._request_json("GET", "/mgp/capabilities")
        return cast(CapabilitiesResponseData, response_body)

    async def initialize(
        self,
        *,
        protocol_version: str | None = "0.1.0",
        supported_versions: list[str] | None = None,
        preferred_version: str | None = None,
        client_name: str = "mgp-python-sdk",
        client_version: str = "0.1.0",
        client_title: str | None = None,
        client_description: str | None = None,
        requested_capabilities: dict[str, Any] | None = None,
        runtime_capabilities: dict[str, Any] | None = None,
        requested_profiles: list[str] | None = None,
        transport_profile: str | None = None,
        request_id: str | None = None,
    ) -> InitializeResponseData:
        payload: dict[str, Any] = {
            "request_id": _request_id(request_id),
            "client": {
                "name": client_name,
                "version": client_version,
            },
        }
        if supported_versions is not None:
            payload["supported_versions"] = supported_versions
        elif protocol_version is not None:
            payload["protocol_version"] = protocol_version
        if preferred_version is not None:
            payload["preferred_version"] = preferred_version
        if client_title is not None:
            payload["client"]["title"] = client_title
        if client_description is not None:
            payload["client"]["description"] = client_description
        if requested_capabilities is not None:
            payload["requested_capabilities"] = requested_capabilities
        if runtime_capabilities is not None:
            payload["runtime_capabilities"] = runtime_capabilities
        if requested_profiles is not None:
            payload["requested_profiles"] = requested_profiles
        if transport_profile is not None:
            payload["transport_profile"] = transport_profile

        response_body = await self._request_json("POST", "/mgp/initialize", json_body=payload)
        return response_body["data"]

    async def query_audit(
        self,
        policy_context: PolicyContext | dict[str, Any],
        query: AuditQuery | dict[str, Any],
        request_id: str | None = None,
    ) -> MGPResponse[AuditQueryResponseData]:
        payload = query.to_payload() if isinstance(query, AuditQuery) else query
        return await self._post("/mgp/audit/query", policy_context, payload, request_id=request_id)

    async def get_task(self, task_id: str, request_id: str | None = None) -> AsyncTask:
        response_body = await self._request_json(
            "POST",
            "/mgp/tasks/get",
            json_body={
                "request_id": _request_id(request_id),
                "task_id": task_id,
            },
        )
        return response_body["data"]["task"]

    async def cancel_task(self, task_id: str, *, reason: str | None = None, request_id: str | None = None) -> AsyncTask:
        payload: dict[str, Any] = {
            "request_id": _request_id(request_id),
            "task_id": task_id,
        }
        if reason is not None:
            payload["reason"] = reason
        response_body = await self._request_json("POST", "/mgp/tasks/cancel", json_body=payload)
        return response_body["data"]["task"]

    async def wait_for_task(
        self,
        task_id: str,
        *,
        timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 0.5,
    ) -> AsyncTask:
        return await wait_for_task_completion_async(
            self,
            task_id,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    def iter_search_pages(
        self,
        policy_context: PolicyContext | dict[str, Any],
        search: SearchQuery | dict[str, Any],
    ):
        return iterate_search_pages_async(self, policy_context, search)

    def iter_search_results(
        self,
        policy_context: PolicyContext | dict[str, Any],
        search: SearchQuery | dict[str, Any],
    ):
        return iterate_search_results_async(self, policy_context, search)

    def iter_audit_pages(
        self,
        policy_context: PolicyContext | dict[str, Any],
        query: AuditQuery | dict[str, Any],
    ):
        return iterate_audit_pages_async(self, policy_context, query)

    def iter_audit_events(
        self,
        policy_context: PolicyContext | dict[str, Any],
        query: AuditQuery | dict[str, Any],
    ):
        return iterate_audit_events_async(self, policy_context, query)

    async def _post(
        self,
        path: str,
        policy_context: PolicyContext | dict[str, Any],
        payload: dict[str, Any],
        *,
        request_id: str | None = None,
    ) -> MGPResponse[Any]:
        body = {
            "request_id": _request_id(request_id),
            "policy_context": policy_context,
            "payload": payload,
        }
        response_body = await self._request_json("POST", path, json_body=body)
        return MGPResponse(
            request_id=response_body["request_id"],
            status=response_body["status"],
            data=response_body.get("data"),
            error=response_body.get("error"),
        )

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        attempt = 0
        while True:
            attempt += 1
            try:
                response = await self._client.request(method, path, json=json_body)
            except Exception as error:
                if should_retry_exception(error, self.options.retry, attempt):
                    await async_backoff_sleep(self.options.retry, attempt)
                    continue
                raise BackendError(
                    code="MGP_BACKEND_ERROR",
                    message=str(error),
                    details={"path": path, "method": method},
                ) from error

            if should_retry_response(response, self.options.retry, attempt):
                await async_backoff_sleep(self.options.retry, attempt)
                continue

            try:
                response_body = response.json()
            except ValueError as error:
                raise BackendError(
                    code="MGP_BACKEND_ERROR",
                    message="gateway returned a non-JSON response",
                    details={"path": path, "status_code": response.status_code},
                ) from error

            if isinstance(response_body, dict) and response_body.get("status") == "error":
                raise_for_error(response_body.get("error"))

            if response.status_code >= 400:
                raise BackendError(
                    code="MGP_BACKEND_ERROR",
                    message=f"gateway returned HTTP {response.status_code}",
                    details={"path": path, "status_code": response.status_code},
                )

            return response_body
