from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = ROOT / "sdk" / "python"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from mgp_client import MGPClient, PolicyContextBuilder


def main() -> None:
    memory_url = os.getenv("MGP_MEMORY_URL", "http://127.0.0.1:8080")
    file_url = os.getenv("MGP_FILE_URL", "http://127.0.0.1:8081")

    context = PolicyContextBuilder(
        actor_agent="nanobot/main",
        subject_id="user_backend_1",
        tenant_id="tenant_1",
    )

    memory_id = f"mem_backend_{uuid4().hex[:8]}"
    memory = {
        "memory_id": memory_id,
        "subject": {"kind": "user", "id": "user_backend_1"},
        "scope": "user",
        "type": "preference",
        "content": {
            "statement": "User prefers Cursor as the editor.",
            "preference": "Cursor as the editor",
            "preference_key": "editor",
            "preference_value": "cursor",
            "summary": "User prefers Cursor as the editor.",
            "keywords": ["cursor", "editor"],
        },
        "source": {"kind": "human", "ref": "chat:backend-demo"},
        "sensitivity": "internal",
        "created_at": "2026-03-17T12:20:00Z",
        "backend_ref": {"tenant_id": "tenant_1"},
        "extensions": {},
    }

    with MGPClient(memory_url) as memory_client:
        memory_client.write_memory(context.build("write"), memory)
        memory_result = memory_client.get_memory(context.build("read"), memory_id)

    with MGPClient(file_url) as file_client:
        file_client.write_memory(context.build("write"), memory)
        file_result = file_client.get_memory(context.build("read"), memory_id)

    print(
        json.dumps(
            {
                "memory_adapter": memory_result.data["memory"],
                "file_adapter": file_result.data["memory"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
