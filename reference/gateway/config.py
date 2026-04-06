from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ensure_repo_root_on_path() -> None:
    root = project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


@dataclass
class GatewaySettings:
    host: str = "127.0.0.1"
    port: int = 8080
    reload: bool = False
    adapter: str = "memory"
    audit_log: str | None = None
    file_storage_dir: str | None = None
    graph_db_path: str | None = None
    postgres_dsn: str | None = None
    lancedb_dir: str | None = None
    lancedb_table: str | None = None
    lancedb_enable_hybrid: bool = True
    lancedb_embedding_provider: str | None = None
    lancedb_embedding_model: str | None = None
    lancedb_embedding_api_key: str | None = None
    lancedb_embedding_base_url: str | None = None
    lancedb_embedding_dim: int | None = None
    auth_mode: str = "off"
    api_key: str | None = None
    bearer_token: str | None = None
    tenant_header: str = "MGP-Tenant-Id"
    require_tenant_header: bool = False
    request_id_header: str = "MGP-Request-Id"
    version_header: str = "MGP-Version"
    log_level: str = "INFO"
    log_format: str = "json"
    environment: str = "development"

    @classmethod
    def from_env(cls) -> "GatewaySettings":
        lancedb_embedding_dim = os.getenv("MGP_LANCEDB_EMBEDDING_DIM")
        return cls(
            host=os.getenv("MGP_GATEWAY_HOST", "127.0.0.1"),
            port=int(os.getenv("MGP_GATEWAY_PORT", "8080")),
            reload=_env_flag("MGP_GATEWAY_RELOAD", False),
            adapter=os.getenv("MGP_ADAPTER", "memory"),
            audit_log=os.getenv("MGP_AUDIT_LOG"),
            file_storage_dir=os.getenv("MGP_FILE_STORAGE_DIR"),
            graph_db_path=os.getenv("MGP_GRAPH_DB_PATH"),
            postgres_dsn=os.getenv("MGP_POSTGRES_DSN"),
            lancedb_dir=os.getenv("MGP_LANCEDB_DIR"),
            lancedb_table=os.getenv("MGP_LANCEDB_TABLE"),
            lancedb_enable_hybrid=_env_flag("MGP_LANCEDB_ENABLE_HYBRID", True),
            lancedb_embedding_provider=os.getenv("MGP_LANCEDB_EMBEDDING_PROVIDER"),
            lancedb_embedding_model=os.getenv("MGP_LANCEDB_EMBEDDING_MODEL"),
            lancedb_embedding_api_key=os.getenv("MGP_LANCEDB_EMBEDDING_API_KEY"),
            lancedb_embedding_base_url=os.getenv("MGP_LANCEDB_EMBEDDING_BASE_URL"),
            lancedb_embedding_dim=int(lancedb_embedding_dim) if lancedb_embedding_dim else None,
            auth_mode=os.getenv("MGP_GATEWAY_AUTH_MODE", "off").strip().lower(),
            api_key=os.getenv("MGP_GATEWAY_API_KEY"),
            bearer_token=os.getenv("MGP_GATEWAY_BEARER_TOKEN"),
            tenant_header=os.getenv("MGP_GATEWAY_TENANT_HEADER", "MGP-Tenant-Id"),
            require_tenant_header=_env_flag("MGP_GATEWAY_REQUIRE_TENANT_HEADER", False),
            request_id_header=os.getenv("MGP_GATEWAY_REQUEST_ID_HEADER", "MGP-Request-Id"),
            version_header=os.getenv("MGP_GATEWAY_VERSION_HEADER", "MGP-Version"),
            log_level=os.getenv("MGP_GATEWAY_LOG_LEVEL", "INFO").upper(),
            log_format=os.getenv("MGP_GATEWAY_LOG_FORMAT", "json").strip().lower(),
            environment=os.getenv("MGP_GATEWAY_ENV", "development"),
        )

    def with_overrides(self, **updates: Any) -> "GatewaySettings":
        cleaned = {key: value for key, value in updates.items() if value is not None}
        return replace(self, **cleaned)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("request_id", "method", "path", "status_code", "adapter", "tenant_id", "environment"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(settings: GatewaySettings) -> None:
    root_logger = logging.getLogger()
    formatter: logging.Formatter
    if settings.log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter("%(levelname)s %(name)s %(message)s")

    if not root_logger.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)
    else:
        for existing_handler in root_logger.handlers:
            existing_handler.setFormatter(formatter)

    root_logger.setLevel(settings.log_level)


def apply_settings_environment(settings: GatewaySettings) -> None:
    os.environ["MGP_GATEWAY_HOST"] = settings.host
    os.environ["MGP_GATEWAY_PORT"] = str(settings.port)
    os.environ["MGP_GATEWAY_RELOAD"] = "true" if settings.reload else "false"
    os.environ["MGP_ADAPTER"] = settings.adapter
    os.environ["MGP_GATEWAY_AUTH_MODE"] = settings.auth_mode
    os.environ["MGP_GATEWAY_TENANT_HEADER"] = settings.tenant_header
    os.environ["MGP_GATEWAY_REQUIRE_TENANT_HEADER"] = "true" if settings.require_tenant_header else "false"
    os.environ["MGP_GATEWAY_REQUEST_ID_HEADER"] = settings.request_id_header
    os.environ["MGP_GATEWAY_VERSION_HEADER"] = settings.version_header
    os.environ["MGP_GATEWAY_LOG_LEVEL"] = settings.log_level
    os.environ["MGP_GATEWAY_LOG_FORMAT"] = settings.log_format
    os.environ["MGP_GATEWAY_ENV"] = settings.environment

    if settings.audit_log is not None:
        os.environ["MGP_AUDIT_LOG"] = settings.audit_log
    if settings.file_storage_dir is not None:
        os.environ["MGP_FILE_STORAGE_DIR"] = settings.file_storage_dir
    if settings.graph_db_path is not None:
        os.environ["MGP_GRAPH_DB_PATH"] = settings.graph_db_path
    if settings.postgres_dsn is not None:
        os.environ["MGP_POSTGRES_DSN"] = settings.postgres_dsn
    if settings.lancedb_dir is not None:
        os.environ["MGP_LANCEDB_DIR"] = settings.lancedb_dir
    if settings.lancedb_table is not None:
        os.environ["MGP_LANCEDB_TABLE"] = settings.lancedb_table
    os.environ["MGP_LANCEDB_ENABLE_HYBRID"] = "true" if settings.lancedb_enable_hybrid else "false"
    if settings.lancedb_embedding_provider is not None:
        os.environ["MGP_LANCEDB_EMBEDDING_PROVIDER"] = settings.lancedb_embedding_provider
    if settings.lancedb_embedding_model is not None:
        os.environ["MGP_LANCEDB_EMBEDDING_MODEL"] = settings.lancedb_embedding_model
    if settings.lancedb_embedding_api_key is not None:
        os.environ["MGP_LANCEDB_EMBEDDING_API_KEY"] = settings.lancedb_embedding_api_key
    if settings.lancedb_embedding_base_url is not None:
        os.environ["MGP_LANCEDB_EMBEDDING_BASE_URL"] = settings.lancedb_embedding_base_url
    if settings.lancedb_embedding_dim is not None:
        os.environ["MGP_LANCEDB_EMBEDDING_DIM"] = str(settings.lancedb_embedding_dim)
    if settings.api_key is not None:
        os.environ["MGP_GATEWAY_API_KEY"] = settings.api_key
    if settings.bearer_token is not None:
        os.environ["MGP_GATEWAY_BEARER_TOKEN"] = settings.bearer_token
