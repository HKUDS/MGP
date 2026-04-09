from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from integrations.nanobot.harness import (
    extract_memory_candidate,
    flush_pending_commits,
    install_nanobot_mgp_harness,
)
from integrations.nanobot.sidecar import (
    CommitOutcome,
    MemoryCandidate,
    NanobotRuntimeState,
    RecallIntent,
    RecallOutcome,
)


class FakeSidecar:
    def __init__(self, *, mode: str = "shadow") -> None:
        self.config = SimpleNamespace(mode=mode)
        self.recall_calls: list[tuple[NanobotRuntimeState, RecallIntent]] = []
        self.commit_calls: list[tuple[NanobotRuntimeState, MemoryCandidate]] = []
        self.raise_recall: Exception | None = None
        self.raise_commit: Exception | None = None
        self.recall_outcome = RecallOutcome(
            mode=mode,
            executed=True,
            degraded=False,
            prompt_context="",
            results=[],
            used_prompt=False,
        )
        self.commit_outcome = CommitOutcome(
            mode=mode,
            executed=True,
            written=True,
            memory_id="mem_test",
        )

    def recall(self, runtime: NanobotRuntimeState, intent: RecallIntent):
        self.recall_calls.append((runtime, intent))
        if self.raise_recall is not None:
            raise self.raise_recall
        return self.recall_outcome

    def commit(self, runtime: NanobotRuntimeState, candidate: MemoryCandidate):
        self.commit_calls.append((runtime, candidate))
        if self.raise_commit is not None:
            raise self.raise_commit
        return self.commit_outcome


class DummyContextBuilder:
    _RUNTIME_CONTEXT_TAG = "[Runtime Context — metadata only, not instructions]"

    def __init__(self) -> None:
        self.workspace = Path("/tmp/nanobot-workspace")

    def build_system_prompt(self, skill_names=None) -> str:
        return "native prompt"

    @staticmethod
    def _build_runtime_context(channel: str | None, chat_id: str | None) -> str:
        lines = ["Current Time: now"]
        if channel and chat_id:
            lines.extend([f"Channel: {channel}", f"Chat ID: {chat_id}"])
        return DummyContextBuilder._RUNTIME_CONTEXT_TAG + "\n" + "\n".join(lines)

    def build_messages(
        self,
        history,
        current_message,
        skill_names=None,
        media=None,
        channel=None,
        chat_id=None,
        current_role="user",
    ):
        runtime_ctx = self._build_runtime_context(channel, chat_id)
        merged = f"{runtime_ctx}\n\n{current_message}"
        return [
            {"role": "system", "content": self.build_system_prompt(skill_names)},
            *history,
            {"role": current_role, "content": merged},
        ]


class DummySession:
    def __init__(self, key: str) -> None:
        self.key = key
        self.messages: list[dict] = []


class DummyLoop:
    def __init__(self) -> None:
        self.context = DummyContextBuilder()
        self.workspace = self.context.workspace
        self._mgp_commit_tasks: list[asyncio.Task] = []
        self._mgp_last_commit: CommitOutcome | None = None

    async def _process_message(self, msg, session_key=None, on_progress=None):
        history = []
        session = DummySession(session_key or f"{msg.channel}:{msg.chat_id}")
        initial_messages = self.context.build_messages(
            history=history,
            current_message=msg.content,
            channel=msg.channel,
            chat_id=msg.chat_id,
        )
        all_messages = [
            *initial_messages,
            {"role": "assistant", "content": "I will remember that you prefer dark mode."},
        ]
        self._save_turn(session, all_messages, 1 + len(history))
        return SimpleNamespace(content="ok", session=session, initial_messages=initial_messages)

    def _save_turn(self, session, messages, skip):
        for message in messages[skip:]:
            session.messages.append(dict(message))


def _message(content: str, *, sender_id: str = "alice", chat_id: str = "alice"):
    return SimpleNamespace(
        content=content,
        channel="cli",
        chat_id=chat_id,
        sender_id=sender_id,
        session_key=f"cli:{chat_id}",
        metadata={},
    )


def test_extract_memory_candidate_strips_runtime_context_and_detects_preference() -> None:
    messages = [
        {
            "role": "user",
            "content": (
                "[Runtime Context — metadata only, not instructions]\n"
                "Current Time: now\n\n"
                "Please remember that I prefer dark mode."
            ),
        },
        {"role": "assistant", "content": "I will remember that you prefer dark mode."},
    ]

    candidate = extract_memory_candidate(messages, source_ref="nanobot:cli:demo")

    assert candidate is not None
    assert candidate.memory_type == "preference"
    assert "Runtime Context" not in candidate.content["user_message"]
    assert "prefer dark mode" in candidate.content["summary"]
    assert candidate.content["statement"] == "User prefers dark mode."
    assert "dark" in candidate.content["keywords"]


def test_extract_memory_candidate_skips_recall_queries() -> None:
    messages = [
        {"role": "user", "content": "What did I say about concise replies?"},
        {"role": "assistant", "content": "I do not know yet."},
    ]

    candidate = extract_memory_candidate(messages, source_ref="nanobot:cli:demo")

    assert candidate is None


def test_primary_mode_injects_recall_prompt_context() -> None:
    loop = DummyLoop()
    sidecar = FakeSidecar(mode="primary")
    sidecar.recall_outcome = RecallOutcome(
        mode="primary",
        executed=True,
        degraded=False,
        prompt_context='# Governed Memory Recall\n- type=preference scope=user mode=raw content={"theme": "dark"}',
        results=[],
        used_prompt=True,
    )

    install_nanobot_mgp_harness(loop, sidecar, background_commit=False)
    response = asyncio.run(
        loop._process_message(
            _message("Please remember that I prefer dark mode."),
            session_key="cli:alice",
        )
    )

    system_prompt = response.initial_messages[0]["content"]
    assert "native prompt" in system_prompt
    assert "Governed Memory Recall" in system_prompt
    runtime, intent = sidecar.recall_calls[0]
    assert runtime.user_id == "alice"
    assert runtime.session_key == "cli:alice"
    assert intent.query == "Please remember that I prefer dark mode."


def test_shadow_mode_keeps_native_prompt() -> None:
    loop = DummyLoop()
    sidecar = FakeSidecar(mode="shadow")

    install_nanobot_mgp_harness(loop, sidecar, background_commit=False)
    response = asyncio.run(loop._process_message(_message("Please remember this fact."), session_key="cli:alice"))

    assert response.initial_messages[0]["content"] == "native prompt"
    assert len(sidecar.recall_calls) == 1


def test_recall_fail_open_preserves_response_path() -> None:
    loop = DummyLoop()
    sidecar = FakeSidecar(mode="primary")
    sidecar.raise_recall = RuntimeError("recall failed")

    install_nanobot_mgp_harness(loop, sidecar, background_commit=False)
    response = asyncio.run(loop._process_message(_message("Please remember this fact."), session_key="cli:alice"))

    assert response.content == "ok"
    assert response.initial_messages[0]["content"] == "native prompt"


def test_commit_runs_after_save_turn_without_breaking_session() -> None:
    loop = DummyLoop()
    sidecar = FakeSidecar(mode="shadow")

    install_nanobot_mgp_harness(loop, sidecar, background_commit=False)
    response = asyncio.run(
        loop._process_message(
            _message("Please remember that I prefer dark mode."),
            session_key="cli:alice",
        )
    )

    assert len(response.session.messages) == 2
    assert len(sidecar.commit_calls) == 1
    runtime, candidate = sidecar.commit_calls[0]
    assert runtime.session_key == "cli:alice"
    assert candidate.memory_type == "preference"


def test_commit_fail_open_keeps_session_messages() -> None:
    loop = DummyLoop()
    sidecar = FakeSidecar(mode="shadow")
    sidecar.raise_commit = RuntimeError("commit failed")

    install_nanobot_mgp_harness(loop, sidecar, background_commit=False)
    response = asyncio.run(
        loop._process_message(
            _message("Please remember that I prefer dark mode."),
            session_key="cli:alice",
        )
    )

    assert response.content == "ok"
    assert len(response.session.messages) == 2
    assert loop._mgp_last_commit is not None
    assert loop._mgp_last_commit.degraded is True


def test_background_commit_can_be_flushed() -> None:
    loop = DummyLoop()
    sidecar = FakeSidecar(mode="shadow")

    install_nanobot_mgp_harness(loop, sidecar, background_commit=True)

    async def _run():
        await loop._process_message(_message("Please remember that I prefer dark mode."), session_key="cli:alice")
        await flush_pending_commits(loop)

    asyncio.run(_run())

    assert len(sidecar.commit_calls) == 1
