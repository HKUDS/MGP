from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = ROOT / "sdk" / "python"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

mgp_client = importlib.import_module("mgp_client")
MGPClient = mgp_client.MGPClient
PolicyContextBuilder = mgp_client.PolicyContextBuilder


def main() -> None:
    base_url = os.getenv("MGP_BASE_URL", "http://127.0.0.1:8080")
    context = PolicyContextBuilder(actor_agent="task/demo", subject_id="user_task_demo", tenant_id="tenant_task")

    with MGPClient(base_url) as client:
        export_response = client.export_memories(
            context.build("read"),
            {"execution_mode": "async", "limit": 25},
        )
        task_id = export_response.data["task"]["task_id"]
        completed_task = client.wait_for_task(task_id, timeout_seconds=10.0, poll_interval_seconds=0.2)

    print(json.dumps({"accepted": export_response.data, "completed_task": completed_task}, indent=2))


if __name__ == "__main__":
    main()
