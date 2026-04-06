# Extensions

This document defines the extension mechanism for `MGP v0.1`.

## Purpose

MGP needs a stable core schema and a flexible way to carry vendor-specific backend details.

The extension mechanism provides that flexibility without allowing adapters or runtimes to mutate the meaning of core protocol fields.

## Core Rule

Portable vendor-specific or implementation-specific semantics must be carried inside the `extensions` field of the canonical memory object.

Core protocol fields must not be:

- renamed
- repurposed
- overloaded with vendor-specific meanings
- removed from the canonical object model

This preserves interoperability across runtimes and adapters.

## Allowed Locations

Portable extension data belongs in:

- `memory_object.extensions`

Adapter-local handle data may also use:

- `memory_object.backend_ref`

Boundary rule:

- `backend_ref` is for opaque adapter-local routing, storage, or handle metadata
- `extensions` is for namespaced semantics that another implementation may preserve or reason about

Implementations must not add vendor-defined top-level fields next to core fields such as `memory_id`, `subject`, `scope`, or `type`.

## Namespace Format

Every extension key must use a namespace prefix:

```text
vendor:key_name
```

Examples:

- `zep:graph_edge_type`
- `langgraph:checkpoint_id`
- `openclaw:file_path`

This makes it possible to:

- avoid collisions between vendors
- reason about which adapter understands which keys
- preserve unknown extension keys safely

## Compatibility Rules

Extensions must not break core compatibility.

That means:

- a memory object containing extensions must still validate against the core memory object schema
- a runtime that does not understand an extension should still be able to process the core object
- adapters may ignore unknown extensions for behavior, but should not corrupt the rest of the object

## Round-Trip Preservation

When an adapter reads and later re-emits a memory object, it should preserve unknown extensions whenever possible.

Recommended behavior:

- preserve known extensions exactly
- preserve unknown extensions if the backend can store opaque metadata
- document any dropped extensions as an adapter limitation when round-trip preservation is impossible

The goal is that extension data should survive transit through MGP even if an intermediate component does not interpret it.

## Adapter Declaration

If an adapter understands or emits extensions, it should declare supported namespaces in its adapter manifest.

Example:

```json
{
  "adapter_name": "zep-adapter",
  "extension_namespaces": [
    "zep"
  ]
}
```

This helps runtimes know which extension families are likely to be meaningful for a particular backend.

## Boundary With `content`

Semantic fields that another runtime can reason about should remain in `content`.

Examples:

- a preference memory may keep `preference_key` and `preference_value` in `content` because they are part of the meaning of the memory
- a relationship memory may keep role or validity-window fields in `content` when they describe the governed fact itself

Backend-local or adapter-local opaque handles belong in `backend_ref`.

Portable vendor semantics belong in `extensions`.

Examples:

- `backend_ref.tenant_id`
- `backend_ref.document_pk`
- `backend_ref.collection`
- `zep:episode_id`
- `langgraph:checkpoint_id`
- `openclaw:file_path`

## Examples

### Graph-Oriented Extension

```json
{
  "memory_id": "mem_1",
  "type": "relationship",
  "extensions": {
    "zep:graph_edge_type": "works_at"
  }
}
```

### Checkpoint Extension

```json
{
  "memory_id": "mem_2",
  "type": "checkpoint_pointer",
  "extensions": {
    "langgraph:checkpoint_id": "ckpt_123"
  }
}
```

### File-Oriented Extension

```json
{
  "memory_id": "mem_3",
  "type": "artifact_summary",
  "extensions": {
    "openclaw:file_path": "/memory/user_1.md"
  }
}
```

## Invalid Examples

These are invalid extension patterns:

- adding `graph_edge_type` as a new top-level field
- placing opaque adapter handle data in `extensions` when it is only meaningful to one backend hop
- placing vendor metadata inside `content` when it is not part of the semantic memory payload
- using unnamespaced keys such as `checkpoint_id` inside `extensions`

## Non-Goals

This document does not define:

- a global registry of extension namespaces
- semantic meaning for every vendor extension
- per-vendor validation schemas in the core spec
