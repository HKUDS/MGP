# ruff: noqa: E402, I001
from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from gateway.config import ensure_repo_root_on_path

ensure_repo_root_on_path()

from gateway.middleware import GatewayAuthMiddleware, RequestContextMiddleware
from gateway.routes.memory import router as memory_router
from gateway.routes.operational import router as operational_router
from gateway.routes.protocol import router as protocol_router
from gateway.state import APP_VERSION, settings
from gateway.version import APP_TITLE

app = FastAPI(title=APP_TITLE, version=APP_VERSION)
app.add_middleware(GatewayAuthMiddleware, settings=settings)
app.add_middleware(RequestContextMiddleware, settings=settings)

app.include_router(operational_router)
app.include_router(memory_router)
app.include_router(protocol_router)


if __name__ == "__main__":
    uvicorn.run("gateway.app:app", host=settings.host, port=settings.port, reload=settings.reload)
