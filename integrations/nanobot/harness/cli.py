from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_harness_module = importlib.import_module("integrations.nanobot.harness")
default_runtime_state_factory = _harness_module.default_runtime_state_factory
flush_pending_commits = _harness_module.flush_pending_commits
install_nanobot_mgp_harness = _harness_module.install_nanobot_mgp_harness

_sidecar_module = importlib.import_module("integrations.nanobot.sidecar")
NanobotMGPSidecar = _sidecar_module.NanobotMGPSidecar
NanobotSidecarConfig = _sidecar_module.NanobotSidecarConfig

DEFAULT_NANOBOT_ROOT = ROOT.parent / "nanobot"


def _serialize(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return str(value)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Nanobot with the MGP harness around process_direct().")
    parser.add_argument("message", help="Message to send through Nanobot process_direct().")
    parser.add_argument("--config", help="Nanobot config path.", default=None)
    parser.add_argument("--workspace", help="Override Nanobot workspace.", default=None)
    parser.add_argument("--session", help="Nanobot session key.", default="cli:direct")
    parser.add_argument("--channel", help="Nanobot channel name.", default="cli")
    parser.add_argument("--chat-id", help="Nanobot chat id.", default="direct")
    parser.add_argument("--user-id", help="Override MGP subject id for cross-session testing.", default=None)
    parser.add_argument("--actor-agent", help="Override actor agent identifier.", default="nanobot/main")
    parser.add_argument("--tenant-id", help="Override MGP tenant id.", default=None)
    parser.add_argument("--task-type", help="Override task type sent in policy_context.", default=None)
    parser.add_argument("--risk-level", help="Override risk level sent in policy_context.", default=None)
    parser.add_argument("--mode", choices=["off", "shadow", "primary"], default=os.getenv("NANOBOT_MGP_MODE", "shadow"))
    parser.add_argument("--gateway-url", default=os.getenv("MGP_BASE_URL", "http://127.0.0.1:8080"))
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--recall-limit", type=int, default=5)
    parser.add_argument("--recall-type", action="append", dest="recall_types", default=[])
    parser.add_argument("--sync-commit", action="store_true", help="Run commit inline instead of as a background task.")
    parser.add_argument("--fail-closed", action="store_true", help="Raise if the sidecar cannot reach the gateway.")
    parser.add_argument("--nanobot-root", default=os.getenv("NANOBOT_ROOT", str(DEFAULT_NANOBOT_ROOT)))
    return parser.parse_args()


def _ensure_runtime(nanobot_root: Path) -> None:
    if sys.version_info < (3, 11):
        raise SystemExit(
            "Nanobot harness requires Python 3.11+ because the external Nanobot runtime targets 3.11+. "
            "Run this command with Nanobot's virtualenv or another Python 3.11 interpreter."
        )
    if not nanobot_root.exists():
        raise SystemExit(f"Nanobot checkout not found: {nanobot_root}")

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(nanobot_root) not in sys.path:
        sys.path.insert(0, str(nanobot_root))


def _build_runtime_state_factory(args: argparse.Namespace):
    def _factory(
        *,
        workspace_id: str,
        channel: str | None,
        chat_id: str | None,
        session_key: str | None,
        sender_id: str | None,
    ):
        runtime = default_runtime_state_factory(
            workspace_id=workspace_id,
            channel=channel,
            chat_id=chat_id,
            session_key=session_key,
            sender_id=sender_id,
            actor_agent=args.actor_agent,
        )
        if args.user_id:
            runtime.user_id = args.user_id
        if args.tenant_id:
            runtime.tenant_id = args.tenant_id
        if args.task_type:
            runtime.task_type = args.task_type
        if args.risk_level:
            runtime.risk_level = args.risk_level
        return runtime

    return _factory


async def _run(args: argparse.Namespace) -> int:
    nanobot_root = Path(args.nanobot_root).expanduser().resolve()
    _ensure_runtime(nanobot_root)

    from nanobot.agent.loop import AgentLoop
    from nanobot.bus.queue import MessageBus
    from nanobot.cli.commands import _load_runtime_config, _make_provider
    from nanobot.config.paths import get_cron_dir
    from nanobot.cron.service import CronService
    from nanobot.utils.helpers import sync_workspace_templates

    config = _load_runtime_config(args.config, args.workspace)
    sync_workspace_templates(config.workspace_path)

    bus = MessageBus()
    provider = _make_provider(config)
    cron = CronService(get_cron_dir() / "jobs.json")
    agent_loop = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=config.agents.defaults.model,
        max_iterations=config.agents.defaults.max_tool_iterations,
        context_window_tokens=config.agents.defaults.context_window_tokens,
        web_search_config=config.tools.web.search,
        web_proxy=config.tools.web.proxy or None,
        exec_config=config.tools.exec,
        cron_service=cron,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        mcp_servers=config.tools.mcp_servers,
        channels_config=config.channels,
    )

    sidecar = NanobotMGPSidecar(
        NanobotSidecarConfig(
            gateway_url=args.gateway_url,
            mode=args.mode,
            timeout=args.timeout,
            fail_open=not args.fail_closed,
        )
    )
    runtime_state_factory = _build_runtime_state_factory(args)
    bindings = install_nanobot_mgp_harness(
        agent_loop,
        sidecar,
        runtime_state_factory=runtime_state_factory,
        recall_limit=args.recall_limit,
        recall_types=args.recall_types or None,
        background_commit=not args.sync_commit,
    )

    try:
        response = await agent_loop.process_direct(
            args.message,
            session_key=args.session,
            channel=args.channel,
            chat_id=args.chat_id,
        )
        await flush_pending_commits(agent_loop)
        payload = {
            "nanobot_root": str(nanobot_root),
            "workspace": str(config.workspace_path),
            "mode": args.mode,
            "gateway_url": args.gateway_url,
            "session": args.session,
            "channel": args.channel,
            "chat_id": args.chat_id,
            "user_id": args.user_id,
            "response": response,
            "last_recall": _serialize(getattr(agent_loop.context, "_mgp_last_recall", None)),
            "last_commit": _serialize(getattr(agent_loop, "_mgp_last_commit", None)),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    finally:
        bindings.restore()
        await agent_loop.close_mcp()


def main() -> int:
    args = _parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
