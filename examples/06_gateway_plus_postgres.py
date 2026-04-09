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
MGPClient = mgp_client.MGPClient
PolicyContextBuilder = mgp_client.PolicyContextBuilder
SearchQuery = mgp_client.SearchQuery


def main() -> None:
    base_url = os.getenv("MGP_POSTGRES_URL", "http://127.0.0.1:8080")
    context = PolicyContextBuilder(actor_agent="postgres/demo", subject_id="user_postgres_demo", tenant_id="tenant_pg")
    memory_id = f"mem_pg_{uuid4().hex[:8]}"

    with MGPClient(base_url) as client:
        capabilities = client.get_capabilities()
        write = client.write_memory(
            context.build("write"),
            {
                "memory_id": memory_id,
                "subject": {"kind": "user", "id": "user_postgres_demo"},
                "scope": "user",
                "type": "semantic_fact",
                "content": {
                    "statement": "User works from Berlin.",
                    "fact": "User works from Berlin.",
                    "summary": "User works from Berlin.",
                    "keywords": ["berlin", "work"],
                },
                "source": {"kind": "human", "ref": "chat:postgres"},
                "created_at": "2026-03-28T00:00:00Z",
                "backend_ref": {"tenant_id": "tenant_pg"},
                "extensions": {},
            },
        )
        search = client.search_memory(
            context.build("search"),
            SearchQuery(query_text="Where does the user work from?", keywords=["berlin"], limit=5),
        )

    print(json.dumps({"capabilities": capabilities, "write": write.data, "search": search.data}, indent=2))


if __name__ == "__main__":
    main()
