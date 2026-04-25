# Search Results

This document defines the normalized result contract for `SearchMemory`.

## Purpose

Different backends may use different retrieval algorithms, ranking ranges, and access transformations. MGP standardizes the structure of returned results so that runtimes can interpret search results consistently across adapters.

Machine-readable schema:

- `schemas/search-result-item.schema.json`

## Result Item Shape

```json
{
  "memory": {},
  "score": 0.92,
  "score_kind": "backend_local",
  "backend_origin": "adapter-or-backend-id",
  "retrieval_mode": "lexical",
  "return_mode": "raw",
  "redaction_info": null,
  "consumable_text": "User prefers concise replies.",
  "matched_terms": ["concise", "replies"],
  "explanation": "Matched lexical terms against normalized memory content."
}
```

## Fields

### `memory`

The normalized MGP memory object returned by the search operation.

This object should conform to [schemas/memory-object.schema.json](../schemas/memory-object.schema.json), subject to any access-control transformation allowed by policy.

For `metadata_only` in `MGP v0.1.1`, implementations should still return a schema-valid canonical memory object, but any semantic content must be replaced with non-sensitive placeholder content.

### `score`

A numeric relevance score assigned by the implementation.

MGP does not standardize the numeric range or ranking formula. It only requires that a score be present so callers can reason about relative ordering.

### `score_kind`

Indicates how `score` should be interpreted.

Allowed values:

- `backend_local`
- `normalized`
- `comparable`

### `backend_origin`

Identifier of the adapter or backend that produced the result.

This is especially important when a gateway fans out across multiple backends and merges the result set.

### `retrieval_mode`

Describes the retrieval strategy that surfaced the result.

Allowed values:

- `lexical`
- `semantic`
- `hybrid`
- `graph`
- `direct_lookup`

### `return_mode`

The effective access-control representation mode for the result item.

Allowed values:

- `raw`
- `summary`
- `masked`
- `metadata_only`

This should align with the access decision contract defined in [spec/access-control.md](access-control.md).

### `redaction_info`

Optional object describing what was transformed or hidden.

Possible fields include:

- `reason_code`
- `masked_fields`
- `summary_generated`

The `redaction_info` field has a standardized machine-readable shape defined in:

- `schemas/redaction-info.schema.json`

### `consumable_text`

A runtime-safe text view of the result that can be consumed without runtime-specific rendering logic.

This field is the preferred prompt-facing view for:

- `raw`
- `summary`
- `masked`

For `metadata_only`, the value should still be present but should not leak semantic memory content.

### `matched_terms`

Terms or keywords that contributed to result retrieval.

### `explanation`

Human-readable explanation of why the result was returned.

## Result Set Rules

### Ordering

Result ordering is implementation-defined, but items should be returned in a stable order relative to the implementation's ranking logic.

### Empty Results

An empty result set is valid and should not be treated as an error.

Example:

```json
{
  "request_id": "req_123",
  "status": "ok",
  "error": null,
  "data": {
    "results": []
  }
}
```

### Mixed Return Modes

Different results in the same response may have different `return_mode` values.

Example:

- one result is returned as `raw`
- another as `summary`
- another as `masked`

Runtimes must not assume one request yields only one representation mode across all items.

Denied search items may either:

- be omitted entirely from the result set
- appear as `metadata_only` when policy allows existence disclosure without semantic content

In both cases, implementations must avoid leaking semantic memory content through `memory`, `consumable_text`, `matched_terms`, or `explanation`.

For `metadata_only`, a schema-valid canonical memory shape is still expected. Callers should treat the object as non-semantic metadata even when placeholder `memory.content.statement` fields are present to preserve schema validity.

Runtimes should also avoid assuming:

- scores are globally comparable across backends unless `score_kind == "comparable"`
- `memory.content` is always the best prompt view; prefer `consumable_text`

## Multi-Backend Guidance

When a gateway aggregates results from multiple backends:

- each result item should still include a single `backend_origin`
- scores may be normalized or merged by implementation policy
- access-control transformations must be reflected in each item's `return_mode`
- gateways should preserve or synthesize `consumable_text` and `explanation` even when adapters differ

## Non-Goals

This document does not define:

- ranking formulas
- embedding similarity math
- merge algorithms for multi-backend score normalization
- one universal prompt composition strategy
