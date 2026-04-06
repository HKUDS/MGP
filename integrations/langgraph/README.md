# LangGraph Integration Sketch

This directory demonstrates how to wire MGP into a LangGraph-style state object without requiring LangGraph itself to be vendored into this repository.

## What It Shows

- treating graph state as the source for `policy_context`
- recalling governed memory before node execution
- committing a candidate after a node decides something should be remembered
- keeping the integration thin enough to move into a real LangGraph project

## Example State

```python
state = {
    "actor_agent": "langgraph/runtime",
    "user_id": "user_123",
    "tenant_id": "tenant_demo",
    "thread_id": "thread_001",
    "session_id": "session_001",
    "query": "What does the user prefer for theme?",
    "limit": 5,
}
```

## Example Usage

```python
from integrations.langgraph import LangGraphMemoryBridge

bridge = LangGraphMemoryBridge("http://127.0.0.1:8080")

recall_patch = bridge.recall_for_state(state)
state.update(recall_patch)

commit_patch = bridge.commit_for_state(
    state,
    {
        "candidate_kind": "assertion",
        "subject": {"kind": "user", "id": state["user_id"]},
        "scope": "user",
        "proposed_type": "preference",
        "statement": "User prefers dark mode.",
        "source": {"kind": "runtime", "ref": f"thread:{state['thread_id']}"},
        "content": {
            "statement": "User prefers dark mode.",
            "preference_key": "theme",
            "preference_value": "dark",
        },
    },
)
```

## Intended Use

Use this bridge when you want:

- a separate memory node before prompt assembly
- a post-turn commit node after extraction or tool execution
- explicit state patches instead of hiding MGP inside framework internals
