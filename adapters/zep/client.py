from __future__ import annotations

import importlib
from typing import Any

try:  # pragma: no cover - optional dependency
    zep_cloud = importlib.import_module("zep_cloud")
    ZepClientSdk: Any = getattr(zep_cloud, "Zep")
    ZepMessage: Any = getattr(zep_cloud, "Message")
except Exception:  # pragma: no cover - compatibility for alternate package layout
    try:
        zep_cloud_client = importlib.import_module("zep_cloud.client")
        zep_cloud_types = importlib.import_module("zep_cloud.types")
        ZepClientSdk = getattr(zep_cloud_client, "Zep")
        ZepMessage = getattr(zep_cloud_types, "Message")
    except Exception:  # pragma: no cover - optional dependency
        ZepClientSdk = None
        ZepMessage = None


class ZepClient:
    def __init__(self, *, api_key: str, base_url: str | None = None) -> None:
        if ZepClientSdk is None:
            raise RuntimeError(
                "Zep SDK integration requested but zep_cloud is not installed. "
                "Install it with: pip install zep-cloud"
            )

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = ZepClientSdk(**kwargs)

    def add_messages(
        self,
        *,
        thread_id: str,
        user_id: str,
        messages: list[dict[str, str]],
        return_context: bool = False,
        ignore_roles: list[str] | None = None,
    ) -> Any:
        self.ensure_user(user_id=user_id)
        self.ensure_thread(thread_id=thread_id, user_id=user_id)
        payload = [self._message(item) for item in messages]
        method = getattr(self._client.thread, "add_messages", None)
        if method is None:
            raise RuntimeError("Installed Zep client does not expose thread.add_messages")
        return method(
            thread_id=thread_id,
            messages=payload,
            return_context=return_context,
            ignore_roles=ignore_roles,
        )

    def ensure_thread(self, *, thread_id: str, user_id: str) -> Any:
        method = getattr(self._client.thread, "create", None)
        if method is None:
            raise RuntimeError("Installed Zep client does not expose thread.create")
        try:
            return method(thread_id=thread_id, user_id=user_id)
        except Exception as error:
            message = str(error).lower()
            if "already exists" in message or "409" in message or "conflict" in message:
                return None
            raise

    def ensure_user(self, *, user_id: str) -> Any:
        method = getattr(self._client.user, "add", None)
        if method is None:
            raise RuntimeError("Installed Zep client does not expose user.add")
        try:
            return method(user_id=user_id)
        except Exception as error:
            message = str(error).lower()
            if "already exists" in message or "409" in message or "conflict" in message:
                return None
            raise

    def get_user_context(self, *, thread_id: str) -> Any:
        method = getattr(self._client.thread, "get_user_context", None)
        if method is None:
            raise RuntimeError("Installed Zep client does not expose thread.get_user_context")
        return method(thread_id=thread_id)

    def graph_add(
        self,
        *,
        user_id: str,
        text: str,
        entry_type: str = "text",
        created_at: str | None = None,
        source_description: str | None = None,
    ) -> Any:
        self.ensure_user(user_id=user_id)
        graph = getattr(self._client, "graph", None)
        if graph is None:
            raise RuntimeError("Installed Zep client does not expose graph operations")
        if hasattr(graph, "add"):
            kwargs: dict[str, Any] = {"user_id": user_id, "data": text, "type": entry_type}
            if created_at:
                kwargs["created_at"] = created_at
            if source_description:
                kwargs["source_description"] = source_description
            return graph.add(**kwargs)
        raise RuntimeError("Installed Zep client does not expose graph.add")

    def graph_search(
        self,
        *,
        user_id: str,
        query: str,
        scope: str = "edges",
        limit: int = 10,
        search_filters: dict[str, Any] | None = None,
        reranker: str | None = None,
    ) -> Any:
        graph = getattr(self._client, "graph", None)
        if graph is None or not hasattr(graph, "search"):
            raise RuntimeError("Installed Zep client does not expose graph.search")
        kwargs: dict[str, Any] = {
            "user_id": user_id,
            "query": query,
            "scope": scope,
            "limit": limit,
        }
        if search_filters:
            kwargs["search_filters"] = search_filters
        if reranker:
            kwargs["reranker"] = reranker
        return graph.search(**kwargs)

    def get_episode(self, *, uuid_: str) -> Any:
        graph = getattr(self._client, "graph", None)
        if graph is None:
            raise RuntimeError("Installed Zep client does not expose graph operations")
        episode = getattr(graph, "episode", None)
        if episode is None or not hasattr(episode, "get"):
            raise RuntimeError("Installed Zep client does not expose graph.episode.get")
        return episode.get(uuid_=uuid_)

    def get_user_episodes(self, *, user_id: str, last: int | None = None) -> Any:
        graph = getattr(self._client, "graph", None)
        if graph is None:
            raise RuntimeError("Installed Zep client does not expose graph operations")
        episode = getattr(graph, "episode", None)
        if episode is None or not hasattr(episode, "get_by_user_id"):
            raise RuntimeError("Installed Zep client does not expose graph.episode.get_by_user_id")
        kwargs: dict[str, Any] = {"user_id": user_id}
        if last is not None:
            kwargs["lastn"] = last
        return episode.get_by_user_id(**kwargs)

    def delete_episode(self, *, uuid_: str) -> Any:
        graph = getattr(self._client, "graph", None)
        if graph is None:
            raise RuntimeError("Installed Zep client does not expose graph operations")
        episode = getattr(graph, "episode", None)
        if episode is None or not hasattr(episode, "delete"):
            raise RuntimeError("Installed Zep client does not expose graph.episode.delete")
        return episode.delete(uuid_=uuid_)

    def delete_edge(self, *, uuid_: str) -> Any:
        graph = getattr(self._client, "graph", None)
        edge = getattr(graph, "edge", None) if graph is not None else None
        if edge is None or not hasattr(edge, "delete"):
            raise RuntimeError("Installed Zep client does not expose graph.edge.delete")
        return edge.delete(uuid_=uuid_)

    def update_edge(
        self,
        *,
        uuid_: str,
        fact: str | None = None,
        name: str | None = None,
        attributes: dict[str, Any] | None = None,
        expired_at: str | None = None,
        invalid_at: str | None = None,
        valid_at: str | None = None,
    ) -> Any:
        graph = getattr(self._client, "graph", None)
        edge = getattr(graph, "edge", None) if graph is not None else None
        if edge is None or not hasattr(edge, "update"):
            raise RuntimeError("Installed Zep client does not expose graph.edge.update")
        kwargs: dict[str, Any] = {"uuid_": uuid_}
        if fact is not None:
            kwargs["fact"] = fact
        if name is not None:
            kwargs["name"] = name
        if attributes is not None:
            kwargs["attributes"] = attributes
        if expired_at is not None:
            kwargs["expired_at"] = expired_at
        if invalid_at is not None:
            kwargs["invalid_at"] = invalid_at
        if valid_at is not None:
            kwargs["valid_at"] = valid_at
        return edge.update(**kwargs)

    def _message(self, item: dict[str, str]):
        role = item.get("role", "user")
        content = item.get("content", "")
        name = item.get("name")
        if ZepMessage is None:  # pragma: no cover - defensive
            raise RuntimeError("Zep Message type is unavailable")
        kwargs: dict[str, Any] = {
            "content": content,
            "role": role,
        }
        if name:
            kwargs["name"] = name
        return ZepMessage(**kwargs)
