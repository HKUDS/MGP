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
    context = PolicyContextBuilder(
        actor_agent="nanobot/main",
        subject_id="user_profile_1",
        tenant_id="tenant_1",
    )

    memory_id = f"mem_profile_{uuid4().hex[:8]}"
    memory = {
        "memory_id": memory_id,
        "subject": {"kind": "user", "id": "user_profile_1"},
        "scope": "user",
        "type": "profile",
        "content": {"name": "Alice", "role": "Engineer"},
        "source": {"kind": "human", "ref": "chat:profile-demo"},
        "sensitivity": "internal",
        "created_at": "2026-03-17T12:00:00Z",
        "backend_ref": {"tenant_id": "tenant_1"},
        "extensions": {},
    }

    with MGPClient(base_url) as client:
        write_response = client.write_memory(context.build("write"), memory)
        get_response = client.get_memory(context.build("read"), memory_id)

    print(
        json.dumps(
            {
                "write": write_response.data,
                "get": get_response.data,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
