from __future__ import annotations

import importlib
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_sidecar_module = importlib.import_module("integrations.nanobot.sidecar")
MemoryCandidate = _sidecar_module.MemoryCandidate
NanobotMGPSidecar = _sidecar_module.NanobotMGPSidecar
NanobotRuntimeState = _sidecar_module.NanobotRuntimeState
NanobotSidecarConfig = _sidecar_module.NanobotSidecarConfig
RecallIntent = _sidecar_module.RecallIntent

FIXTURES_DIR = ROOT / "integrations" / "nanobot" / "fixtures"


def load_json(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def main() -> None:
    runtime = NanobotRuntimeState.from_mapping(load_json("runtime_state.json"))
    candidate = MemoryCandidate.from_mapping(load_json("memory_candidate.json"))

    gateway_url = os.getenv("MGP_BASE_URL", "http://127.0.0.1:8080")
    mode = os.getenv("NANOBOT_MGP_MODE", "primary")
    query = os.getenv("NANOBOT_MGP_QUERY", "quiet_hours")

    sidecar = NanobotMGPSidecar(
        NanobotSidecarConfig(
            gateway_url=gateway_url,
            mode=mode,
            fail_open=True,
        )
    )

    commit_outcome = sidecar.commit(runtime, candidate)
    recall_outcome = sidecar.recall(runtime, RecallIntent(query=query, limit=5, types=["preference"]))

    print(
        json.dumps(
            {
                "config": {"gateway_url": gateway_url, "mode": mode, "query": query},
                "runtime": asdict(runtime),
                "commit_outcome": asdict(commit_outcome),
                "recall_outcome": asdict(recall_outcome),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
