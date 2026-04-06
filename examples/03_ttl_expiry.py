from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = ROOT / "sdk" / "python"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from mgp_client import MGPClient, PolicyContextBuilder, SearchQuery


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    base_url = os.getenv("MGP_BASE_URL", "http://127.0.0.1:8080")
    context = PolicyContextBuilder(
        actor_agent="nanobot/main",
        subject_id="user_ttl_1",
        tenant_id="tenant_1",
    )

    memory = {
        "memory_id": f"mem_ttl_{uuid4().hex[:8]}",
        "subject": {"kind": "user", "id": "user_ttl_1"},
        "scope": "user",
        "type": "semantic_fact",
        "content": {
            "statement": "Remember this fact: temporary fact.",
            "fact": "temporary fact",
            "summary": "Remember this fact: temporary fact.",
            "keywords": ["temporary", "fact"],
        },
        "source": {"kind": "human", "ref": "chat:ttl-demo"},
        "sensitivity": "internal",
        "ttl_seconds": 1,
        "created_at": utc_now(),
        "backend_ref": {"tenant_id": "tenant_1"},
        "extensions": {},
    }

    with MGPClient(base_url) as client:
        client.write_memory(context.build("write"), memory)
        before = client.search_memory(context.build("search"), SearchQuery(query="temporary fact", limit=10))
        time.sleep(1.2)
        after = client.search_memory(context.build("search"), SearchQuery(query="temporary fact", limit=10))

    print(
        json.dumps(
            {
                "before_expiry_results": len(before.data["results"]),
                "after_expiry_results": len(after.data["results"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
