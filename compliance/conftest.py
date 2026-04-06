from __future__ import annotations

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "reference"
SCHEMA_DIR = ROOT / "schemas"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
HOST = "127.0.0.1"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_gateway_runtime = importlib.import_module("scripts.gateway_runtime")
allocate_port = _gateway_runtime.allocate_port
wait_for_ready = _gateway_runtime.wait_for_ready


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="session")
def root_dir() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def schema_dir() -> Path:
    return SCHEMA_DIR


@pytest.fixture(scope="session")
def base_url(gateway_process) -> str:
    return gateway_process["base_url"]

@pytest.fixture(scope="session")
def gateway_process(tmp_path_factory: pytest.TempPathFactory):
    if not VENV_PYTHON.exists():
        raise RuntimeError("Virtual environment not found at .venv; install dependencies first.")

    runtime_dir = tmp_path_factory.mktemp("mgp-runtime")
    port = allocate_port(HOST)
    base_url = f"http://{HOST}:{port}"
    audit_log = runtime_dir / "audit.jsonl"
    gateway_log = runtime_dir / "gateway.log"
    file_storage = runtime_dir / "file-storage"
    file_storage.mkdir(parents=True, exist_ok=True)
    graph_db = runtime_dir / "graph.db"
    lancedb_dir = runtime_dir / "lancedb"
    lancedb_dir.mkdir(parents=True, exist_ok=True)
    log_handle = gateway_log.open("w+", encoding="utf-8", buffering=1)

    env = os.environ.copy()
    env["MGP_AUDIT_LOG"] = str(audit_log)
    env["MGP_ADAPTER"] = env.get("MGP_ADAPTER", "memory")
    env["MGP_FILE_STORAGE_DIR"] = str(file_storage)
    env["MGP_GRAPH_DB_PATH"] = str(graph_db)
    env["MGP_LANCEDB_DIR"] = env.get("MGP_LANCEDB_DIR", str(lancedb_dir))
    env["MGP_LANCEDB_TABLE"] = env.get("MGP_LANCEDB_TABLE", "memories")
    env["MGP_LANCEDB_ENABLE_HYBRID"] = env.get("MGP_LANCEDB_ENABLE_HYBRID", "1")
    env["MGP_LANCEDB_EMBEDDING_PROVIDER"] = env.get("MGP_LANCEDB_EMBEDDING_PROVIDER", "fake")
    env["MGP_LANCEDB_EMBEDDING_MODEL"] = env.get("MGP_LANCEDB_EMBEDDING_MODEL", "mgp-fake-embedding-v1")
    env["MGP_LANCEDB_EMBEDDING_DIM"] = env.get("MGP_LANCEDB_EMBEDDING_DIM", "64")

    if env["MGP_ADAPTER"] == "postgres" and not env.get("MGP_POSTGRES_DSN"):
        pytest.skip("Postgres adapter tests require MGP_POSTGRES_DSN.")

    if env["MGP_ADAPTER"] == "lancedb" and importlib.util.find_spec("lancedb") is None:
        pytest.skip("LanceDB adapter tests require lancedb. Install it with: pip install lancedb")

    if env["MGP_ADAPTER"] == "mem0" and not (env.get("MGP_MEM0_API_KEY") or env.get("MEM0_API_KEY")):
        pytest.skip("Mem0 adapter tests require MGP_MEM0_API_KEY or MEM0_API_KEY.")

    if env["MGP_ADAPTER"] == "zep" and not (env.get("MGP_ZEP_API_KEY") or env.get("ZEP_API_KEY")):
        pytest.skip("Zep adapter tests require MGP_ZEP_API_KEY or ZEP_API_KEY.")

    process = subprocess.Popen(
        [
            str(VENV_PYTHON),
            "-m",
            "uvicorn",
            "gateway.app:app",
            "--host",
            HOST,
            "--port",
            str(port),
            "--no-access-log",
        ],
        cwd=str(REFERENCE_DIR),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )

    try:
        wait_for_ready(
            base_url,
            40.0,
            is_process_running=lambda: process.poll() is None,
        )
    except Exception as error:  # pragma: no cover - setup failure path
        process.kill()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
        log_handle.flush()
        log_handle.seek(0)
        stdout = log_handle.read()
        log_handle.close()
        raise RuntimeError(f"Gateway failed to start: {error}\n{stdout}")

    if process.poll() is not None:
        log_handle.flush()
        log_handle.seek(0)
        stdout = log_handle.read()
        exit_code = process.returncode
        log_handle.close()
        raise RuntimeError(f"Gateway exited early with code {exit_code}\n{stdout}")

    yield {
        "process": process,
        "audit_log": audit_log,
        "file_storage": file_storage,
        "graph_db": graph_db,
        "lancedb_dir": lancedb_dir,
        "gateway_log": gateway_log,
        "adapter": env["MGP_ADAPTER"],
        "port": port,
        "base_url": base_url,
    }

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:  # pragma: no cover - defensive cleanup
        process.kill()
    finally:
        log_handle.close()


@pytest.fixture
def audit_log_path(gateway_process) -> Path:
    return gateway_process["audit_log"]


@pytest.fixture
def adapter_name(gateway_process) -> str:
    return gateway_process["adapter"]


@pytest.fixture
def adapter_manifest(mgp_get) -> dict[str, Any]:
    return mgp_get("/mgp/capabilities").json()["manifest"]


@pytest.fixture
def manifest_capabilities(adapter_manifest) -> dict[str, Any]:
    return adapter_manifest["capabilities"]


@pytest.fixture
def mgp_get(base_url: str, gateway_process) -> Callable[[str], httpx.Response]:
    def _call(path: str) -> httpx.Response:
        return httpx.get(f"{base_url}{path}", timeout=5.0, trust_env=False)

    return _call


@pytest.fixture
def mgp_post(base_url: str, gateway_process) -> Callable[[str, dict[str, Any]], httpx.Response]:
    def _call(path: str, payload: dict[str, Any]) -> httpx.Response:
        return httpx.post(f"{base_url}{path}", json=payload, timeout=5.0, trust_env=False)

    return _call


@pytest.fixture
def make_policy_context() -> Callable[..., dict[str, Any]]:
    def _make(
        *,
        action: str,
        actor_agent: str = "nanobot/main",
        subject_kind: str = "user",
        subject_id: str = "user_123",
        tenant_id: str = "tenant_1",
        session_id: str | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        context = {
            "actor_agent": actor_agent,
            "acting_for_subject": {"kind": subject_kind, "id": subject_id},
            "requested_action": action,
            "tenant_id": tenant_id,
        }
        if session_id is not None:
            context["session_id"] = session_id
        if channel is not None:
            context["channel"] = channel
        if chat_id is not None:
            context["chat_id"] = chat_id
        if correlation_id is not None:
            context["correlation_id"] = correlation_id
        return context

    return _make


def _structured_content(memory_type: str, content: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(content or {})
    if memory_type == "preference":
        if "statement" not in payload:
            values = ", ".join(str(value) for value in payload.values()) if payload else "default"
            payload["statement"] = f"User prefers {values}."
        payload.setdefault("preference", payload["statement"])
        payload.setdefault("summary", payload["statement"])
        payload.setdefault("keywords", ["preference"])
    elif memory_type == "semantic_fact":
        if "statement" not in payload:
            values = ", ".join(str(value) for value in payload.values()) if payload else "default fact"
            payload["statement"] = f"Remember this fact: {values}."
        payload.setdefault("fact", payload["statement"])
        payload.setdefault("summary", payload["statement"])
        payload.setdefault("keywords", ["fact"])
    elif memory_type == "relationship":
        payload.setdefault("statement", "A relationship exists.")
        payload.setdefault("relation", "related_to")
        payload.setdefault("subject_entity", "source")
        payload.setdefault("object_entity", "target")
    elif memory_type == "procedural_rule":
        payload.setdefault("statement", "Follow the default rule.")
        payload.setdefault("rule", "default")
        payload.setdefault("action", "act")
    return payload


@pytest.fixture
def make_memory() -> Callable[..., dict[str, Any]]:
    def _make(
        *,
        memory_id: str | None = None,
        subject_id: str = "user_123",
        scope: str = "user",
        memory_type: str = "preference",
        content: dict[str, Any] | None = None,
        sensitivity: str = "internal",
        ttl_seconds: int | None = None,
        created_at: str = "2026-03-17T12:00:00Z",
        tenant_id: str = "tenant_1",
        retention_policy: str | None = None,
    ) -> dict[str, Any]:
        memory: dict[str, Any] = {
            "memory_id": memory_id or f"mem_{uuid4().hex}",
            "subject": {"kind": "user", "id": subject_id},
            "scope": scope,
            "type": memory_type,
            "content": _structured_content(memory_type, content),
            "source": {"kind": "human", "ref": "chat:test"},
            "sensitivity": sensitivity,
            "created_at": created_at,
            "backend_ref": {"tenant_id": tenant_id},
            "extensions": {},
        }
        if ttl_seconds is not None:
            memory["ttl_seconds"] = ttl_seconds
        if retention_policy is not None:
            memory["retention_policy"] = retention_policy
        return memory

    return _make


@pytest.fixture
def make_request(make_policy_context: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    def _make(*, action: str, payload: dict[str, Any], tenant_id: str = "tenant_1") -> dict[str, Any]:
        return {
            "request_id": f"req_{uuid4().hex}",
            "policy_context": make_policy_context(action=action, tenant_id=tenant_id),
            "payload": payload,
        }

    return _make
