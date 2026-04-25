# Getting Started

This guide walks you through setting up MGP, starting the reference gateway, and running your first governed memory operations — all in about five minutes.

**What you'll learn:**

- Install the MGP reference gateway and Python SDK
- Start a local gateway with the in-memory adapter
- Write, search, update, expire, and audit memory objects
- Understand core concepts: memory objects, policy context, adapters, and lifecycle

## Prerequisites

- Python 3.11+
- Git

## 1. Clone And Install

```bash
git clone https://github.com/hkuds/MGP.git
cd MGP
make install
```

This creates a virtual environment at `.venv/` and installs the reference gateway, compliance suite, documentation tooling, and the Python SDK.

If you only want the packaged reference gateway CLI instead of the whole repository toolchain:

```bash
python3 -m pip install .
```

## 2. Start The Reference Gateway

```bash
make serve
```

The gateway starts at `http://127.0.0.1:8080` using the in-memory adapter by default. You can verify it is running:

```bash
curl http://127.0.0.1:8080/mgp/capabilities
```

You should see a JSON response containing the backend capabilities, including `backend_kind`, supported operations, and feature flags. This confirms the gateway is ready.

Alternative run paths:

```bash
mgp-gateway --host 127.0.0.1 --port 8080
docker compose up --build
```

Operational helpers:

- `GET /healthz`
- `GET /readyz`
- `GET /version`

## 3. Write Your First Memory

Every MGP request requires a **policy context** that describes who is acting, on whose behalf, and for what purpose. This gives the protocol a stable place to carry governance inputs such as actor, subject, tenant, and request intent. MGP does not define the internal policy engine itself.

Minimum required fields in policy context:

- `actor_agent` — the agent or service performing the action
- `acting_for_subject` — who the action is on behalf of
- `requested_action` — what operation is being requested

### Using cURL

```bash
curl -X POST http://127.0.0.1:8080/mgp/write \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_001",
    "policy_context": {
      "actor_agent": "my-agent/v1",
      "acting_for_subject": {"kind": "user", "id": "user_alice"},
      "requested_action": "write",
      "tenant_id": "my_tenant"
    },
    "payload": {
      "memory": {
        "memory_id": "mem_001",
        "subject": {"kind": "user", "id": "user_alice"},
        "scope": "user",
        "type": "preference",
        "content": {
          "statement": "User prefers dark mode.",
          "preference_key": "theme",
          "preference_value": "dark"
        },
        "source": {"kind": "human", "ref": "chat:1"},
        "sensitivity": "internal",
        "created_at": "2026-01-01T00:00:00Z",
        "backend_ref": {"tenant_id": "my_tenant"},
        "extensions": {}
      }
    }
  }'
```

Expected response:

```json
{"status": "ok", "request_id": "req_001", ...}
```

### Using the Python SDK

```python
from mgp_client import MGPClient, PolicyContextBuilder

context = PolicyContextBuilder(
    actor_agent="my-agent/v1",
    subject_id="user_alice",
    tenant_id="my_tenant",
)

with MGPClient("http://127.0.0.1:8080") as client:
    response = client.write_memory(
        context.build("write"),
        {
            "memory_id": "mem_001",
            "subject": {"kind": "user", "id": "user_alice"},
            "scope": "user",
            "type": "preference",
            "content": {
                "statement": "User prefers dark mode.",
                "preference_key": "theme",
                "preference_value": "dark",
            },
            "source": {"kind": "human", "ref": "chat:1"},
            "sensitivity": "internal",
            "created_at": "2026-01-01T00:00:00Z",
            "backend_ref": {"tenant_id": "my_tenant"},
            "extensions": {},
        },
    )
    print(response.status)  # "ok"
```

## 4. Search Memory

Now recall what you just wrote. MGP search returns structured results with `consumable_text` that runtimes can safely inject into prompts.

### Using cURL

```bash
curl -X POST http://127.0.0.1:8080/mgp/search \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_002",
    "policy_context": {
      "actor_agent": "my-agent/v1",
      "acting_for_subject": {"kind": "user", "id": "user_alice"},
      "requested_action": "search",
      "tenant_id": "my_tenant"
    },
    "payload": {
      "query": "dark mode",
      "limit": 10
    }
  }'
```

The response contains a `results` array. Each result item includes the matched memory object, a `consumable_text` string safe for prompt injection, and a `return_mode` indicator.

### Using the Python SDK

```python
from mgp_client import MGPClient, PolicyContextBuilder, SearchQuery

search_context = PolicyContextBuilder(
    actor_agent="my-agent/v1",
    subject_id="user_alice",
    tenant_id="my_tenant",
).build("search")

with MGPClient("http://127.0.0.1:8080") as client:
    result = client.search_memory(
        search_context,
        SearchQuery(query="dark mode", limit=10),
    )
    for item in result.data.get("results", []):
        print(item["consumable_text"])
```

## 5. Full Lifecycle Walkthrough

The following sequence demonstrates the complete governed memory lifecycle: write, search, get, update, expire, and audit.

```python
from mgp_client import MGPClient, PolicyContextBuilder, SearchQuery, AuditQuery

context = PolicyContextBuilder(
    actor_agent="my-agent/v1",
    subject_id="user_alice",
    tenant_id="my_tenant",
)

with MGPClient("http://127.0.0.1:8080") as client:
    # Write a preference
    client.write_memory(
        context.build("write"),
        {
            "memory_id": "mem_lifecycle",
            "subject": {"kind": "user", "id": "user_alice"},
            "scope": "user",
            "type": "preference",
            "content": {
                "statement": "User prefers Python.",
                "preference": "Python",
                "preference_key": "language",
                "preference_value": "python",
            },
            "source": {"kind": "human", "ref": "chat:2"},
            "created_at": "2026-01-01T00:00:00Z",
            "backend_ref": {"tenant_id": "my_tenant"},
            "extensions": {},
        },
    )

    # Search — should find the preference
    results = client.search_memory(
        context.build("search"),
        SearchQuery(query="python", limit=5),
    )
    print(f"Search found {len(results.data.get('results', []))} result(s)")

    # Get by ID
    mem = client.get_memory(context.build("read"), "mem_lifecycle")
    print(f"Got memory: {mem.data['memory']['type']}")

    # Update the content
    client.update_memory(
        context.build("update"),
        "mem_lifecycle",
        {
            "content": {
                "statement": "User prefers Rust.",
                "preference": "Rust",
                "preference_key": "language",
                "preference_value": "rust",
            }
        },
    )

    # Expire the memory
    client.expire_memory(
        context.build("expire"),
        "mem_lifecycle",
        reason="user_changed_mind",
    )

    # Search again — expired memory should not appear
    after = client.search_memory(
        context.build("search"),
        SearchQuery(query="python", limit=5),
    )
    print(f"After expire: {len(after.data.get('results', []))} result(s)")

    # Audit trail — see what happened to this memory
    audit = client.query_audit(
        context.build("read"),
        AuditQuery(target_memory_id="mem_lifecycle", limit=20),
    )
    for event in audit.data.get("events", []):
        print(f"  {event['action']} at {event.get('timestamp', 'N/A')}")
```

Expected console output:

```
Search found 1 result(s)
Got memory: preference
After expire: 0 result(s)
  write at 2026-01-01T00:00:00Z
  update at ...
  expire at ...
```

You can also run the bundled end-to-end demo directly:

```bash
make serve  # in one terminal
./.venv/bin/python examples/e2e_demo.py  # in another terminal
```

## Key Concepts

### Memory Object

The canonical unit of governed memory. Every memory object has a `subject` (who it's about), a `scope` (how broadly it applies), a `type` (what kind of memory it is), and structured `content`.

### Policy Context

Every request carries a policy context that tells the gateway who is acting, on whose behalf, and under what governance constraints. This enables a stable protocol contract for audit, access control, and policy outcomes, while leaving the concrete policy engine to the implementation.

### Adapter

An adapter bridges a concrete storage backend into the MGP protocol surface. The repository includes adapters for in-memory, file, graph (SQLite), PostgreSQL, LanceDB, Mem0, and Zep backends. You can write your own by following the [Adapter Guide](adapter-guide.md).

### Capability

Each adapter declares what it can and cannot do through a `manifest.json`. Runtimes use capability declarations to reason about backend behavior without trial and error.

### Lifecycle

Memory in MGP is not just CRUD. Objects can be expired, revoked, deleted, or purged — each with distinct governance semantics. Audit trails record every state transition.

## A Note On Reference Adapters

The in-memory adapter used in this guide (and the file and graph adapters) are **reference implementations** for protocol verification and learning. They are not intended for production use. For production deployments, build or adopt adapters targeting your actual storage backend — see the [Adapter Guide](adapter-guide.md).

## Next Steps

| Goal | Resource |
| --- | --- |
| Understand the protocol in depth | [Protocol Reference](protocol-reference.md) |
| See all JSON schemas | [Schema Reference](schema-reference.md) |
| Build your own adapter | [Adapter Guide](adapter-guide.md) |
| Explore existing adapters | [Adapters Overview](adapters-overview.md) |
| Use the Python SDK | [Python SDK](python-sdk.md) |
| Run compliance tests | [Compliance Suite](compliance-suite.md) |
| Integrate via sidecar | [Sidecar Integration](sidecar-integration.md) |
| Understand MGP vs MCP | [MGP vs MCP](mgp-vs-mcp.md) |
| Try different backends | `make serve` with `MGP_ADAPTER=file` or `MGP_ADAPTER=graph` |
