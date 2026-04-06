from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from gateway.operations import server_info
from gateway.state import APP_VERSION, audit_sink
from gateway.state import router as adapter_router
from gateway.validation import validate_adapter_manifest
from gateway.version import APP_NAME

router = APIRouter()


@router.get("/healthz")
async def healthz() -> JSONResponse:
    return JSONResponse(status_code=200, content={"status": "ok", "service": APP_NAME, "version": APP_VERSION})


@router.get("/readyz")
async def readyz() -> JSONResponse:
    try:
        manifest = adapter_router.get_manifest()
        validate_adapter_manifest(manifest)
        return JSONResponse(
            status_code=200,
            content={
                "status": "ready",
                "adapter": adapter_router.adapter_name,
                "audit_log": str(audit_sink.path),
                "manifest_backend_kind": manifest.get("backend_kind"),
            },
        )
    except Exception as error:  # pragma: no cover - operational path
        return JSONResponse(status_code=503, content={"status": "not_ready", "error": str(error)})


@router.get("/version")
async def version_info() -> JSONResponse:
    return JSONResponse(status_code=200, content=server_info(include_runtime_fields=True))
