# MGP Python SDK

[![PyPI](https://img.shields.io/badge/package-mgp--client-blue)](#)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](../../LICENSE)

Python client SDK for the Memory Governance Protocol.

## Install

From the repository root:

```bash
python3 -m pip install ./sdk/python
```

Or for development with test dependencies:

```bash
cd sdk/python
python3 -m pip install -e ".[dev]"
```

If you're using the full repository toolchain, `make install` covers this automatically.

## What It Includes

| Component | Description |
|-----------|-------------|
| `MGPClient` | Synchronous HTTP client for all protocol operations |
| `AsyncMGPClient` | Async client for async runtimes |
| `PolicyContextBuilder` | Helper for constructing policy context objects |
| `SearchQuery` / `AuditQuery` | Typed query builders |
| Auth helpers | `ApiKeyAuth`, `BearerAuth`, `TLSConfig` |
| `RetryConfig` | Retry configuration for transient failures |
| Pagination helpers | Iterators for search and audit result streams |
| Task polling | Helpers for async protocol operations |
| Error classes | Mapped from MGP protocol error codes |

## Quick Example

```python
from mgp_client import MGPClient, PolicyContextBuilder, SearchQuery

ctx = PolicyContextBuilder(
    actor_agent="nanobot/main",
    subject_id="user_123",
    tenant_id="tenant_1",
)

with MGPClient("http://127.0.0.1:8080") as client:
    # Write
    client.write_memory(
        ctx.build("write"),
        {
            "memory_id": "mem_1",
            "subject": {"kind": "user", "id": "user_123"},
            "scope": "user",
            "type": "preference",
            "content": {
                "statement": "User prefers dark mode.",
                "preference_key": "theme",
                "preference_value": "dark",
            },
            "source": {"kind": "human", "ref": "chat:1"},
            "created_at": "2026-03-17T12:00:00Z",
            "backend_ref": {"tenant_id": "tenant_1"},
            "extensions": {},
        },
    )

    # Search
    result = client.search_memory(
        ctx.build("search"),
        SearchQuery(
            query_text="What does the user prefer for theme?",
            intent_type="preference_lookup",
            keywords=["dark", "theme"],
            target_memory_types=["preference"],
        ),
    )
    print(result.data["results"])
```

## Async Usage

```python
from mgp_client import AsyncMGPClient, BearerAuth, PolicyContextBuilder

ctx = PolicyContextBuilder(
    actor_agent="runtime/agent",
    subject_id="user_123",
    tenant_id="tenant_1",
)

async with AsyncMGPClient(
    "http://127.0.0.1:8080",
    auth=BearerAuth("secret-token"),
) as client:
    capabilities = await client.get_capabilities()
    print(capabilities["manifest"]["backend_kind"])

    response = await client.export_memories(
        ctx.build("read"),
        {"execution_mode": "async", "limit": 100},
    )
    task = await client.wait_for_task(response.data["task"]["task_id"])
    print(task["status"])
```

## Auth And Retry

```python
from mgp_client import ApiKeyAuth, MGPClient, RetryConfig, TLSConfig

client = MGPClient(
    "https://gateway.example.com",
    auth=ApiKeyAuth("gateway-api-key"),
    tls=TLSConfig(verify=True),
    retry=RetryConfig(max_attempts=3, backoff_seconds=0.2),
)
```

## Pagination

```python
for item in client.iter_search_results(
    ctx.build("search"),
    SearchQuery(query_text="preferences", limit=50),
):
    print(item["memory"]["memory_id"])
```

## Surface Coverage

- Core memory operations (write, search, get, update, expire, revoke, delete, purge)
- Lifecycle operations (initialize, capabilities)
- Batch write
- Export / import / sync
- Audit query
- Async task polling

## Notes

- This SDK is transport-focused and independent of the reference gateway implementation.
- `write_memory()` accepts canonical memory objects; `write_candidate()` accepts `MemoryCandidate` payloads.
- Search and get responses include `consumable_text`, `return_mode`, and `redaction_info` — runtimes should prefer those fields over assuming raw `memory.content` is always prompt-safe.
- The SDK can be used against any gateway that implements the MGP HTTP binding.
