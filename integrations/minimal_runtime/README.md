# Minimal Runtime Integration

This integration shows the smallest useful MGP runtime bridge without depending on a specific agent framework.

The repository path uses `integrations/minimal_runtime/` because this directory is also the importable Python package used in the examples.

## What It Demonstrates

- building `policy_context` with `PolicyContextBuilder`
- recalling governed memory before a model call
- committing a candidate memory after a turn
- keeping the integration thin enough to copy into another codebase

## Example

```python
from integrations.minimal_runtime import MinimalRuntimeMemoryBridge

bridge = MinimalRuntimeMemoryBridge("http://127.0.0.1:8080")

recall = bridge.recall(
    actor_agent="minimal-runtime/agent",
    user_id="user_123",
    tenant_id="tenant_demo",
    query="What does the user prefer for theme?",
)

commit = bridge.commit_candidate(
    actor_agent="minimal-runtime/agent",
    user_id="user_123",
    tenant_id="tenant_demo",
    candidate={
        "candidate_kind": "assertion",
        "subject": {"kind": "user", "id": "user_123"},
        "scope": "user",
        "proposed_type": "preference",
        "statement": "User prefers dark mode.",
        "source": {"kind": "runtime", "ref": "turn:1"},
        "content": {
            "statement": "User prefers dark mode.",
            "preference_key": "theme",
            "preference_value": "dark",
        },
    },
)
```

## Intended Use

Use this directory as the starting point when you want to integrate MGP into:

- a proprietary runtime
- a CLI agent loop
- a background worker that needs governed memory recall and commit
