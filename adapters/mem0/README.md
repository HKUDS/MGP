# Mem0 Adapter

Mem0-backed MGP adapter.

## Purpose

This adapter maps MGP canonical memory objects onto a real Mem0 service and treats Mem0 as the source of truth.

It is intended for:

- service-backed governed memory storage
- semantic and graph-aware recall through Mem0
- production deployments that already use Mem0 infrastructure

It is no longer a compatibility wrapper around the local file adapter.

## Storage Model

The adapter stores each MGP memory in Mem0 and keeps the canonical MGP object in Mem0 metadata.

Key points:

- `memory_id` is stored in metadata as `mgp_memory_id`
- the full canonical MGP object is stored in metadata as `mgp_memory`
- lifecycle state is stored in metadata as `mgp_state`
- Mem0 record IDs remain internal service IDs

Because Mem0 has its own internal IDs, the adapter resolves MGP `memory_id` by metadata lookup inside a shared `app_id` namespace.

## Mapping Rules

- `backend_ref.adapter` is always `mem0`
- `backend_ref.mgp_state` is one of `active`, `expired`, `revoked`, or `deleted`
- `backend_ref.mem0_id` stores the Mem0 service record ID when available
- search uses Mem0 semantic retrieval and maps hits back into canonical MGP search results
- graph-enriched search results are exposed through `extensions.mem0:relations`
- delete is a soft-delete implemented via metadata state
- purge is a hard delete implemented via `MemoryClient.delete()`

## Required Environment Variables

- `MGP_MEM0_API_KEY` or `MEM0_API_KEY`: Mem0 API key

## Optional Environment Variables

- `MGP_MEM0_APP_ID`: shared Mem0 application namespace used for metadata lookups, default `mgp`
- `MGP_MEM0_ORG_ID`: Mem0 organization ID
- `MGP_MEM0_PROJECT_ID`: Mem0 project ID
- `MGP_MEM0_ENABLE_GRAPH`: enable graph enrichment on writes, default `1`

## Install

```bash
pip install mem0ai
```

## Quickstart

Export credentials:

```bash
export MGP_MEM0_API_KEY="..."
export MGP_MEM0_ORG_ID="..."
export MGP_MEM0_PROJECT_ID="..."
export MGP_MEM0_APP_ID="mgp-integration-test"
export MGP_MEM0_ENABLE_GRAPH="0"
```

Start the reference gateway with the Mem0 adapter:

```bash
MGP_ADAPTER=mem0 make serve
```

Then verify the adapter is reachable:

```bash
curl http://127.0.0.1:8080/mgp/capabilities
```

## Supported Capabilities

See [manifest.json](manifest.json).

Highlights:

- `supports_write: true`
- `supports_update: true`
- `supports_delete: true`
- `supports_purge: true`
- `supports_search: true`
- `supports_graph_relations: true`

## Known Limitations

- `get(memory_id)` and related lifecycle operations resolve the target by metadata lookup, not by a native Mem0 custom ID
- exact lookup performance depends on how efficiently Mem0 applies metadata filters for the configured account
- MGP lifecycle states (`expired`, `revoked`, `deleted`) are adapter-managed metadata semantics layered on top of Mem0
- native conflict detection, native dedupe, and native merge remain unsupported

## Validation

This adapter requires a real Mem0 service configuration. It is not part of the default local CI matrix.

Example manual validation:

```bash
MGP_ADAPTER=mem0 MGP_MEM0_API_KEY=... make test
```

Use `memory`, `file`, or `graph` adapters for offline protocol testing without external services.

## Live Validation Notes

This adapter has been validated against a real Mem0 project with:

- live `write`, `search`, `get`, `update`, `expire`, and `purge`
- metadata-based `memory_id` lookup
- adapter-vs-direct SDK comparison
- full HTTP gateway flow through `/mgp/write`, `/mgp/get`, `/mgp/search`, `/mgp/update`, `/mgp/expire`, and `/mgp/purge`

Observed differences versus calling Mem0 directly:

- the adapter preserves canonical MGP memory objects, while direct Mem0 calls return service-native records
- the adapter adds MGP lifecycle semantics (`expired`, `revoked`, `deleted`) on top of Mem0 metadata
- `get(memory_id)` requires a metadata lookup round-trip because Mem0 does not natively use MGP `memory_id`

Observed performance on the tested account:

- direct Mem0: add ~2.24s, get ~0.65s, search ~1.09s
- through MGP adapter: write ~4.37s, get ~0.69s, search ~1.30s
- through MGP HTTP gateway: write ~10.64s, get ~8.17s, search ~14.90s

The tested account did not have Mem0 graph memory enabled. The adapter therefore ran in semantic-only mode and advertised `supports_graph_relations: false` dynamically at runtime.
