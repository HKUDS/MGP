from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .config import GatewaySettings
from .version import PROTOCOL_VERSION

LOGGER = logging.getLogger("mgp.gateway")
EXEMPT_PATHS = {"/healthz", "/readyz", "/version"}


def _request_id(request: Request, settings: GatewaySettings) -> str:
    header_value = request.headers.get(settings.request_id_header)
    return header_value or f"req_{uuid4().hex}"


def _error_response(request_id: str, code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "request_id": request_id,
            "status": "error",
            "error": {
                "code": code,
                "message": message,
                "details": {},
            },
            "data": None,
        },
    )


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: GatewaySettings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = _request_id(request, self.settings)
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[self.settings.request_id_header] = request_id
        response.headers[self.settings.version_header] = PROTOCOL_VERSION

        LOGGER.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "environment": self.settings.environment,
            },
        )
        return response


class GatewayAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: GatewaySettings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in EXEMPT_PATHS or self.settings.auth_mode == "off":
            return await call_next(request)

        request_id = _request_id(request, self.settings)
        mode = self.settings.auth_mode

        if mode == "api_key":
            provided_key = request.headers.get("X-MGP-API-Key")
            if not self.settings.api_key or provided_key != self.settings.api_key:
                return _error_response(request_id, "MGP_POLICY_DENIED", "Missing or invalid API key.", 401)
        elif mode == "bearer":
            authorization = request.headers.get("Authorization", "")
            prefix = "Bearer "
            token = authorization[len(prefix) :] if authorization.startswith(prefix) else None
            if not self.settings.bearer_token or token != self.settings.bearer_token:
                return _error_response(request_id, "MGP_POLICY_DENIED", "Missing or invalid bearer token.", 401)
        else:
            return _error_response(request_id, "MGP_INVALID_OBJECT", f"Unsupported auth mode: {mode}", 500)

        return await call_next(request)


def validate_tenant_binding(
    request: Request,
    policy_context: dict[str, Any],
    settings: GatewaySettings,
) -> tuple[bool, str | None]:
    if request.url.path in EXEMPT_PATHS:
        return True, None

    tenant_header_value = request.headers.get(settings.tenant_header)
    tenant_id = policy_context.get("tenant_id")

    if settings.require_tenant_header and not tenant_header_value:
        return False, f"Missing required tenant header: {settings.tenant_header}"

    if tenant_header_value and tenant_id and tenant_header_value != tenant_id:
        return False, f"Tenant header {settings.tenant_header} does not match policy_context.tenant_id"

    return True, None
