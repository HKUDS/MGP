# ruff: noqa: E402
from __future__ import annotations

import logging

from gateway.config import GatewaySettings, configure_logging, ensure_repo_root_on_path
from gateway.version import gateway_version

ensure_repo_root_on_path()

from audit.sink import AuditSink
from policy.hook import PolicyHook

from gateway.router import AdapterRouter
from gateway.tasks import TaskStore

settings = GatewaySettings.from_env()
configure_logging(settings)
LOGGER = logging.getLogger("mgp.gateway")

APP_VERSION = gateway_version()

router = AdapterRouter(settings)
policy_hook = PolicyHook()
audit_sink = AuditSink(file_path=settings.audit_log)
task_store = TaskStore()

PROTOCOL_PROFILE_ORDER = ["core-memory", "governance", "interop", "lifecycle"]
TRANSPORT_PROFILE = "stateless_http"
SESSION_MODE = "stateless"
CANONICAL_RETURN_MODES = ["raw", "summary", "masked", "metadata_only"]

LOGGER.info(
    "gateway_initialized",
    extra={
        "adapter": settings.adapter,
        "environment": settings.environment,
    },
)
