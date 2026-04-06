from __future__ import annotations

from typing import Any

from gateway.config import GatewaySettings, ensure_repo_root_on_path

ensure_repo_root_on_path()


class AdapterRouter:
    def __init__(self, settings: GatewaySettings | None = None, adapter_name: str | None = None) -> None:
        self.settings = settings or GatewaySettings.from_env()
        selected = adapter_name or self.settings.adapter
        self.adapter_name = selected
        self.adapter = self._build_adapter(selected)

    def _build_adapter(self, adapter_name: str):
        normalized = adapter_name.lower()
        if normalized in {"memory", "in-memory", "in_memory"}:
            from adapters.memory import InMemoryAdapter

            return InMemoryAdapter()
        if normalized == "file":
            from adapters.file import FileAdapter

            return FileAdapter(storage_dir=self.settings.file_storage_dir)
        if normalized == "graph":
            from adapters.graph import GraphAdapter

            return GraphAdapter(db_path=self.settings.graph_db_path)
        if normalized in {"postgres", "postgresql"}:
            from adapters.postgres import PostgresAdapter

            return PostgresAdapter(dsn=self.settings.postgres_dsn)
        if normalized == "lancedb":
            from adapters.lancedb import LanceDBAdapter

            return LanceDBAdapter(
                db_dir=self.settings.lancedb_dir,
                table_name=self.settings.lancedb_table,
                hybrid_enabled=self.settings.lancedb_enable_hybrid,
                embedding_provider=self.settings.lancedb_embedding_provider,
                embedding_model=self.settings.lancedb_embedding_model,
                embedding_api_key=self.settings.lancedb_embedding_api_key,
                embedding_base_url=self.settings.lancedb_embedding_base_url,
                embedding_dimension=self.settings.lancedb_embedding_dim,
            )
        if normalized == "mem0":
            from adapters.mem0 import Mem0Adapter

            return Mem0Adapter()
        if normalized == "zep":
            from adapters.zep import ZepAdapter

            return ZepAdapter()
        raise ValueError(f"unsupported adapter: {adapter_name}")

    def dispatch(self, operation: str, payload: dict[str, Any]) -> Any:
        if operation == "write":
            return self.adapter.write(payload["memory"])
        if operation == "search":
            return self.adapter.search(
                query=payload["query"],
                intent=payload.get("intent"),
                subject=payload.get("subject"),
                scope=payload.get("scope"),
                types=payload.get("types"),
                limit=payload.get("limit", 10),
            )
        if operation == "get":
            return self.adapter.get(payload["memory_id"])
        if operation == "update":
            return self.adapter.update(payload["memory_id"], payload["patch"])
        if operation == "expire":
            return self.adapter.expire(
                payload["memory_id"],
                expired_at=payload.get("expired_at"),
                reason=payload.get("reason"),
            )
        if operation == "revoke":
            return self.adapter.revoke(
                payload["memory_id"],
                revoked_at=payload.get("revoked_at"),
                reason=payload.get("reason"),
            )
        if operation == "delete":
            return self.adapter.delete(
                payload["memory_id"],
                deleted_at=payload.get("deleted_at"),
                reason=payload.get("reason"),
            )
        if operation == "purge":
            return self.adapter.purge(
                payload["memory_id"],
                purged_at=payload.get("purged_at"),
                reason=payload.get("reason"),
            )
        if operation == "list_memories":
            return self.adapter.list_memories(
                include_inactive=payload.get("include_inactive", False),
                limit=payload.get("limit"),
            )
        raise ValueError(f"unsupported operation: {operation}")

    def get_manifest(self) -> dict[str, Any]:
        return self.adapter.get_manifest()
