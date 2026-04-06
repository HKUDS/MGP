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
    base_url = os.getenv("MGP_BASE_URL", "http://127.0.0.1:8080")
    context = PolicyContextBuilder(actor_agent="sdk-only/demo", subject_id="user_sdk_only", tenant_id="tenant_sdk")
    memory_id = f"mem_sdk_only_{uuid4().hex[:8]}"

    with MGPClient(base_url) as client:
        capabilities = client.get_capabilities()
        write = client.write_memory(
            context.build("write"),
            {
                "memory_id": memory_id,
                "subject": {"kind": "user", "id": "user_sdk_only"},
                "scope": "user",
                "type": "preference",
                "content": {
                    "statement": "User prefers concise replies.",
                    "preference_key": "response_style",
                    "preference_value": "concise",
                },
                "source": {"kind": "human", "ref": "chat:sdk-only"},
                "created_at": "2026-03-28T00:00:00Z",
                "backend_ref": {"tenant_id": "tenant_sdk"},
                "extensions": {},
            },
        )
        get_result = client.get_memory(context.build("read"), memory_id)

    print(json.dumps({"capabilities": capabilities, "write": write.data, "get": get_result.data}, indent=2))


if __name__ == "__main__":
    main()
