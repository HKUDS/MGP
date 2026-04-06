from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = ROOT / "sdk" / "python"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from integrations.nanobot.sidecar import MemoryCandidate, NanobotMGPSidecar, NanobotRuntimeState, NanobotSidecarConfig, RecallIntent


def main() -> None:
    gateway_url = os.getenv("MGP_BASE_URL", "http://127.0.0.1:8080")
    sidecar = NanobotMGPSidecar(
        NanobotSidecarConfig(gateway_url=gateway_url, mode="shadow", reuse_client=True),
    )
    runtime = NanobotRuntimeState(
        actor_agent="nanobot/main",
        user_id="user_shadow_demo",
        session_key="cli:user_shadow_demo",
        workspace_id="workspace_demo",
        channel="cli",
        tenant_id="tenant_shadow",
        task_type="process_direct",
    )
    recall = sidecar.recall(runtime, RecallIntent(query="theme preference"))
    commit = sidecar.commit(
        runtime,
        MemoryCandidate(
            content={
                "statement": "User prefers dark mode.",
                "preference_key": "theme",
                "preference_value": "dark",
            },
            memory_type="preference",
            source_ref="nanobot:shadow-demo",
        ),
    )
    sidecar.close()

    print(json.dumps({"recall": recall.__dict__, "commit": commit.__dict__}, indent=2))


if __name__ == "__main__":
    main()
