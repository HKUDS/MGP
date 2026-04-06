from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mgp_client.types import MGPResponse

from integrations.nanobot.sidecar import (
    AsyncNanobotMGPSidecar,
    MemoryCandidate,
    NanobotRuntimeState,
    NanobotSidecarConfig,
    RecallIntent,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def load_runtime() -> NanobotRuntimeState:
    return NanobotRuntimeState.from_mapping(
        json.loads((FIXTURES_DIR / "runtime_state.json").read_text(encoding="utf-8"))
    )


def load_candidate() -> MemoryCandidate:
    return MemoryCandidate.from_mapping(
        json.loads((FIXTURES_DIR / "memory_candidate.json").read_text(encoding="utf-8"))
    )


class FakeAsyncClient:
    def __init__(self) -> None:
        self.closed = False

    async def search_memory(self, policy_context, search, request_id=None):
        return MGPResponse(
            request_id="req_search",
            status="ok",
            data={"results": [{"consumable_text": "quiet_hours=22:00-07:00"}]},
            error=None,
        )

    async def write_candidate(self, policy_context, candidate, merge_hint=None, request_id=None):
        return MGPResponse(
            request_id="req_write",
            status="ok",
            data={"memory": {"memory_id": "mem_async"}},
            error=None,
        )

    async def close(self) -> None:
        self.closed = True


def test_async_sidecar_recall_and_commit() -> None:
    fake = FakeAsyncClient()
    sidecar = AsyncNanobotMGPSidecar(
        NanobotSidecarConfig(gateway_url="http://mgp.invalid", mode="primary"),
        client_factory=lambda base_url, timeout, headers: fake,
    )

    async def _run():
        recall = await sidecar.recall(load_runtime(), RecallIntent(query="quiet hours"))
        commit = await sidecar.commit(load_runtime(), load_candidate())
        await sidecar.close()
        return recall, commit

    recall, commit = asyncio.run(_run())
    assert recall.used_prompt is True
    assert commit.memory_id == "mem_async"
    assert fake.closed is True
