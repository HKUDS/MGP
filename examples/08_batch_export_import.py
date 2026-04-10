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


def main() -> None:
    base_url = os.getenv("MGP_BASE_URL", "http://127.0.0.1:8080")
    context = PolicyContextBuilder(actor_agent="interop/demo", subject_id="user_interop", tenant_id="tenant_interop")

    batch_items = [
        {
            "memory": {
                "memory_id": f"mem_batch_{uuid4().hex[:8]}",
                "subject": {"kind": "user", "id": "user_interop"},
                "scope": "user",
                "type": "preference",
                "content": {
                    "statement": "User prefers dark mode.",
                    "preference_key": "theme",
                    "preference_value": "dark",
                },
                "source": {"kind": "human", "ref": "chat:batch-1"},
                "created_at": "2026-03-28T00:00:00Z",
                "backend_ref": {"tenant_id": "tenant_interop"},
                "extensions": {},
            }
        },
        {
            "memory": {
                "memory_id": f"mem_batch_{uuid4().hex[:8]}",
                "subject": {"kind": "user", "id": "user_interop"},
                "scope": "user",
                "type": "semantic_fact",
                "content": {
                    "statement": "User likes espresso.",
                    "fact": "User likes espresso.",
                    "summary": "User likes espresso.",
                },
                "source": {"kind": "human", "ref": "chat:batch-2"},
                "created_at": "2026-03-28T00:00:00Z",
                "backend_ref": {"tenant_id": "tenant_interop"},
                "extensions": {},
            }
        },
    ]

    with MGPClient(base_url) as client:
        batch = client.write_batch(context.build("write"), batch_items)
        exported = client.export_memories(context.build("read"), {"limit": 50})
        imported = client.import_memories(
            context.build("write"),
            {"memories": (exported.data or {}).get("memories", [])},
        )

    print(json.dumps({"batch": batch.data, "export": exported.data, "import": imported.data}, indent=2))


if __name__ == "__main__":
    main()
