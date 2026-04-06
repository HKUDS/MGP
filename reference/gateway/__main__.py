from __future__ import annotations

import argparse

import uvicorn

from .config import GatewaySettings, apply_settings_environment, configure_logging
from .version import gateway_version


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the MGP reference gateway.")
    parser.add_argument("--host", help="Gateway bind host.")
    parser.add_argument("--port", type=int, help="Gateway bind port.")
    parser.add_argument("--reload", action="store_true", help="Enable autoreload for development.")
    parser.add_argument("--adapter", help="Adapter name: memory, file, graph, postgres, lancedb, mem0, or zep.")
    parser.add_argument("--audit-log", help="Path to the audit JSONL file.")
    parser.add_argument("--file-storage-dir", help="Storage directory for the file adapter.")
    parser.add_argument("--graph-db-path", help="SQLite path for the graph adapter.")
    parser.add_argument("--postgres-dsn", help="Connection string for the postgres adapter.")
    parser.add_argument("--lancedb-dir", help="Storage directory for the lancedb adapter.")
    parser.add_argument("--lancedb-table", help="Table name for the lancedb adapter.")
    parser.add_argument(
        "--lancedb-enable-hybrid",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable LanceDB hybrid search support.",
    )
    parser.add_argument("--lancedb-embedding-provider", help="Embedding provider for the lancedb adapter.")
    parser.add_argument("--lancedb-embedding-model", help="Embedding model for the lancedb adapter.")
    parser.add_argument("--auth-mode", choices=["off", "api_key", "bearer"], help="Authentication mode.")
    parser.add_argument("--api-key", help="Expected API key when auth mode is api_key.")
    parser.add_argument("--bearer-token", help="Expected bearer token when auth mode is bearer.")
    parser.add_argument("--tenant-header", help="Header used for tenant binding checks.")
    parser.add_argument(
        "--require-tenant-header",
        action="store_true",
        help="Require the tenant header on governed-memory routes.",
    )
    parser.add_argument("--log-level", help="Gateway log level.")
    parser.add_argument("--log-format", choices=["json", "plain"], help="Gateway log format.")
    parser.add_argument("--environment", help="Deployment environment label.")
    parser.add_argument("--version", action="store_true", help="Print the gateway version and exit.")
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()

    if args.version:
        print(gateway_version())
        return 0

    settings = GatewaySettings.from_env().with_overrides(
        host=args.host,
        port=args.port,
        reload=True if args.reload else None,
        adapter=args.adapter,
        audit_log=args.audit_log,
        file_storage_dir=args.file_storage_dir,
        graph_db_path=args.graph_db_path,
        postgres_dsn=args.postgres_dsn,
        lancedb_dir=args.lancedb_dir,
        lancedb_table=args.lancedb_table,
        lancedb_enable_hybrid=args.lancedb_enable_hybrid,
        lancedb_embedding_provider=args.lancedb_embedding_provider,
        lancedb_embedding_model=args.lancedb_embedding_model,
        auth_mode=args.auth_mode,
        api_key=args.api_key,
        bearer_token=args.bearer_token,
        tenant_header=args.tenant_header,
        require_tenant_header=True if args.require_tenant_header else None,
        log_level=args.log_level.upper() if args.log_level else None,
        log_format=args.log_format,
        environment=args.environment,
    )

    apply_settings_environment(settings)
    configure_logging(settings)
    uvicorn.run("gateway.app:app", host=settings.host, port=settings.port, reload=settings.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
