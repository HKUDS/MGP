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
    base_url = os.getenv("MGP_BASE_URL", "http://127.0.0.1:8080")
    context = PolicyContextBuilder(
        actor_agent="nanobot/main",
        subject_id="user_episode_1",
        tenant_id="tenant_1",
    )

    memory = {
        "memory_id": f"mem_episode_{uuid4().hex[:8]}",
        "subject": {"kind": "user", "id": "user_episode_1"},
        "scope": "user",
        "type": "episodic_event",
        "content": {"summary": "User asked about dark mode setup in VS Code."},
        "source": {"kind": "human", "ref": "chat:episodic-demo"},
        "sensitivity": "internal",
        "created_at": "2026-03-17T12:10:00Z",
        "backend_ref": {"tenant_id": "tenant_1"},
        "extensions": {},
    }

    with MGPClient(base_url) as client:
        client.write_memory(context.build("write"), memory)
        search_response = client.search_memory(
            context.build("search"),
            SearchQuery(query="dark mode", limit=10),
        )

    print(json.dumps(search_response.data, indent=2))


if __name__ == "__main__":
    main()
