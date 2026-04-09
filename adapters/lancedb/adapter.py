from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from adapters.base import BaseAdapter
from adapters.memory_utils import apply_memory_patch, env_flag, matches_memory_filters, normalize_mgp_memory
from adapters.search_utils import (
    build_search_result_item,
    consumable_text,
    memory_matches_terms,
    recall_terms,
    search_score,
)

try:  # pragma: no cover - optional dependency
    import lancedb
    import pyarrow as pa
except Exception:  # pragma: no cover - optional dependency
    lancedb = None
    pa = None


def _parse_int(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _ttl_expiry(created_at: str | None, ttl_seconds: int | None) -> str | None:
    if created_at is None or ttl_seconds is None:
        return None
    created = _parse_datetime(created_at)
    if created is None:
        return None
    return (created + timedelta(seconds=int(ttl_seconds))).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _quote_sql(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip().lower())


def _tokenize(value: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", value.lower())


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        parts: list[str] = []
        for item in value.values():
            parts.extend(_flatten_strings(item))
        return parts
    if isinstance(value, list):
        parts = []
        for item in value:
            parts.extend(_flatten_strings(item))
        return parts
    return []


def _coerce_embedding_rows(value: Any) -> list[list[float]]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list):
        if not value:
            return []
        if isinstance(value[0], (int, float)):
            return [[float(item) for item in value]]
        rows: list[list[float]] = []
        for item in value:
            if hasattr(item, "tolist"):
                item = item.tolist()
            rows.append([float(part) for part in item])
        return rows
    raise TypeError("unexpected embedding payload shape")


class _EmbeddingClient:
    provider: str
    model_name: str
    dimension: int

    def embed_query(self, query: str) -> list[float]:
        raise NotImplementedError

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        raise NotImplementedError


class _FakeEmbeddingClient(_EmbeddingClient):
    def __init__(self, model_name: str, dimension: int = 64) -> None:
        self.provider = "fake"
        self.model_name = model_name
        self.dimension = dimension

    def embed_query(self, query: str) -> list[float]:
        return self._vectorize(query)

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        return [self._vectorize(text) for text in texts]

    def _vectorize(self, text: str) -> list[float]:
        features = _tokenize(text)
        if not features:
            normalized = _normalize_text(text)
            features = [normalized] if normalized else ["__empty__"]
        expanded: list[str] = []
        for token in features:
            expanded.append(token)
            if len(token) >= 5:
                expanded.extend(token[index : index + 3] for index in range(0, len(token) - 2))

        vector = [0.0] * self.dimension
        for feature in expanded:
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            for offset in range(0, 12, 3):
                index = int.from_bytes(digest[offset : offset + 2], "big") % self.dimension
                sign = 1.0 if digest[offset + 2] % 2 == 0 else -1.0
                vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [float(value / norm) for value in vector]


class _RegistryEmbeddingClient(_EmbeddingClient):
    def __init__(
        self,
        *,
        provider: str,
        model_name: str,
        api_key: str | None,
        base_url: str | None,
        dimension: int | None,
    ) -> None:
        from lancedb.embeddings import get_registry

        registry = get_registry()
        registry_name = provider
        provider_alias = provider
        if provider == "openrouter":
            registry_name = "openai"
            base_url = base_url or "https://openrouter.ai/api/v1"
        if provider == "gemini":
            registry_name = "gemini-text"

        try:
            provider_cls = registry.get(registry_name)
        except KeyError as error:
            raise RuntimeError(f"unsupported LanceDB embedding provider: {provider_alias}") from error

        kwargs: dict[str, Any] = {"name": model_name}
        model_fields = getattr(provider_cls, "model_fields", {})
        if dimension is not None and "dim" in model_fields:
            kwargs["dim"] = int(dimension)
        if api_key and "api_key" in model_fields:
            env_name = f"MGP_LANCEDB_{provider_alias.upper().replace('-', '_')}_API_KEY"
            registry.set_var(env_name, api_key)
            kwargs["api_key"] = f"$var:{env_name}"
        if base_url and "base_url" in model_fields:
            kwargs["base_url"] = base_url
        self._model = provider_cls.create(**kwargs)
        self.provider = provider_alias
        self.model_name = model_name
        self.dimension = int(dimension) if dimension is not None else int(self._model.ndims())

    def embed_query(self, query: str) -> list[float]:
        rows = _coerce_embedding_rows(self._model.compute_query_embeddings(query))
        if not rows:
            raise RuntimeError("embedding provider returned no query embedding")
        return rows[0]

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        rows = _coerce_embedding_rows(self._model.compute_source_embeddings(list(texts)))
        if not rows:
            raise RuntimeError("embedding provider returned no source embeddings")
        return rows


class LanceDBAdapter(BaseAdapter):
    """LanceDB-backed adapter for canonical MGP memory objects."""

    def __init__(
        self,
        *,
        db_dir: str | None = None,
        table_name: str | None = None,
        hybrid_enabled: bool | None = None,
        embedding_provider: str | None = None,
        embedding_model: str | None = None,
        embedding_api_key: str | None = None,
        embedding_base_url: str | None = None,
        embedding_dimension: int | None = None,
    ) -> None:
        if lancedb is None or pa is None:
            raise RuntimeError(
                "LanceDB adapter requires the optional dependency 'lancedb'. "
                "Install it with: pip install lancedb or pip install -e 'reference[lancedb]'"
            )

        self._manifest_path = Path(__file__).with_name("manifest.json")
        db_path_value = db_dir or os.getenv("MGP_LANCEDB_DIR") or ".mgp-lancedb"
        self._db_dir = Path(db_path_value).expanduser()
        self._db_dir.mkdir(parents=True, exist_ok=True)
        self._table_name = table_name or os.getenv("MGP_LANCEDB_TABLE", "memories")
        self._hybrid_requested = (
            hybrid_enabled if hybrid_enabled is not None else env_flag("MGP_LANCEDB_ENABLE_HYBRID", True)
        )
        self._embedding_provider = (
            (embedding_provider or os.getenv("MGP_LANCEDB_EMBEDDING_PROVIDER") or "openai").strip().lower()
        )
        self._embedding_model = (
            embedding_model or os.getenv("MGP_LANCEDB_EMBEDDING_MODEL") or self._default_embedding_model()
        ).strip()
        self._embedding_api_key = embedding_api_key or os.getenv("MGP_LANCEDB_EMBEDDING_API_KEY")
        self._embedding_base_url = embedding_base_url or os.getenv("MGP_LANCEDB_EMBEDDING_BASE_URL")
        self._embedding_dimension = embedding_dimension or _parse_int(os.getenv("MGP_LANCEDB_EMBEDDING_DIM"))
        if self._embedding_dimension is None:
            self._embedding_dimension = self._default_embedding_dimension()

        self._embedding = self._build_embedding_client()
        self._db = lancedb.connect(str(self._db_dir))
        self._table = self._open_or_create_table()
        self._validate_table_shape()
        self._hybrid_enabled = self._ensure_hybrid_index()

    def write(self, memory: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_memory(memory)
        self._upsert_memory(normalized)
        return copy.deepcopy(normalized)

    def search(
        self,
        query: str,
        intent: dict[str, Any] | None = None,
        subject: dict[str, Any] | None = None,
        scope: str | None = None,
        types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        terms = recall_terms(query, intent)
        semantic_query = self._effective_semantic_query(query, intent)
        if not terms or not semantic_query:
            return []

        candidate_limit = max(limit * 5, 25)
        filter_expression = self._filter_expression(subject=subject, scope=scope, types=types, active_only=True)
        results: list[dict[str, Any]]
        retrieval_mode = "semantic"

        if self._hybrid_enabled:
            text_query = self._effective_text_query(query, intent)
            try:
                results = self._execute_hybrid_search(
                    semantic_query=semantic_query,
                    text_query=text_query,
                    filter_expression=filter_expression,
                    limit=candidate_limit,
                )
                retrieval_mode = "hybrid"
            except Exception:
                results = self._execute_semantic_search(
                    semantic_query=semantic_query,
                    filter_expression=filter_expression,
                    limit=candidate_limit,
                )
        else:
            results = self._execute_semantic_search(
                semantic_query=semantic_query,
                filter_expression=filter_expression,
                limit=candidate_limit,
            )

        items: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        for row in results:
            memory = self._row_to_memory(row)
            if not self._memory_is_searchable(memory):
                continue
            if not matches_memory_filters(memory, subject=subject, scope=scope, types=types):
                continue

            matches = memory_matches_terms(memory, terms)
            if not matches:
                continue

            collapse_key = self._collapse_key(memory)
            if collapse_key in seen_keys:
                continue
            seen_keys.add(collapse_key)

            score = self._result_score(row=row, retrieval_mode=retrieval_mode, fallback=search_score(matches, terms))
            items.append(
                build_search_result_item(
                    memory,
                    score=score,
                    retrieval_mode=retrieval_mode,
                    term_matches=matches,
                    explanation=self._explanation(retrieval_mode),
                )
            )

        items.sort(key=lambda item: (item["score"], item["memory"]["memory_id"]), reverse=True)
        return items[:limit]

    def get(self, memory_id: str) -> dict[str, Any] | None:
        row = self._get_row(memory_id)
        if row is None:
            return None
        return self._row_to_memory(row)

    def update(self, memory_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        current = self.get(memory_id)
        if current is None:
            return None
        if current.get("backend_ref", {}).get("mgp_state") == "deleted":
            return None

        merged = apply_memory_patch(current, patch)
        merged["updated_at"] = _now_iso()
        normalized = self._normalize_memory(merged)
        self._upsert_memory(normalized)
        return copy.deepcopy(normalized)

    def expire(
        self,
        memory_id: str,
        expired_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        return self._transition_state(
            memory_id,
            state="expired",
            timestamp_key="mgp:expired_at",
            timestamp_value=expired_at,
            reason=reason,
        )

    def revoke(
        self,
        memory_id: str,
        revoked_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        return self._transition_state(
            memory_id,
            state="revoked",
            timestamp_key="mgp:revoked_at",
            timestamp_value=revoked_at,
            reason=reason,
        )

    def delete(
        self,
        memory_id: str,
        deleted_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        return self._transition_state(
            memory_id,
            state="deleted",
            timestamp_key="mgp:deleted_at",
            timestamp_value=deleted_at,
            reason=reason,
        )

    def purge(
        self,
        memory_id: str,
        purged_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        current = self.get(memory_id)
        if current is None:
            return None
        self._table.delete(f"memory_id = {_quote_sql(memory_id)}")
        return {"memory_id": memory_id, "state": "purged", "purged_at": purged_at, "reason": reason}

    def list_memories(
        self,
        *,
        include_inactive: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        filter_expression = None if include_inactive else "mgp_state = 'active'"
        rows = self._table_rows(filter_expression=filter_expression, limit=limit)
        memories: list[dict[str, Any]] = []
        for row in rows:
            memory = self._row_to_memory(row)
            if not include_inactive and not self._memory_is_searchable(memory):
                continue
            memories.append(memory)
        memories.sort(key=lambda item: item["memory_id"])
        return memories if limit is None else memories[:limit]

    def get_manifest(self) -> dict[str, Any]:
        with self._manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        manifest["capabilities"]["search_modes"] = ["semantic", "hybrid"] if self._hybrid_enabled else ["semantic"]
        manifest["capabilities"]["score_kind"] = "backend_local"
        return manifest

    def _build_embedding_client(self) -> _EmbeddingClient:
        if self._embedding_provider == "fake":
            return _FakeEmbeddingClient(
                model_name=self._embedding_model,
                dimension=self._embedding_dimension or 64,
            )
        return _RegistryEmbeddingClient(
            provider=self._embedding_provider,
            model_name=self._embedding_model,
            api_key=self._embedding_api_key,
            base_url=self._embedding_base_url,
            dimension=self._embedding_dimension,
        )

    def _default_embedding_model(self) -> str:
        if self._embedding_provider == "openrouter":
            return "openai/text-embedding-3-small"
        if self._embedding_provider in {"gemini", "gemini-text"}:
            return "text-embedding-004"
        if self._embedding_provider == "fake":
            return "mgp-fake-embedding-v1"
        return "text-embedding-3-small"

    def _default_embedding_dimension(self) -> int | None:
        normalized_model = self._embedding_model.lower()
        if self._embedding_provider in {"openai", "openrouter"}:
            if normalized_model.endswith("text-embedding-3-small"):
                return 1536
            if normalized_model.endswith("text-embedding-3-large"):
                return 3072
            if normalized_model.endswith("text-embedding-ada-002"):
                return 1536
        if self._embedding_provider in {"gemini", "gemini-text"}:
            if normalized_model.endswith("text-embedding-004"):
                return 768
        return None

    def _table_schema(self):
        vector_type = pa.list_(pa.float32(), self._embedding.dimension)
        return pa.schema(
            [
                ("memory_id", pa.string()),
                ("subject_kind", pa.string()),
                ("subject_id", pa.string()),
                ("scope", pa.string()),
                ("type", pa.string()),
                ("mgp_state", pa.string()),
                ("created_at", pa.string()),
                ("updated_at", pa.string()),
                ("expires_at", pa.string()),
                ("sensitivity", pa.string()),
                ("retention_policy", pa.string()),
                ("ttl_seconds", pa.int64()),
                ("dedupe_key", pa.string()),
                ("consumable_text", pa.string()),
                ("search_text", pa.string()),
                ("embedding_provider", pa.string()),
                ("embedding_model", pa.string()),
                ("memory_json", pa.string()),
                ("vector", vector_type),
            ]
        )

    def _open_or_create_table(self):
        try:
            return self._db.open_table(self._table_name)
        except Exception:
            return self._db.create_table(self._table_name, schema=self._table_schema())

    def _validate_table_shape(self) -> None:
        schema = self._table.schema
        required_fields = {
            "memory_id",
            "subject_kind",
            "subject_id",
            "scope",
            "type",
            "mgp_state",
            "created_at",
            "updated_at",
            "expires_at",
            "sensitivity",
            "retention_policy",
            "ttl_seconds",
            "dedupe_key",
            "consumable_text",
            "search_text",
            "embedding_provider",
            "embedding_model",
            "memory_json",
            "vector",
        }
        missing = required_fields.difference(schema.names)
        if missing:
            raise RuntimeError(f"LanceDB table '{self._table_name}' is missing required fields: {sorted(missing)}")

        vector_field = schema.field("vector")
        vector_dimension = getattr(vector_field.type, "list_size", None)
        if vector_dimension != self._embedding.dimension:
            raise RuntimeError(
                "LanceDB vector dimension mismatch: "
                f"table has {vector_dimension}, embedding model expects {self._embedding.dimension}"
            )

        if self._table.count_rows() == 0:
            return

        sample = self._table_rows(limit=1)
        if not sample:
            return
        row = sample[0]
        stored_provider = row.get("embedding_provider")
        stored_model = row.get("embedding_model")
        if stored_provider and stored_provider != self._embedding.provider:
            raise RuntimeError(
                "LanceDB table already contains embeddings from "
                f"provider '{stored_provider}', but current config requested '{self._embedding.provider}'."
            )
        if stored_model and stored_model != self._embedding.model_name:
            raise RuntimeError(
                "LanceDB table already contains embeddings for "
                f"model '{stored_model}', but current config requested '{self._embedding.model_name}'."
            )

    def _ensure_hybrid_index(self) -> bool:
        if not self._hybrid_requested:
            return False
        try:
            self._table.create_fts_index("search_text", replace=True)
        except Exception:
            return False
        return True

    def _memory_to_row(self, memory: dict[str, Any]) -> dict[str, Any]:
        subject = memory.get("subject", {})
        extensions = memory.get("extensions", {})
        dedupe_key = extensions.get("mgp:dedupe_key")
        search_text = self._search_text(memory)
        vector = self._embedding.embed_query(search_text)
        ttl_seconds = memory.get("ttl_seconds")
        ttl_value = int(ttl_seconds) if ttl_seconds is not None else None
        return {
            "memory_id": memory["memory_id"],
            "subject_kind": subject.get("kind"),
            "subject_id": subject.get("id"),
            "scope": memory.get("scope"),
            "type": memory.get("type"),
            "mgp_state": memory.get("backend_ref", {}).get("mgp_state", "active"),
            "created_at": memory.get("created_at"),
            "updated_at": memory.get("updated_at"),
            "expires_at": _ttl_expiry(memory.get("created_at"), ttl_value),
            "sensitivity": memory.get("sensitivity"),
            "retention_policy": memory.get("retention_policy"),
            "ttl_seconds": ttl_value,
            "dedupe_key": dedupe_key if isinstance(dedupe_key, str) else None,
            "consumable_text": consumable_text(memory),
            "search_text": search_text,
            "embedding_provider": self._embedding.provider,
            "embedding_model": self._embedding.model_name,
            "memory_json": _json_dumps(memory),
            "vector": [float(value) for value in vector],
        }

    def _search_text(self, memory: dict[str, Any]) -> str:
        content = memory.get("content", {})
        parts: list[str] = [
            memory.get("memory_id", ""),
            memory.get("type", ""),
            memory.get("scope", ""),
            consumable_text(memory),
        ]
        if isinstance(content, dict):
            for key in ("statement", "summary", "fact", "preference", "preference_key", "preference_value"):
                value = content.get(key)
                if isinstance(value, str):
                    parts.append(value)
            keywords = content.get("keywords")
            if isinstance(keywords, list):
                parts.extend(str(keyword) for keyword in keywords if str(keyword).strip())
            parts.extend(_flatten_strings(content))
        return " ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())

    def _upsert_memory(self, memory: dict[str, Any]) -> None:
        row = self._memory_to_row(memory)
        (self._table.merge_insert("memory_id").when_matched_update_all().when_not_matched_insert_all().execute([row]))

    def _get_row(self, memory_id: str) -> dict[str, Any] | None:
        rows = self._table_rows(filter_expression=f"memory_id = {_quote_sql(memory_id)}", limit=1)
        if not rows:
            return None
        return rows[0]

    def _table_rows(self, *, filter_expression: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        if limit is None:
            limit_value = max(self._table.count_rows(filter=filter_expression), 1)
        else:
            limit_value = max(limit, 1)
        builder = self._table.search()
        if filter_expression:
            builder = builder.where(filter_expression)
        return builder.limit(limit_value).to_list()

    def _row_to_memory(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = row.get("memory_json")
        if isinstance(payload, str):
            memory = json.loads(payload)
        else:
            memory = copy.deepcopy(payload or {})
        backend_ref = memory.setdefault("backend_ref", {})
        backend_ref["adapter"] = "lancedb"
        backend_ref["mgp_state"] = row.get("mgp_state") or backend_ref.get("mgp_state") or "active"
        memory.setdefault("extensions", {})
        memory.setdefault("content", {})
        return memory

    def _effective_semantic_query(self, query: str, intent: dict[str, Any] | None) -> str:
        if query.strip():
            return query.strip()
        if intent and str(intent.get("query_text") or "").strip():
            return str(intent["query_text"]).strip()
        keywords = [str(keyword).strip() for keyword in (intent or {}).get("keywords") or [] if str(keyword).strip()]
        return " ".join(keywords)

    def _effective_text_query(self, query: str, intent: dict[str, Any] | None) -> str:
        keywords = [str(keyword).strip() for keyword in (intent or {}).get("keywords") or [] if str(keyword).strip()]
        if keywords:
            return " ".join(keywords)
        return self._effective_semantic_query(query, intent)

    def _execute_semantic_search(
        self,
        *,
        semantic_query: str,
        filter_expression: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        query_vector = self._embedding.embed_query(semantic_query)
        builder = self._table.search(query_vector, query_type="vector")
        if filter_expression:
            builder = builder.where(filter_expression)
        return builder.limit(limit).to_list()

    def _execute_hybrid_search(
        self,
        *,
        semantic_query: str,
        text_query: str,
        filter_expression: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        query_vector = self._embedding.embed_query(semantic_query)
        builder = self._table.search(query_type="hybrid").vector(query_vector).text(text_query)
        if filter_expression:
            builder = builder.where(filter_expression)
        return builder.limit(limit).to_list()

    def _filter_expression(
        self,
        *,
        subject: dict[str, Any] | None,
        scope: str | None,
        types: list[str] | None,
        active_only: bool,
    ) -> str | None:
        clauses: list[str] = []
        if active_only:
            clauses.append("mgp_state = 'active'")
        if subject is not None:
            kind = subject.get("kind")
            identifier = subject.get("id")
            if kind:
                clauses.append(f"subject_kind = {_quote_sql(str(kind))}")
            if identifier:
                clauses.append(f"subject_id = {_quote_sql(str(identifier))}")
        if scope:
            clauses.append(f"scope = {_quote_sql(scope)}")
        if types:
            quoted = ", ".join(_quote_sql(value) for value in types)
            clauses.append(f"type IN ({quoted})")
        return " AND ".join(clauses) if clauses else None

    def _memory_is_searchable(self, memory: dict[str, Any]) -> bool:
        backend_ref = memory.get("backend_ref", {})
        if backend_ref.get("mgp_state") != "active":
            return False
        ttl_seconds = memory.get("ttl_seconds")
        created_at = memory.get("created_at")
        expires_at = _ttl_expiry(created_at, int(ttl_seconds)) if ttl_seconds is not None else None
        if expires_at is None:
            return True
        expiry = _parse_datetime(expires_at)
        return expiry is None or expiry > datetime.now(timezone.utc)

    def _collapse_key(self, memory: dict[str, Any]) -> str:
        extensions = memory.get("extensions", {})
        dedupe_key = extensions.get("mgp:dedupe_key")
        if isinstance(dedupe_key, str) and dedupe_key.strip():
            return f"dedupe:{dedupe_key.strip().lower()}"
        subject = memory.get("subject", {})
        statement = memory.get("content", {}).get("statement")
        normalized = _normalize_text(statement if isinstance(statement, str) else consumable_text(memory))
        return "|".join(
            [
                str(memory.get("type", "")),
                str(subject.get("kind", "")),
                str(subject.get("id", "")),
                normalized,
            ]
        )

    def _result_score(self, *, row: dict[str, Any], retrieval_mode: str, fallback: float) -> float:
        if retrieval_mode == "hybrid":
            relevance = row.get("_relevance_score")
            if relevance is not None:
                return float(relevance)
        distance = row.get("_distance")
        if distance is not None:
            return round(1.0 / (1.0 + float(distance)), 6)
        score = row.get("_score")
        if score is not None:
            return float(score)
        return fallback

    def _explanation(self, retrieval_mode: str) -> str:
        if retrieval_mode == "hybrid":
            return "Retrieved from LanceDB hybrid search while preserving the canonical MGP memory shape."
        return "Retrieved from LanceDB semantic search while preserving the canonical MGP memory shape."

    def _transition_state(
        self,
        memory_id: str,
        *,
        state: str,
        timestamp_key: str,
        timestamp_value: str | None,
        reason: str | None,
    ) -> dict[str, Any] | None:
        current = self.get(memory_id)
        if current is None:
            return None

        memory = self._normalize_memory(current)
        memory.setdefault("backend_ref", {})["mgp_state"] = state
        memory.setdefault("extensions", {})["mgp:last_state_reason"] = reason
        if timestamp_value is not None:
            memory["extensions"][timestamp_key] = timestamp_value
        memory["updated_at"] = _now_iso()
        self._upsert_memory(memory)
        return {"memory_id": memory_id, "state": state}

    def _normalize_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        return normalize_mgp_memory(memory, adapter_name="lancedb")
