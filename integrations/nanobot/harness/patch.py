from __future__ import annotations

import asyncio
import types
from dataclasses import dataclass, field
from typing import Any, Callable

from integrations.nanobot.sidecar import CommitOutcome, NanobotRuntimeState, RecallIntent

from .extract import extract_memory_candidate

RuntimeStateFactory = Callable[..., NanobotRuntimeState]
CandidateExtractor = Callable[..., Any]


@dataclass
class HarnessBindings:
    restore_callbacks: list[Callable[[], None]] = field(default_factory=list)

    def restore(self) -> None:
        for callback in reversed(self.restore_callbacks):
            callback()


def default_runtime_state_factory(
    *,
    workspace_id: str,
    channel: str | None,
    chat_id: str | None,
    session_key: str | None,
    sender_id: str | None,
    actor_agent: str = "nanobot/main",
) -> NanobotRuntimeState:
    resolved_channel = channel or "cli"
    resolved_chat_id = chat_id or "direct"
    resolved_session_key = session_key or f"{resolved_channel}:{resolved_chat_id}"

    if sender_id and sender_id != "user":
        user_id = sender_id
    elif resolved_chat_id and resolved_chat_id != "direct":
        user_id = resolved_chat_id
    elif ":" in resolved_session_key:
        user_id = resolved_session_key.split(":", 1)[1] or "user"
    else:
        user_id = "user"

    task_type = "process_direct" if resolved_channel == "cli" else f"channel:{resolved_channel}"
    return NanobotRuntimeState(
        actor_agent=actor_agent,
        user_id=user_id,
        session_key=resolved_session_key,
        workspace_id=workspace_id,
        channel=resolved_channel,
        chat_id=resolved_chat_id,
        task_type=task_type,
    )


def patch_context_builder(
    context_builder: Any,
    sidecar: Any,
    *,
    runtime_state_factory: RuntimeStateFactory = default_runtime_state_factory,
    recall_limit: int = 5,
    recall_types: list[str] | None = None,
    recall_scope: str = "user",
) -> Callable[[], None]:
    original_build_messages = context_builder.build_messages
    original_build_system_prompt = context_builder.build_system_prompt

    def wrapped_build_system_prompt(self: Any, skill_names: list[str] | None = None) -> str:
        prompt = original_build_system_prompt(skill_names)
        runtime = getattr(self, "_mgp_recall_runtime", None)
        intent = getattr(self, "_mgp_recall_intent", None)
        if runtime is None or intent is None:
            return prompt

        try:
            outcome = sidecar.recall(runtime, intent)
        except Exception as error:  # pragma: no cover - defensive fallback
            outcome = types.SimpleNamespace(
                mode=getattr(sidecar.config, "mode", "shadow"),
                executed=False,
                degraded=True,
                prompt_context="",
                results=[],
                request_id=None,
                error_code=type(error).__name__,
                error_message=str(error),
                fallback="nanobot-native",
                used_prompt=False,
            )
        self._mgp_last_recall = outcome
        if getattr(outcome, "used_prompt", False) and getattr(outcome, "prompt_context", ""):
            return f"{prompt}\n\n---\n\n{outcome.prompt_context}"
        return prompt

    def wrapped_build_messages(
        self: Any,
        history: list[dict[str, Any]],
        current_message: str,
        skill_names: list[str] | None = None,
        media: list[str] | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
        current_role: str = "user",
    ) -> list[dict[str, Any]]:
        if current_role != "user":
            return original_build_messages(
                history,
                current_message,
                skill_names=skill_names,
                media=media,
                channel=channel,
                chat_id=chat_id,
                current_role=current_role,
            )

        session_key = getattr(self, "_mgp_active_session_key", None) or (
            f"{channel}:{chat_id}" if channel and chat_id else "cli:direct"
        )
        sender_id = getattr(self, "_mgp_active_sender_id", None)
        runtime = runtime_state_factory(
            workspace_id=str(self.workspace),
            channel=channel,
            chat_id=chat_id,
            session_key=session_key,
            sender_id=sender_id,
        )
        intent = RecallIntent(
            query=current_message,
            limit=recall_limit,
            scope=recall_scope,
            types=list(recall_types) if recall_types is not None else None,
        )

        self._mgp_recall_runtime = runtime
        self._mgp_recall_intent = intent
        try:
            return original_build_messages(
                history,
                current_message,
                skill_names=skill_names,
                media=media,
                channel=channel,
                chat_id=chat_id,
                current_role=current_role,
            )
        finally:
            self._mgp_recall_runtime = None
            self._mgp_recall_intent = None

    context_builder.build_system_prompt = types.MethodType(wrapped_build_system_prompt, context_builder)
    context_builder.build_messages = types.MethodType(wrapped_build_messages, context_builder)

    def restore() -> None:
        context_builder.build_system_prompt = original_build_system_prompt
        context_builder.build_messages = original_build_messages

    return restore


def patch_agent_loop(
    agent_loop: Any,
    sidecar: Any,
    *,
    runtime_state_factory: RuntimeStateFactory = default_runtime_state_factory,
    candidate_extractor: CandidateExtractor = extract_memory_candidate,
    background_commit: bool = True,
) -> Callable[[], None]:
    original_process_message = agent_loop._process_message
    original_save_turn = agent_loop._save_turn
    context_builder = agent_loop.context

    if not hasattr(agent_loop, "_mgp_commit_tasks"):
        agent_loop._mgp_commit_tasks = []

    async def wrapped_process_message(
        self: Any,
        msg: Any,
        session_key: str | None = None,
        on_progress: Callable[[str], Any] | None = None,
    ) -> Any:
        context_builder._mgp_active_sender_id = getattr(msg, "sender_id", None)
        context_builder._mgp_active_session_key = session_key or getattr(msg, "session_key", None) or (
            f"{getattr(msg, 'channel', 'cli')}:{getattr(msg, 'chat_id', 'direct')}"
        )
        context_builder._mgp_active_channel = getattr(msg, "channel", None)
        context_builder._mgp_active_chat_id = getattr(msg, "chat_id", None)
        try:
            return await original_process_message(msg, session_key=session_key, on_progress=on_progress)
        finally:
            context_builder._mgp_active_sender_id = None
            context_builder._mgp_active_session_key = None
            context_builder._mgp_active_channel = None
            context_builder._mgp_active_chat_id = None

    def wrapped_save_turn(self: Any, session: Any, messages: list[dict[str, Any]], skip: int) -> None:
        original_save_turn(session, messages, skip)

        session_key = getattr(context_builder, "_mgp_active_session_key", None) or getattr(session, "key", None)
        channel = getattr(context_builder, "_mgp_active_channel", None)
        chat_id = getattr(context_builder, "_mgp_active_chat_id", None)
        sender_id = getattr(context_builder, "_mgp_active_sender_id", None)

        if session_key is None:
            return

        runtime = runtime_state_factory(
            workspace_id=str(self.workspace),
            channel=channel,
            chat_id=chat_id,
            session_key=session_key,
            sender_id=sender_id,
        )

        candidate = candidate_extractor(
            messages[skip:],
            source_ref=f"nanobot:{runtime.channel}:{runtime.session_key}",
        )
        if candidate is None:
            self._mgp_last_commit = CommitOutcome(
                mode=getattr(sidecar.config, "mode", "shadow"),
                executed=False,
                written=False,
                degraded=False,
                fallback="nanobot-native",
            )
            return

        def _run_commit() -> CommitOutcome:
            try:
                outcome = sidecar.commit(runtime, candidate)
            except Exception as error:  # pragma: no cover - defensive fallback
                outcome = CommitOutcome(
                    mode=getattr(sidecar.config, "mode", "shadow"),
                    executed=False,
                    written=False,
                    degraded=True,
                    error_code=type(error).__name__,
                    error_message=str(error),
                    fallback="nanobot-native",
                )
            self._mgp_last_commit = outcome
            return outcome

        if background_commit:
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            if running_loop and running_loop.is_running():
                task = running_loop.create_task(asyncio.to_thread(_run_commit))
                self._mgp_commit_tasks.append(task)

                def _cleanup(finished: asyncio.Task[Any]) -> None:
                    if finished in self._mgp_commit_tasks:
                        self._mgp_commit_tasks.remove(finished)
                    try:
                        self._mgp_last_commit = finished.result()
                    except Exception as error:  # pragma: no cover - defensive fallback
                        self._mgp_last_commit = CommitOutcome(
                            mode=getattr(sidecar.config, "mode", "shadow"),
                            executed=False,
                            written=False,
                            degraded=True,
                            error_code=type(error).__name__,
                            error_message=str(error),
                            fallback="nanobot-native",
                        )

                task.add_done_callback(_cleanup)
                return

        _run_commit()

    agent_loop._process_message = types.MethodType(wrapped_process_message, agent_loop)
    agent_loop._save_turn = types.MethodType(wrapped_save_turn, agent_loop)

    def restore() -> None:
        agent_loop._process_message = original_process_message
        agent_loop._save_turn = original_save_turn

    return restore


def install_nanobot_mgp_harness(
    agent_loop: Any,
    sidecar: Any,
    *,
    runtime_state_factory: RuntimeStateFactory = default_runtime_state_factory,
    candidate_extractor: CandidateExtractor = extract_memory_candidate,
    recall_limit: int = 5,
    recall_types: list[str] | None = None,
    recall_scope: str = "user",
    background_commit: bool = True,
) -> HarnessBindings:
    bindings = HarnessBindings()
    bindings.restore_callbacks.append(
        patch_context_builder(
            agent_loop.context,
            sidecar,
            runtime_state_factory=runtime_state_factory,
            recall_limit=recall_limit,
            recall_types=recall_types,
            recall_scope=recall_scope,
        )
    )
    bindings.restore_callbacks.append(
        patch_agent_loop(
            agent_loop,
            sidecar,
            runtime_state_factory=runtime_state_factory,
            candidate_extractor=candidate_extractor,
            background_commit=background_commit,
        )
    )
    return bindings


async def flush_pending_commits(agent_loop: Any) -> list[Any]:
    tasks = list(getattr(agent_loop, "_mgp_commit_tasks", []))
    if not tasks:
        return []
    return await asyncio.gather(*tasks, return_exceptions=True)
