from __future__ import annotations

import argparse
import importlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_gateway_runtime = importlib.import_module("scripts.gateway_runtime")
allocate_port = _gateway_runtime.allocate_port
request_json = _gateway_runtime.request_json
wait_for_ready = _gateway_runtime.wait_for_ready


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test an installed mgp-gateway against the LanceDB adapter.")
    parser.add_argument(
        "--gateway-cmd",
        default="mgp-gateway",
        help="Command used to launch the gateway. Defaults to the installed mgp-gateway entrypoint.",
    )
    parser.add_argument(
        "--gateway-cwd",
        help="Optional working directory for the gateway command, useful for source-path execution.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Gateway bind host.")
    parser.add_argument("--port", type=int, default=0, help="Gateway bind port. Use 0 to auto-allocate.")
    parser.add_argument("--db-dir", help="LanceDB storage directory. Defaults to a temporary directory.")
    parser.add_argument("--table", default="memories", help="LanceDB table name.")
    parser.add_argument("--timeout", type=float, default=40.0, help="Gateway startup timeout in seconds.")
    return parser.parse_args()


def _load_dotenv(env: dict[str, str]) -> None:
    dotenv_path = ROOT / ".env"
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        env.setdefault(key, value)

def _policy_context(action: str) -> dict[str, Any]:
    return {
        "actor_agent": "lancedb-smoke",
        "acting_for_subject": {"kind": "user", "id": "user_lancedb_smoke"},
        "requested_action": action,
        "tenant_id": "tenant_lancedb_smoke",
    }


def _memory_payload(memory_id: str) -> dict[str, Any]:
    return {
        "memory_id": memory_id,
        "subject": {"kind": "user", "id": "user_lancedb_smoke"},
        "scope": "user",
        "type": "semantic_fact",
        "content": {
            "statement": "User likes matcha latte.",
            "fact": "User likes matcha latte.",
            "summary": "User likes matcha latte.",
            "keywords": ["matcha", "latte"],
        },
        "source": {"kind": "human", "ref": "chat:lancedb-smoke"},
        "created_at": "2026-04-02T00:00:00Z",
        "backend_ref": {"tenant_id": "tenant_lancedb_smoke"},
        "extensions": {},
    }


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _default_embedding_env(env: dict[str, str]) -> None:
    if env.get("MGP_LANCEDB_EMBEDDING_PROVIDER"):
        return
    env["MGP_LANCEDB_EMBEDDING_PROVIDER"] = "fake"
    env["MGP_LANCEDB_EMBEDDING_MODEL"] = "mgp-fake-embedding-v1"
    env["MGP_LANCEDB_EMBEDDING_DIM"] = "64"


def main() -> int:
    args = _parse_args()
    env = os.environ.copy()
    _load_dotenv(env)
    _default_embedding_env(env)

    port = args.port or allocate_port()
    base_url = f"http://{args.host}:{port}"

    with tempfile.TemporaryDirectory(prefix="mgp-lancedb-smoke-") as temp_dir:
        runtime_root = Path(temp_dir)
        db_dir = Path(args.db_dir).expanduser() if args.db_dir else runtime_root / "lancedb"
        db_dir.mkdir(parents=True, exist_ok=True)
        log_path = runtime_root / "gateway.log"

        env["PYTHONUNBUFFERED"] = "1"
        env["MGP_ADAPTER"] = "lancedb"
        env["MGP_GATEWAY_LOG_FORMAT"] = "plain"
        env["MGP_LANCEDB_DIR"] = str(db_dir)
        env["MGP_LANCEDB_TABLE"] = args.table
        env.setdefault("MGP_LANCEDB_ENABLE_HYBRID", "1")

        command = shlex.split(args.gateway_cmd)
        command.extend(
            [
                "--host",
                args.host,
                "--port",
                str(port),
                "--adapter",
                "lancedb",
                "--lancedb-dir",
                str(db_dir),
                "--lancedb-table",
                args.table,
            ]
        )

        with log_path.open("w+", encoding="utf-8", buffering=1) as log_handle:
            process = subprocess.Popen(
                command,
                cwd=args.gateway_cwd,
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )
            try:
                wait_for_ready(
                    base_url,
                    args.timeout,
                    is_process_running=lambda: process.poll() is None,
                )

                capabilities_status, capabilities = request_json("GET", f"{base_url}/mgp/capabilities")
                _assert(capabilities_status == 200, f"/mgp/capabilities failed: {capabilities_status} {capabilities}")
                manifest = capabilities["manifest"]
                _assert(manifest["backend_kind"] == "vector_db", "expected LanceDB manifest backend_kind=vector_db")
                _assert(manifest["capabilities"]["supports_search"] is True, "expected supports_search=true")
                _assert("semantic" in manifest["capabilities"]["search_modes"], "expected semantic search mode")

                memory_id = f"mem_lancedb_smoke_{uuid4().hex[:10]}"
                write_status, write_payload = request_json(
                    "POST",
                    f"{base_url}/mgp/write",
                    {
                        "request_id": f"req_write_{uuid4().hex}",
                        "policy_context": _policy_context("write"),
                        "payload": {"memory": _memory_payload(memory_id)},
                    },
                )
                _assert(write_status == 200, f"/mgp/write failed: {write_status} {write_payload}")
                written_memory = write_payload["data"]["memory"]
                _assert(written_memory["memory_id"] == memory_id, "written memory_id mismatch")
                _assert(written_memory["backend_ref"]["adapter"] == "lancedb", "write did not use lancedb adapter")

                search_status, search_payload = request_json(
                    "POST",
                    f"{base_url}/mgp/search",
                    {
                        "request_id": f"req_search_{uuid4().hex}",
                        "policy_context": _policy_context("search"),
                        "payload": {"query": "matcha latte", "limit": 5},
                    },
                )
                _assert(search_status == 200, f"/mgp/search failed: {search_status} {search_payload}")
                results = search_payload["data"]["results"]
                _assert(results, "expected at least one LanceDB search result")
                first_result = results[0]
                _assert(first_result["memory"]["memory_id"] == memory_id, "search returned unexpected memory")
                _assert(
                    first_result["retrieval_mode"] in {"semantic", "hybrid"},
                    f"unexpected retrieval_mode: {first_result['retrieval_mode']}",
                )

                get_status, get_payload = request_json(
                    "POST",
                    f"{base_url}/mgp/get",
                    {
                        "request_id": f"req_get_{uuid4().hex}",
                        "policy_context": _policy_context("read"),
                        "payload": {"memory_id": memory_id},
                    },
                )
                _assert(get_status == 200, f"/mgp/get failed: {get_status} {get_payload}")
                fetched_memory = get_payload["data"]["memory"]
                _assert(fetched_memory["memory_id"] == memory_id, "get returned unexpected memory")

                summary = {
                    "gateway_command": args.gateway_cmd,
                    "gateway_cwd": args.gateway_cwd,
                    "base_url": base_url,
                    "db_dir": str(db_dir),
                    "embedding_provider": env.get("MGP_LANCEDB_EMBEDDING_PROVIDER"),
                    "embedding_model": env.get("MGP_LANCEDB_EMBEDDING_MODEL"),
                    "memory_id": memory_id,
                    "retrieval_mode": first_result["retrieval_mode"],
                    "search_modes": manifest["capabilities"]["search_modes"],
                }
                print(json.dumps(summary, indent=2, ensure_ascii=False))
                return 0
            except Exception as error_value:
                log_handle.flush()
                log_handle.seek(0)
                gateway_log = log_handle.read()
                print(f"LanceDB gateway smoke test failed: {error_value}", file=sys.stderr)
                if gateway_log.strip():
                    print("\nGateway log:\n", file=sys.stderr)
                    print(gateway_log, file=sys.stderr)
                return 1
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
