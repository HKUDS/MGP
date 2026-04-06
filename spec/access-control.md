# Access Control

This document defines the access decision contract for `MGP v0.1`.

## Purpose

MGP does not define a policy engine, rule language, or authorization framework. Instead, it defines the stable protocol-level output shape that any policy evaluation must produce.

This makes policy behavior interoperable without forcing all implementations to share the same internal engine.

## Access Decision Shape

```json
{
  "decision": "allow | deny | redact | summarize",
  "reason_code": "string",
  "applied_rules": [
    "string"
  ],
  "return_mode": "raw | summary | masked | metadata_only"
}
```

## Fields

### `decision`

The top-level governance outcome for the request or result item.

Allowed values:

- `allow`
- `deny`
- `redact`
- `summarize`

### `reason_code`

A stable implementation-defined reason identifier that explains why the decision was produced.

Examples:

- `tenant_mismatch`
- `sensitivity_restricted`
- `summary_required_by_policy`

### `applied_rules`

An ordered list of policy rule identifiers that contributed to the final decision.

This is useful for auditability and debugging, even when different implementations use different policy engines internally.

### `return_mode`

The required representation mode for data returned to the caller.

Allowed values:

- `raw`
- `summary`
- `masked`
- `metadata_only`

## Decision Outcomes

### `allow`

The caller is allowed to receive or perform the requested operation without governance-driven transformation beyond normal protocol behavior.

Typical return mode:

- `raw`

### `deny`

The caller is not permitted to perform the operation or receive the requested data.

Typical return mode:

- `metadata_only` or no data, depending on operation semantics

Typical protocol outcome:

- may return `MGP_POLICY_DENIED`

### `redact`

The caller may receive the result, but sensitive fields must be masked or removed.

Typical return mode:

- `masked`

### `summarize`

The caller may receive a derived summary rather than the full raw memory object.

Typical return mode:

- `summary`

## Return Modes

### `raw`

Return the full memory object in its normal protocol shape.

### `summary`

Return a summary representation instead of the full underlying payload.

Example:

- a search result may expose a brief summary of a restricted memory rather than its original content

### `masked`

Return the object with sensitive fields masked, omitted, or transformed.

Example:

- a memory object may return content with restricted attributes removed

### `metadata_only`

Return a metadata-safe canonical memory view.

For `MGP v0.1.0`, this mode still uses the normal response shape and a schema-valid memory object.

That means:

- the caller must not receive semantic memory content
- implementations may replace semantic fields with non-sensitive placeholders so the object still conforms to the published schemas
- callers must treat the returned object as metadata only, even though it still uses the canonical memory-object shape

Example:

- `memory_id`, `type`, `scope`, and timestamps are returned
- `memory.content` may contain a placeholder statement such as `"preference metadata only"` rather than the original semantic payload
- `consumable_text`, `matched_terms`, and `explanation` must not leak semantic content

## Operation Guidance

### Single-Object Operations

For `GetMemory`, `WriteMemory`, `UpdateMemory`, `ExpireMemory`, and `RevokeMemory`, the access decision typically applies to the whole operation.

### Search Results

For `SearchMemory`, different result items may carry different governance outcomes.

This means:

- one result can be `raw`
- another can be `summary`
- another can be `masked`
- another may be removed entirely due to `deny`

Implementations should therefore treat access decisions as potentially item-level during search, not only request-level.

For `deny` during search, two interoperable behaviors are allowed:

- omit the denied item entirely
- return a `metadata_only` item when policy allows existence disclosure without semantic content

Implementations should choose one behavior consistently within a deployment and document that choice for runtime authors.

## Stable Contract Rule

The access decision contract is the interoperable surface.

Implementations are free to use:

- RBAC
- ABAC
- custom rule engines
- external policy systems

But they should normalize policy outcomes into the contract defined here before exposing them through MGP.

## Non-Goals

This document does not define:

- role models
- permission vocabularies
- policy DSLs
- identity providers
- authentication protocols
