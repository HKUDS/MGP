# Nanobot Reference Integration

This directory contains the reference integration assets for connecting MGP to the [Nanobot](https://github.com/HKUDS/nanobot) agent runtime.

Use this README together with [`docs/sidecar-integration.md`](../../docs/sidecar-integration.md): that page explains the generic sidecar pattern, while this directory is the concrete repository reference path.

> Runtime-side wiring details (skill, tool schema, AgentLoop hooks, config keys) live in nanobot's [`nanobot/agent/mgp/README.md`](https://github.com/HKUDS/nanobot/blob/main/nanobot/agent/mgp/README.md).

## Why Nanobot

Nanobot is a useful integration target because it already has the runtime shape MGP needs to validate:

- it is a real agent host
- it already speaks MCP for tools and resources
- it has a concrete native memory system, but no peer protocol for governed memory

This makes it a good proving ground for MGP as a runtime-facing protocol.

---

## Two Integration Paths

There are two supported ways to connect Nanobot to an MGP gateway. They share the same gateway and the same wire protocol; what differs is **where the integration code lives** and **how the rollout is staged**.

| | Path A — `nanobot[mgp]` extra | Path B — harness in this directory |
| --- | --- | --- |
| Audience | End users running Nanobot in production | MGP maintainers / CI validating against an unmodified runtime |
| Code location | Lives inside Nanobot (`nanobot/agent/mgp/`) | Patches Nanobot at runtime via `harness/patch.py` |
| Recall trigger | Always-on `recall_memory` tool the agent calls when needed | Auto-injected into the system prompt in `primary` mode |
| Commit trigger | Automatic after Consolidator / Dream produce summaries | Best-effort after `_save_turn` in shadow / primary mode |
| Rollout knob | `mgp.enable_*_commit` flags + per-call decisions | `mode = off / shadow / primary` |
| Install | `pip install "nanobot[mgp]"` | This repo's checkout + harness CLI against a sibling `../nanobot/` |
| Status | Production-ready (default once `mgp.enabled = true`) | Reference / validation only |

If you are deploying Nanobot, choose **Path A**. If you are developing MGP and want to validate against unmodified Nanobot HEAD, use **Path B**.

```mermaid
flowchart LR
  subgraph PathA [Path A: nanobot mgp extra]
    NbA[Nanobot AgentLoop] --> SkillA[mgp-memory skill]
    SkillA --> ToolA[recall_memory tool]
    ToolA --> ClientA[mgp_client AsyncMGPClient]
    NbA --> ConsoA[Consolidator and Dream]
    ConsoA --> SidecarA[in-tree AsyncMGPSidecar]
    SidecarA --> ClientA
  end
  subgraph PathB [Path B: harness]
    NbB[stock Nanobot] --> Patch[harness patch.py]
    Patch --> SidecarB[NanobotMgpSidecar in this directory]
    SidecarB --> ClientB[mgp_client]
  end
  ClientA --> Gateway[MGP gateway]
  ClientB --> Gateway
  Gateway --> Adapter[backend adapter]
  Adapter --> Storage[memory storage]
  Gateway --> Audit[audit sink]
```

---

## What Lives Here

| Path | Purpose |
| --- | --- |
| `sidecar/` | Reference sidecar implementation used by Path B (`service.py` sync, `async_service.py` async, `mappers.py`, `models.py`, `telemetry.py`, `_core.py`) |
| `harness/` | Runtime patch layer and CLI for Path B (`patch.py`, `cli.py`, `extract.py`) |
| `tests/` | Sidecar mapping, mode behavior, and fail-open tests |
| `demo/` | `simulated_payload_demo.py` and `process_direct_shadow.md` validation notes |

These assets are reference-grade. Path A consumers do **not** import them; they install `nanobot[mgp]` and let the in-tree integration handle everything.

---

## Path A — `nanobot[mgp]` (Production Path)

### Quickstart

```bash
# 1. Install Nanobot with the MGP extra (~one extra dep: mgp-client)
pip install "nanobot[mgp]"

# 2. Install the gateway with your chosen adapter (postgres shown here)
pip install "mgp-gateway[postgres]>=0.1.1"

# 3. Run a Postgres for the gateway
docker run -d --name mgp-pg \
  -e POSTGRES_USER=mgp -e POSTGRES_PASSWORD=mgp -e POSTGRES_DB=mgp \
  -p 5432:5432 postgres:16

# 4. Start the gateway
MGP_ADAPTER=postgres \
MGP_POSTGRES_DSN='postgresql://mgp:mgp@127.0.0.1:5432/mgp' \
mgp-gateway
```

Enable MGP in your Nanobot config:

```yaml
agents:
  defaults:
    mgp:
      enabled: true
      gateway_url: "http://127.0.0.1:8080"
      # Recommended: pin a stable subject id so Dream-extracted [USER] facts
      # land where CLI/channel sessions can find them. Without this the
      # subject defaults to getpass.getuser() (the OS login).
      default_user_id: "alice"
```

Restart Nanobot. Use the slash command `/mgp-status` to verify the connection. Ask the agent something that references past context (e.g. "what's my preferred indentation?") to see it call `recall_memory`.

For the full nanobot-side reference (config keys, what gets written, opt-out flags), see [`nanobot/agent/mgp/README.md`](https://github.com/HKUDS/nanobot/blob/main/nanobot/agent/mgp/README.md).

### Memory Type Mapping (Nanobot to MGP spec)

Nanobot's Dream produces three tagged categories. The integration maps them onto canonical MGP `(scope, memory_type)` pairs:

| Dream tag  | MGP scope | MGP memory type | Rationale |
| ---------- | --------- | --------------- | --------- |
| `[USER]`   | `user`    | `preference`    | User-specific facts (location, language, taste) |
| `[MEMORY]` | `agent`   | `semantic_fact` | Stable shared knowledge surfaced by Dream |
| `[SOUL]`   | `agent`   | `profile`       | Agent identity / persona facts |

Memory types must align with the spec's `supported_memory_types` set (`profile / preference / episodic_event / semantic_fact / procedural_rule / relationship / checkpoint_pointer / artifact_summary`). Anything else is rejected with `MGP_INVALID_OBJECT`.

> The earlier `identity` label is **not** a valid MGP type. Use `profile`. The Nanobot integration handles this mapping internally; downstream callers building their own commit pipelines must do the same.

### Subject (`user_id`) Derivation

The MGP subject under which memories are written and searched is resolved per call from routing context, in this priority:

1. `sender_id` from the inbound message (e.g. group-chat member id from Telegram / Discord / Slack — a real per-person identifier).
2. `chat_id` if it is not a synthetic placeholder (`direct`, `dream`, `user`).
3. `mgp.default_user_id` from your config.
4. `getpass.getuser()` (the OS login).

**Why this matters.** Dream runs at workspace scope and uses the synthetic `chat_id="dream"`. Without a configured `default_user_id`, every Dream `[USER]` fact would land under subject `"dream"` (or `getpass.getuser()`), not under the subject your CLI/channel session uses for recall — making those facts effectively unreachable. **Always set `default_user_id` for SDK-only deployments and any setup where multiple Nanobot instances should share one subject.**

For group chats, the inbound `sender_id` is plumbed all the way down to the `recall_memory` tool, so each member gets their own user-scoped memory island even though the `chat_id` is shared.

### Operational Notes

- **Fail-open by default.** Every MGP call (`/mgp/search`, `/mgp/write`) is wrapped — HTTP timeouts, gateway 5xx, schema validation errors are swallowed and surfaced as `[recall_memory degraded: <code>]` to the agent. The conversation never dies because of an MGP problem. Set `mgp.fail_open: false` only if you want hard failures.
- **Commit channels are independent.** `mgp.enable_consolidator_commit` (Consolidator bullets) and `mgp.enable_dream_commit` (Dream Phase-1 tags) toggle independently. The `recall_memory` tool stays available regardless.
- **`/mgp-status` slash command** reports `enabled`, `gateway_url`, last recall (query, latency, error code), and the last 32 commit outcomes. When MGP is disabled, it returns a one-liner.
- **Air-gap when disabled.** `mgp.enabled: false` means `mgp_client` is never imported and no gateway traffic is generated. Behavior is byte-identical to a build without the extra installed.

---

## Path B — Harness (Validation Path)

This path runs **stock unmodified Nanobot** and patches MGP into it at runtime. Useful for MGP CI, for validating against Nanobot HEAD before a fork PR lands, and for staged rollouts where you want the classic `off → shadow → primary` ladder.

### Architecture

```mermaid
flowchart LR
  UserMsg[UserMessage] --> NanobotLoop[stock NanobotRuntime]
  NanobotLoop --> Patch[harness patch.py]
  Patch --> SidecarLocal[NanobotMgpSidecar]
  SidecarLocal --> MgpGateway[MGP gateway]
  MgpGateway --> PolicyHook[policy hook]
  PolicyHook --> AdapterLayer[adapter layer]
  AdapterLayer --> MemoryBackend[memory backend]
  MgpGateway --> AuditSink[audit sink]
  SidecarLocal --> NanobotLoop
```

The harness patches two Nanobot hooks:

- `ContextBuilder.build_system_prompt()` — appends governed recall output to the system prompt when mode is `primary`.
- `AgentLoop._save_turn()` — triggers best-effort governed commit after the native turn-save path runs.

It also wraps `build_messages()` and `_process_message()` so the current message, sender, session key, and channel metadata are available when building MGP requests.

### Policy Context Mapping

The sidecar maps Nanobot runtime state into the MGP policy context envelope:

| Nanobot source | MGP field |
| --- | --- |
| agent identity | `actor_agent` |
| current user or chat subject | `acting_for_subject` |
| session key | `task_id` |
| invocation kind (`process_direct`, channel turn) | `task_type` |
| workspace or explicit tenant | `tenant_id` |

Notes:

- The Nanobot session key is mapped to `task_id` as a runtime execution correlation.
- This is distinct from the protocol async task identifier returned by `/mgp/tasks/get`.
- Keep `session_id` available separately if you later need explicit conversation identity in policy context.

### Rollout Modes

| Mode      | Behavior |
| --------- | -------- |
| `off`     | No MGP calls. Nanobot behavior is unchanged. |
| `shadow`  | Call MGP, but do **not** inject recall results into the prompt. Useful for measuring quality and load before flipping the switch. |
| `primary` | Call MGP **and** inject usable recall results into the prompt. |

Safety rules (enforced regardless of mode):

- Fail open when the sidecar or gateway is unavailable.
- Never block a reply because `SearchMemory` fails.
- Never break session persistence because `WriteMemory` fails.
- The sidecar supports reusable gateway clients for long-running processes — call `sidecar.close()` during runtime shutdown if `reuse_client = True`.

### Validation Ladder

```mermaid
flowchart TD
  SimInput[SimulatedPayload] --> SidecarOnly[SidecarOnlyTest]
  SidecarOnly --> DirectPath[ProcessDirectPoC]
  DirectPath --> ShadowMode[ShadowModeValidation]
  ShadowMode --> PrimaryMode[PrimaryModeE2E]
```

1. **Sidecar-only tests** — validate mapping and fail-open behavior without Nanobot.
2. **`process_direct()` PoC** — validate against a real Nanobot invocation.
3. **Shadow mode** — call MGP in production but do not inject recall.
4. **Primary mode** — allow MGP recall to influence prompts.

### Quickstart

From the MGP repo root:

```bash
make install
make serve              # starts the reference gateway on :8080
make test-integrations  # sidecar unit tests + harness mapping tests
```

Run the simulated payload demo against the local gateway:

```bash
MGP_BASE_URL=http://127.0.0.1:8080 \
  ./.venv/bin/python integrations/nanobot/demo/simulated_payload_demo.py
```

For real runtime validation, keep Nanobot in a sibling checkout (`../nanobot/`) and run the harness CLI with Nanobot's own Python 3.11+ environment:

```bash
../nanobot/.venv/bin/python integrations/nanobot/harness/cli.py \
  "Please remember that I prefer concise replies." \
  --mode shadow \
  --gateway-url http://127.0.0.1:8080 \
  --user-id demo-user \
  --nanobot-root ../nanobot
```

Notes:

- Use Nanobot's own virtualenv or another Python 3.11+ environment.
- `shadow` is the default rollout mode; move to `primary` only after recall quality is acceptable.
- Prefer `--user-id` for cross-session recall tests so subject identity is stable.

### Real Provider Validation

Use an isolated Nanobot config outside the repository to keep credentials out of git:

- Config under `~/.nanobot-mgp-openrouter/`.
- `providers.openrouter.apiKey` set in that external config.
- `agents.defaults.provider = "openrouter"`.

For the full validation sequence, see [`demo/process_direct_shadow.md`](demo/process_direct_shadow.md).

### Repository Boundary

MGP keeps the integration assets in-tree under `integrations/nanobot/`. Nanobot stays as an external checkout in a sibling directory.

Recommended local layout:

```text
workspace/
  MGP/
  nanobot/
```

Rules:

- do not copy the Nanobot source tree into MGP
- do not add Nanobot as a subtree or vendor directory
- keep Nanobot as the external runtime under test

---

## Gateway-Side Configuration (applies to both paths)

Adapter selection lives **on the MGP gateway**, not in `nanobot.yaml`. Nanobot only needs to know `gateway_url` (and optionally `api_key`).

### Adapters

| Adapter      | Install                                            | Required environment |
| ------------ | -------------------------------------------------- | -------------------- |
| `postgres`   | `pip install "mgp-gateway[postgres]>=0.1.1"`       | `MGP_ADAPTER=postgres`, `MGP_POSTGRES_DSN=...` |
| `oceanbase`  | `pip install "mgp-gateway[oceanbase]>=0.1.1"`      | `MGP_ADAPTER=oceanbase`, **either** `MGP_OCEANBASE_DSN=...` **or** the discrete tuple `MGP_OCEANBASE_URI` + `MGP_OCEANBASE_USER` + `MGP_OCEANBASE_PASSWORD` + `MGP_OCEANBASE_DATABASE` (+ optional `MGP_OCEANBASE_TENANT`) |
| `lancedb`    | `pip install "mgp-gateway[lancedb]>=0.1.1"`        | `MGP_ADAPTER=lancedb`, `MGP_LANCEDB_DIR=...`, `MGP_LANCEDB_EMBEDDING_PROVIDER`, `MGP_LANCEDB_EMBEDDING_MODEL`, `MGP_LANCEDB_EMBEDDING_API_KEY` (+ optional `MGP_LANCEDB_EMBEDDING_BASE_URL`, `MGP_LANCEDB_EMBEDDING_DIM`, `MGP_LANCEDB_TABLE`, `MGP_LANCEDB_ENABLE_HYBRID`) |
| `mem0`       | `pip install mem0ai`                               | `MGP_ADAPTER=mem0`, `MGP_MEM0_API_KEY=...` (+ optional `MGP_MEM0_ORG_ID`, `MGP_MEM0_PROJECT_ID`, `MGP_MEM0_APP_ID`, `MGP_MEM0_ENABLE_GRAPH=true\|false`) |
| `zep`        | `pip install zep-cloud`                            | `MGP_ADAPTER=zep`, `MGP_ZEP_API_KEY=...` (+ optional `MGP_ZEP_BASE_URL`, `MGP_ZEP_GRAPH_USER_ID`, `MGP_ZEP_RERANKER`, `MGP_ZEP_RETURN_CONTEXT`, `MGP_ZEP_IGNORE_ROLES`) |

Reference adapters (`memory`, `file`, `graph`) are for protocol verification — do not use in production.

> **Note on OceanBase.** Although `pyobvector` is the SDK used, the current `oceanbase` adapter performs purely **lexical** search; the vector index is not yet wired through. Retrieval characteristics are close to `postgres`. Track the upstream adapter for vector search support if cross-language / synonym matching is a hard requirement.

### Authentication

```bash
export MGP_GATEWAY_AUTH_MODE=api_key   # off / api_key / bearer
export MGP_GATEWAY_API_KEY=secret-...  # for api_key mode
# export MGP_GATEWAY_BEARER_TOKEN=...  # for bearer mode
mgp-gateway
```

The gateway-side `MGP_GATEWAY_API_KEY` (or `MGP_GATEWAY_BEARER_TOKEN`) **must match** the runtime side — `agents.defaults.mgp.api_key` for Path A, or `--gateway-api-key` for the Path B harness CLI.

### Embedding Models for LanceDB

**Only `lancedb` needs an embedding model.** All other adapters either run lexical search (`memory` / `file` / `graph` / `postgres` / `oceanbase`) or handle embeddings on the vendor side (`mem0` / `zep`). Embedding configuration lives entirely on the gateway; the runtime never touches an embedding model.

| Env var                          | Required        | Purpose |
| -------------------------------- | --------------- | ------- |
| `MGP_LANCEDB_DIR`                | Yes             | Storage path |
| `MGP_LANCEDB_EMBEDDING_PROVIDER` | Yes             | One of LanceDB's [registry](https://docs.lancedb.com/embedding/) entries (`openai`, `gemini`, `sentence-transformers`, `ollama`, `cohere`, …) plus the MGP alias `openrouter`, or `fake` for tests |
| `MGP_LANCEDB_EMBEDDING_MODEL`    | Yes             | Model name as that provider expects it |
| `MGP_LANCEDB_EMBEDDING_API_KEY`  | Cloud providers | API key |
| `MGP_LANCEDB_EMBEDDING_BASE_URL` | Optional        | Override endpoint — required for OpenAI-compatible relays |
| `MGP_LANCEDB_EMBEDDING_DIM`      | Optional        | Pin output dimension (must match the table) |

#### Three common setups

```bash
# A. OpenAI direct — cheap, strong English
export MGP_LANCEDB_EMBEDDING_PROVIDER=openai
export MGP_LANCEDB_EMBEDDING_MODEL=text-embedding-3-small
export MGP_LANCEDB_EMBEDDING_API_KEY=sk-...

# B. Local, free, air-gapped (model auto-downloaded on first use)
export MGP_LANCEDB_EMBEDDING_PROVIDER=sentence-transformers
export MGP_LANCEDB_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# C. OpenRouter (built-in alias; aggregates many vendors behind one key)
export MGP_LANCEDB_EMBEDDING_PROVIDER=openrouter
export MGP_LANCEDB_EMBEDDING_API_KEY=sk-or-v1-...
export MGP_LANCEDB_EMBEDDING_MODEL=openai/text-embedding-3-small
```

#### OpenAI-compatible relays

Use `provider=openai` plus a custom `BASE_URL`. Works for SiliconFlow, DeepInfra, Together, Fireworks, OneAPI/NewAPI, vLLM/Xinference/LocalAI, etc.

```bash
export MGP_LANCEDB_EMBEDDING_PROVIDER=openai
export MGP_LANCEDB_EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
export MGP_LANCEDB_EMBEDDING_API_KEY=sk-...
export MGP_LANCEDB_EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
```

> Azure OpenAI uses a different URL scheme and won't work directly — wrap it with LiteLLM/OneAPI first, or use a dedicated provider entry when one exists.

#### Notes

- **Switching provider/model invalidates existing vectors.** Either `rm -rf $MGP_LANCEDB_DIR` and rewrite, or use `/mgp/export` → `/mgp/import` to recompute on the new model.
- `mem0` / `zep` ignore all `MGP_LANCEDB_EMBEDDING_*` vars — embedding model and pricing are controlled in their vendor dashboard.
- `provider=fake` produces deterministic hash vectors. CI only.

### SaaS Adapter Notes

**mem0** — sign up at [app.mem0.ai](https://app.mem0.ai) for `MGP_MEM0_API_KEY`. The adapter falls back to the env name `MEM0_API_KEY` if the MGP-prefixed variant is unset. `MGP_MEM0_ENABLE_GRAPH` defaults to `true`; turn it off if your mem0 plan does not include the graph feature.

**zep** — sign up at [www.getzep.com](https://www.getzep.com) for `MGP_ZEP_API_KEY`. The adapter also accepts `ZEP_API_KEY`. For self-hosted Zep, set `MGP_ZEP_BASE_URL=http://your-zep:8000`. Zep stores episodes under a single graph user (`MGP_ZEP_GRAPH_USER_ID`, default `mgp-global`); MGP subject isolation is layered on top via metadata filters, so you typically do not need to change this.

### Switching Adapters

The runtime never needs to know which backend the gateway uses — it only needs `gateway_url`. To change backends:

1. **Stop** the running gateway (`pkill mgp-gateway` or Ctrl-C).
2. **Install** the new adapter's extras / SDK and **export** its env vars. Unset the old adapter's vars to avoid surprises.
3. **Restart** `mgp-gateway`. Existing data does **not** migrate automatically — each adapter has its own storage. Use `/mgp/export` → `/mgp/import` if you need to carry data over.

Verify the swap took effect:

```bash
curl http://127.0.0.1:8080/mgp/capabilities | jq '.data.adapter_name'
```

---

## Common Errors

| Symptom | Likely cause |
| --- | --- |
| `MGP_INVALID_OBJECT` on commit | The candidate uses a `memory_type` outside the spec set. Most common: writing `identity` instead of `profile`. |
| `PolicyDeniedError` on search or commit | The policy context is missing a required field (e.g. `actor_agent`, `acting_for_subject.id`) or the configured policy hook denies the action. |
| `401 Unauthorized` from the gateway | `MGP_GATEWAY_AUTH_MODE` is `api_key` / `bearer` but the runtime is sending no token, or the token does not match. |
| `[recall_memory degraded: ...]` on every call | Gateway is unreachable or returning errors. Check `curl http://127.0.0.1:8080/healthz`; for SaaS adapters, confirm the vendor key is valid. |
| Group chat shows the same memory across users (Path A) | The channel implementation is leaving `InboundMessage.sender_id` empty, so subject derivation collapses everyone onto one `chat_id`. Populate `sender_id` with the real per-person id. |

---

## See Also

- [`docs/sidecar-integration.md`](../../docs/sidecar-integration.md) — the generic sidecar pattern this directory implements.
- [`docs/adapter-guide.md`](../../docs/adapter-guide.md) — how to author a new adapter.
- [`docs/protocol-reference.md`](../../docs/protocol-reference.md) — the full MGP wire contract.
- [`nanobot/agent/mgp/README.md`](https://github.com/HKUDS/nanobot/blob/main/nanobot/agent/mgp/README.md) — runtime-side wiring reference for Path A.
