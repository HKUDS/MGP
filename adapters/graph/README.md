# Graph Reference Adapter

SQLite-backed graph and relationship reference adapter for MGP.

## Purpose

This adapter demonstrates how MGP can support graph-like memory and relationship-centric use cases without requiring an external graph database.

It is a concept-compatible adapter intended to validate:

- relationship memory handling
- graph-oriented extensions
- lineage-capable backend behavior

## Storage Model

- `memories` table stores the canonical memory object fields
- `edges` table stores graph-style links derived from namespaced extensions

## Mapping Rules

- core MGP fields map to columns in the `memories` table
- `content`, `backend_ref`, and `extensions` are stored as JSON strings
- graph-specific fields are expressed through namespaced extensions:
  - `graph:target_memory_id`
  - `graph:relation`
  - `graph:edge_type`
- when `graph:target_memory_id` exists, an edge row is created in the `edges` table

## Supported Capabilities

See [manifest.json](manifest.json).

Highlights:

- `supports_write: true`
- `supports_update: true`
- `supports_search: true`
- `supports_graph_relations: true`
- `supports_lineage_native: true`

## Known Limitations

- uses SQLite rather than a true graph engine
- search is SQL `LIKE` over JSON content, not semantic or graph traversal search
- conflict detection is not native
- partial redaction is not native

## Compliance

This adapter is intended to pass the same compliance suite as the other reference adapters:

```bash
cd compliance
MGP_ADAPTER=graph ../.venv/bin/python -m pytest
```

The CI workflow also publishes a JUnit XML artifact for the graph adapter so compatibility results can be reviewed per run.
