# Retention

This document defines the retention model for MGP.

## Purpose

Retention describes the intended lifetime and review posture of a memory object. It is a governance semantic, not just a storage implementation detail.

The memory object includes:

- `retention_policy`
- `ttl_seconds`

This document defines how those fields should be interpreted.

## Retention Policy Identifiers

### `ephemeral`

The memory is intended for immediate or short-lived use and should not be preserved beyond the narrow interaction that produced it.

Typical use cases:

- scratch reasoning outputs
- one-turn extraction artifacts
- temporary memory candidates before filtering

### `session_bound`

The memory remains valid only for the lifetime of the session that produced or owns it.

Typical use cases:

- session-local preferences
- temporary references created during one conversation
- short-lived coordination state

### `task_bound`

The memory remains valid only while the associated task remains active.

Typical use cases:

- task-specific context
- temporary reminders for a single workflow
- execution-local facts not meant to become durable user memory

### `time_bound`

The memory is governed by an explicit time window, typically represented by `ttl_seconds` or equivalent backend metadata.

Typical use cases:

- promotional or time-sensitive facts
- temporary user state
- data with explicit regulatory retention limits

### `persistent`

The memory has no expected automatic expiration and remains available until revoked, superseded, or otherwise governed by policy.

Typical use cases:

- durable user profile facts
- stable preferences
- long-term semantic knowledge

### `manual_review_required`

The memory is retained, but any destructive transition such as hard deletion should require explicit review outside automatic lifecycle rules.

Typical use cases:

- high-risk memories
- regulated records
- memories that may require human confirmation before removal

## TTL and Retention Relationship

Retention policy and TTL are related but different:

- `retention_policy` expresses the semantic intent of the memory lifetime
- `ttl_seconds` expresses a concrete expiration mechanism

Examples:

- A `time_bound` memory should normally provide `ttl_seconds`
- A `session_bound` memory may not need `ttl_seconds` if the runtime can signal session end
- A `persistent` memory should typically omit `ttl_seconds`
- A `manual_review_required` memory may have `ttl_seconds` for review scheduling, but not for automatic hard deletion

## Expiration States

### Soft Expired

Soft-expired memories remain present in the system but are treated as inactive for normal retrieval and ranking behavior.

Expected behavior:

- excluded from default `SearchMemory`
- retrievable by explicit `GetMemory` if the implementation allows expired access
- still available for audit, lineage, and review workflows

### Hard Deleted

Hard-deleted memories are permanently removed from normal storage access paths.

Expected behavior:

- no longer retrievable as a normal memory object
- audit evidence may still exist separately
- lineage references may remain as tombstones or metadata, depending on implementation policy

## Transition Guidance

Recommended lifecycle path:

```text
active -> soft_expired -> deleted_tombstone -> hard_deleted
```

Not all policies require both states:

- `ephemeral` may transition quickly to hard deletion
- `persistent` may never expire automatically
- `manual_review_required` should usually stop at soft expiration or review-pending state until reviewed

### Deleted Tombstone

A deleted tombstone represents protocol-level soft deletion.

Expected behavior:

- excluded from default `SearchMemory`
- may still be returned by explicit `GetMemory` as metadata-only
- should remain auditable
- may later transition to hard purge

## Backend Capability Fallback

Some backends do not support native TTL or native expiration state.

When native TTL is unavailable, the implementation should use one of these fallback strategies:

- gateway-managed expiration checks before reads and searches
- adapter-managed lazy expiration at access time
- periodic sweeps that mark objects as expired in adapter metadata

The absence of native TTL must not change the protocol semantics seen by the runtime. The runtime should still observe consistent retention behavior through MGP.

## Operation Impact

Retention affects operations as follows:

- `WriteMemory` should record the intended retention semantics
- `SearchMemory` should exclude soft-expired memories by default unless explicitly requested
- `GetMemory` may return expired memories with state metadata if allowed by policy
- `ExpireMemory` is the explicit protocol transition into expiration handling
- `RevokeMemory` is distinct from expiration and should not be treated as the same event
- `DeleteMemory` moves a memory into tombstone state
- `PurgeMemory` removes the memory from normal storage access paths

## Non-Goals

This document does not define:

- physical storage deletion algorithms
- backend scheduler implementation details
- legal compliance frameworks
- review workflow UX
