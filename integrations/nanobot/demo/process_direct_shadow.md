# Nanobot `process_direct()` Shadow Demo

This note describes the lowest-risk runtime validation path against an external Nanobot checkout.

## Preconditions

- keep `MGP/` and `nanobot/` as sibling directories
- start the MGP reference gateway from `MGP/`
- use the harness shipped in `MGP/integrations/nanobot/harness/`
- start in `shadow` mode
- run with a Python 3.11+ interpreter that already has Nanobot dependencies

Recommended layout:

```text
workspace/
  MGP/
  nanobot/
```

## Suggested Validation Sequence

1. Start the MGP gateway in `MGP/`
2. Run the sidecar-only tests in `MGP/`
3. Execute the MGP harness CLI with `../nanobot` on `sys.path`
4. Validate `process_direct()` in `shadow` mode
5. Inspect MGP audit output and harness JSON output
6. Promote to `primary` only after the recall path is trustworthy

## Commands

Start the MGP gateway from the MGP repository:

```bash
make serve
```

Run the integration tests:

```bash
make test-integrations
```

Run the real Nanobot `process_direct()` harness in `shadow` mode:

```bash
../nanobot/.venv/bin/python integrations/nanobot/harness/cli.py \
  "Please remember that I prefer concise replies." \
  --mode shadow \
  --gateway-url http://127.0.0.1:8080 \
  --session cli:shadow-demo \
  --chat-id shadow-demo \
  --user-id demo-user \
  --nanobot-root ../nanobot
```

For real-provider validation, point `--config` at an isolated Nanobot config outside the repository, for example:

```bash
../nanobot/.venv/bin/python integrations/nanobot/harness/cli.py \
  "What is my reply preference token?" \
  --mode primary \
  --gateway-url http://127.0.0.1:18080 \
  --config /Users/larfii/.nanobot-mgp-openrouter/config.json \
  --session cli:recall-primary \
  --chat-id recall-primary \
  --user-id demo-user \
  --nanobot-root ../nanobot
```

## What The Harness Does

```python
from integrations.nanobot.harness import install_nanobot_mgp_harness
from integrations.nanobot.sidecar import NanobotMGPSidecar, NanobotSidecarConfig

sidecar = NanobotMGPSidecar(
    NanobotSidecarConfig(gateway_url="http://127.0.0.1:8080", mode="shadow")
)

install_nanobot_mgp_harness(
    agent_loop,
    sidecar,
    recall_limit=5,
    background_commit=True,
)
```

Internally this patch layer:

- wraps `ContextBuilder.build_messages()` to capture the current message and runtime context
- injects recall at `ContextBuilder.build_system_prompt()` time
- wraps `AgentLoop._save_turn()` to extract a minimal memory candidate and call governed commit
- fails open if recall or commit cannot reach the gateway

## What To Check

- the user still gets a normal Nanobot reply if recall fails
- `SearchMemory` failures do not stop the turn
- `WriteMemory` failures do not break session persistence
- MGP audit shows the recall and commit path
- the JSON output includes `last_recall` and `last_commit`

## When To Move To Primary

Only promote to `primary` after shadow mode proves:

- stable mapping from user/session/workspace to `policy_context`
- acceptable latency
- useful recall quality
- safe fail-open behavior
