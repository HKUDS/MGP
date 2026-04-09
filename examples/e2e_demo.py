from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = ROOT / "sdk" / "python"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

mgp_client = importlib.import_module("mgp_client")
AuditQuery = mgp_client.AuditQuery
MGPClient = mgp_client.MGPClient
PolicyContextBuilder = mgp_client.PolicyContextBuilder
SearchQuery = mgp_client.SearchQuery


def main() -> None:
    base_url = os.getenv("MGP_BASE_URL", "http://127.0.0.1:8080")
    context = PolicyContextBuilder(
        actor_agent="nanobot/main",
        subject_id="user_e2e_1",
        tenant_id="tenant_1",
        task_id="task_e2e_1",
        task_type="demo",
    )

    memory_id = f"mem_e2e_{uuid4().hex[:8]}"
    memory = {
        "memory_id": memory_id,
        "subject": {"kind": "user", "id": "user_e2e_1"},
        "scope": "user",
        "type": "preference",
        "content": {
            "statement": "User prefers the solarized theme.",
            "preference": "solarized theme",
            "preference_key": "theme",
            "preference_value": "solarized",
            "summary": "User prefers the solarized theme.",
            "keywords": ["solarized", "theme"],
        },
        "source": {"kind": "human", "ref": "chat:e2e"},
        "sensitivity": "internal",
        "created_at": "2026-03-17T12:30:00Z",
        "backend_ref": {"tenant_id": "tenant_1"},
        "extensions": {},
    }

    with MGPClient(base_url) as client:
        write_response = client.write_memory(context.build("write"), memory)
        search_before = client.search_memory(context.build("search"), SearchQuery(query="solarized", limit=10))
        get_response = client.get_memory(context.build("read"), memory_id)
        expire_response = client.expire_memory(
            context.build("expire"),
            memory_id,
            reason="demo_expire",
        )
        search_after = client.search_memory(context.build("search"), SearchQuery(query="solarized", limit=10))
        audit_response = client.query_audit(
            context.build("read"),
            AuditQuery(action="write", target_memory_id=memory_id, limit=20),
        )

    print(
        json.dumps(
            {
                "write": write_response.data,
                "search_before_expire": search_before.data,
                "get": get_response.data,
                "expire": expire_response.data,
                "search_after_expire": search_after.data,
                "audit": audit_response.data,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
