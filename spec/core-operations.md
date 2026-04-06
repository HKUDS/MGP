# Core Operations

This document defines the core runtime operations for MGP.

## Operation Model

MGP operations remain transport-agnostic, but the reference HTTP binding exposes them as JSON request/response envelopes with richer machine-readable payloads.

Shared assets:

- Request envelope: `schemas/request-envelope.schema.json`
- Response envelope: `schemas/response-envelope.schema.json`
- Memory object: `schemas/memory-object.schema.json`
- Memory candidate: `schemas/memory-candidate.schema.json`
- Recall intent: `schemas/recall-intent.schema.json`
- Search result item: `schemas/search-result-item.schema.json`
- Partial failure: `schemas/partial-failure.schema.json`
- Merge hint: `schemas/memory-merge-hint.schema.json`
- Policy context: `schemas/policy-context.schema.json`

Contract note:

- `schemas/response-envelope.schema.json` defines the shared outer response shell
- operation-specific response schemas such as `schemas/search-memory.response.schema.json` and `schemas/audit-query.response.schema.json` define the exact `data` shape for each operation
- HTTP implementations should follow the operation-specific schema when it is more specific than the shared envelope

## Operation Summary

| Operation | Suggested HTTP path | Semantics | Idempotency |
| --- | --- | --- | --- |
| `WriteMemory` | `/mgp/write` | Create, dedupe, upsert, merge, or reinforce a memory | Strategy-dependent |
| `SearchMemory` | `/mgp/search` | Recall memory via query shorthand or structured recall intent | Safe and read-only |
| `GetMemory` | `/mgp/get` | Fetch a single memory object or tombstone view | Safe and read-only |
| `UpdateMemory` | `/mgp/update` | Patch an existing memory object | Idempotent with explicit target |
| `ExpireMemory` | `/mgp/expire` | Mark a memory as expired | Idempotent |
| `RevokeMemory` | `/mgp/revoke` | Withdraw a memory from normal use | Idempotent |
| `DeleteMemory` | `/mgp/delete` | Soft-delete a memory into a tombstone state | Idempotent |
| `PurgeMemory` | `/mgp/purge` | Hard-delete a memory from normal storage paths | Idempotent |
| `AuditQuery` | `/mgp/audit/query` | Retrieve normalized audit events for a target memory, request, or scope | Safe and read-only |

## Interoperability Extensions

The reference binding also exposes optional interoperability endpoints:

| Operation | Suggested HTTP path | Purpose |
| --- | --- | --- |
| `BatchWriteMemory` | `/mgp/write/batch` | Apply multiple write items in one request |
| `ExportMemories` | `/mgp/export` | Page through canonical memory objects for migration or backup |
| `ImportMemories` | `/mgp/import` | Import canonical memory objects into a compatible backend |
| `SyncMemories` | `/mgp/sync` | Cursor-based synchronization of memory pages |

## Common Request Envelope

```json
{
  "request_id": "req_123",
  "policy_context": {
    "actor_agent": "nanobot/main",
    "acting_for_subject": {
      "kind": "user",
      "id": "user_123"
    },
    "requested_action": "write",
    "tenant_id": "tenant_1",
    "session_id": "session_123",
    "correlation_id": "trace_123"
  },
  "payload": {}
}
```

## Common Response Envelope

```json
{
  "request_id": "req_123",
  "status": "ok",
  "error": null,
  "data": {}
}
```

## WriteMemory

### Description

Creates or reconciles canonical memory under MGP governance.

### Request Shapes

`WriteMemory` accepts one of two payload styles:

1. canonical write

```json
{
  "payload": {
    "memory": {}
  }
}
```

2. candidate write

```json
{
  "payload": {
    "candidate": {},
    "merge_hint": {}
  }
}
```

### Required Fields

- `request_id`
- `policy_context`
- one of `payload.memory` or `payload.candidate`

### Response Fields

- `data.memory`
- `data.return_mode`
- `data.redaction_info`
- `data.consumable_text`
- `data.resolution`

Representation note:

- `data.memory` always uses the canonical memory-object shape from `schemas/memory-object.schema.json`
- for `summary`, `masked`, and `metadata_only`, implementations should transform the canonical object rather than inventing a different response object type

### Resolution Semantics

Reference strategies:

- `create`
- `dedupe`
- `upsert`
- `replace`
- `merge`
- `reinforce`
- `manual_review_required`

If a merge strategy cannot be safely satisfied, the operation should return `MGP_CONFLICT_UNRESOLVED`.

### Retry Guidance

- callers should treat `WriteMemory` as potentially non-idempotent unless they provide explicit dedupe, merge, or target identity signals
- runtimes that need retry safety should reuse the same `request_id` and prefer candidate writes with `merge_hint`, stable `memory_id`, or another documented dedupe mechanism
- implementations should document whether retry safety depends on canonical `memory_id`, merge hints, backend-native dedupe, or gateway-side policy

## SearchMemory

### Description

Searches governed memory using either:

- legacy shorthand: `payload.query`
- structured recall intent: `payload.intent`

### Structured Recall Intent

Machine-readable schema:

- `schemas/recall-intent.schema.json`

Typical fields:

- `query_text`
- `intent_type`
- `keywords`
- `target_memory_types`
- `subject`
- `scope`
- `time_scope`
- `top_k`

### Response Fields

- `data.results[]`
- `data.effective_intent`
- `data.partial_failure`

Each result item should conform to:

- `schemas/search-result-item.schema.json`

## GetMemory

### Description

Fetches one canonical memory object by `memory_id`.

### Response Fields

- `data.memory`
- `data.return_mode`
- `data.redaction_info`
- `data.consumable_text`

`GetMemory` may return a soft-deleted tombstone view when policy allows it.

For `metadata_only` in `MGP v0.1.0`, implementations should still return a schema-valid canonical memory object with non-sensitive placeholder content rather than raw semantic payload.

## UpdateMemory

### Description

Applies a patch to an existing memory object.

### Patch Semantics

- nested `content`, `backend_ref`, and `extensions` should be merged rather than blindly replaced
- updates against deleted tombstones should be rejected
- runtimes should prefer explicit `WriteMemory` with merge semantics for semantic replacement, and reserve `UpdateMemory` for targeted mutation

## ExpireMemory

### Description

Moves an active memory into expired state.

### Effects

- hidden from default search
- still auditable
- explicit get may return the expired object depending on policy

## RevokeMemory

### Description

Withdraws a memory from normal use without implying hard deletion.

### Effects

- hidden from default search
- still present for audit, review, and explicit retrieval depending on policy

## DeleteMemory

### Description

Performs soft deletion and leaves a tombstone record.

### Effects

- hidden from default search
- explicit get may return a metadata-only tombstone
- update should be disallowed
- purge may still be performed later

## PurgeMemory

### Description

Performs hard deletion from normal storage access paths.

### Effects

- no longer retrievable by normal get/search
- audit evidence may remain separately
- lineage may remain only as references or tombstones depending on implementation policy

## AuditQuery

### Description

Returns normalized audit events that help callers inspect prior memory reads, writes, lifecycle actions, and policy outcomes.

### Response Fields

- `data.events[]`
- `data.next_token`

## Cross-Cutting Rules

### Policy Context Requirement

Every request must carry a `policy_context`.

### Error Envelope

Failed operations must use:

- `status: error`
- `data: null`
- `error.code` from `spec/errors.md`

### Correlation

Every response must echo the original `request_id`.

### Audit

Every mutating operation should emit an audit event including:

- `request_id`
- `policy_context`
- `decision`
- `backend`
- `target_memory_id`

### Candidate Interoperability

`MemoryCandidate` is now a protocol-level contract. Runtimes can either:

- resolve candidates to canonical memory before calling MGP
- or send candidates directly and let the gateway resolve them
