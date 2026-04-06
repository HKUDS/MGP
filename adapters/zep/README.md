# Zep Adapter

Zep-backed MGP adapter.

## Purpose

This adapter maps MGP canonical memory objects onto Zep Cloud and treats Zep episodes as the source of truth.

It is intended for:

- service-backed memory storage on Zep
- semantic recall over Zep graph episodes
- graph-oriented relationship memory backed by Zep graph ingestion

It is not a compatibility wrapper around the local file adapter.

## Storage Model

The adapter stores each MGP memory as a Zep graph episode:

- the episode `content` stores a JSON payload containing the full canonical MGP memory
- the episode `source_description` stores a compact MGP index record (`memory_id`, state, subject, scope, type)
- `backend_ref.zep_episode_uuid` stores the Zep episode UUID when available

This gives the adapter a durable canonical source without maintaining local files.

## Mapping Rules

- `backend_ref.adapter` is always `zep`
- `backend_ref.mgp_state` is one of `active`, `expired`, `revoked`, or `deleted`
- the canonical MGP object is reconstructed from episode content
- relationship memories use Zep graph ingestion and are surfaced as `retrieval_mode = graph`
- delete is a soft-delete implemented by replacing the active episode with a tombstone episode
- purge is a hard delete implemented through `graph.episode.delete()`

## Required Environment Variables

- `MGP_ZEP_API_KEY` or `ZEP_API_KEY`: Zep API key

## Optional Environment Variables

- `MGP_ZEP_BASE_URL`: optional API base URL override
- `MGP_ZEP_GRAPH_USER_ID`: shared Zep graph namespace used by the adapter, default `mgp-global`
- `MGP_ZEP_RERANKER`: optional reranker for episode search
- `MGP_ZEP_IGNORE_ROLES`: comma-separated roles ignored when mirroring conversational turns into threads
- `MGP_ZEP_RETURN_CONTEXT`: whether thread writes should ask Zep to return context blocks

## Install

```bash
pip install zep-cloud
```

## Quickstart

Export credentials:

```bash
export MGP_ZEP_API_KEY="..."
export MGP_ZEP_GRAPH_USER_ID="mgp-integration-test"
```

Start the reference gateway with the Zep adapter:

```bash
MGP_ADAPTER=zep make serve
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

- `get(memory_id)` and lifecycle operations resolve records by scanning episodes inside the configured shared graph namespace
- Zep does not expose a native custom ID field for MGP `memory_id`, so lookup depends on `source_description`
- update is implemented as episode replacement, not in-place mutation
- semantic search quality depends on how effectively Zep indexes the JSON-backed episode payload
- Zep graph edges and summaries are treated as enrichment; the canonical MGP memory still comes from the stored episode payload

## Validation

This adapter requires a real Zep account and is not part of the default local CI matrix.

Example manual validation:

```bash
MGP_ADAPTER=zep MGP_ZEP_API_KEY=... make test
```

Use `memory`, `file`, or `graph` adapters for offline protocol testing without external services.

## Live Validation Notes

This adapter has been validated against a real Zep Cloud account with:

- live `write`, `search`, `get`, `update`, `expire`, and `purge`
- episode-based source of truth reconstruction
- adapter-vs-direct SDK comparison
- full HTTP gateway flow through `/mgp/write`, `/mgp/get`, `/mgp/search`, `/mgp/update`, `/mgp/expire`, and `/mgp/purge`

Observed differences versus calling Zep directly:

- direct Zep graph ingestion works on episodes and service UUIDs; the adapter restores canonical MGP memory objects and MGP `memory_id`
- direct `graph.add()` responses may not expose the final `source_description` until the episode finishes processing; the adapter waits for the processed episode before relying on it
- the adapter resolves `get(memory_id)` by scanning episodes in the configured Zep graph namespace

Observed performance on the tested account:

- direct Zep: add ~3.34s, get ~0.35s, search ~0.40s
- through MGP adapter: write ~7.50s, get ~0.78s, search ~1.06s
- through MGP HTTP gateway: write ~13.92s, get ~1.89s, search ~1.23s

This overhead is expected because the adapter adds MGP normalization, lifecycle metadata handling, and episode-resolution logic on top of the native Zep APIs.
