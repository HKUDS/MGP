# LanceDB Adapter

Production-oriented LanceDB adapter for MGP.

## Goal

This adapter maps canonical MGP memory objects onto a local or self-managed LanceDB table.

It is intended to show how a vector database backend can support:

- persistent governed memory storage
- semantic recall over canonical memory objects
- optional hybrid recall through LanceDB full-text search
- soft delete and hard purge while preserving MGP lifecycle semantics
- self-hosted deployment paths that do not depend on a managed memory vendor

## Requirements

- Python environment with `lancedb` installed
- a writable database directory in `MGP_LANCEDB_DIR` or `--lancedb-dir`
- an embedding provider configuration

## Supported Embedding Providers

The adapter can use:

- `fake` for deterministic offline testing
- `openai`
- `openrouter` via the OpenAI-compatible API surface
- `gemini-text`
- any other provider exposed through the LanceDB embedding registry

Recommended environment variables:

- `MGP_LANCEDB_EMBEDDING_PROVIDER`
- `MGP_LANCEDB_EMBEDDING_MODEL`
- `MGP_LANCEDB_EMBEDDING_API_KEY`
- `MGP_LANCEDB_EMBEDDING_BASE_URL`
- `MGP_LANCEDB_EMBEDDING_DIM` for the `fake` provider

OpenRouter example:

```bash
export MGP_ADAPTER=lancedb
export MGP_LANCEDB_DIR=./data/lancedb
export MGP_LANCEDB_TABLE=memories
export MGP_LANCEDB_ENABLE_HYBRID=1
export MGP_LANCEDB_EMBEDDING_PROVIDER=openrouter
export MGP_LANCEDB_EMBEDDING_MODEL=openai/text-embedding-3-small
export MGP_LANCEDB_EMBEDDING_API_KEY=...
export MGP_LANCEDB_EMBEDDING_BASE_URL=https://openrouter.ai/api/v1
```

Offline test example:

```bash
export MGP_ADAPTER=lancedb
export MGP_LANCEDB_DIR=./data/lancedb
export MGP_LANCEDB_EMBEDDING_PROVIDER=fake
export MGP_LANCEDB_EMBEDDING_MODEL=mgp-fake-embedding-v1
```

## Storage Model

The adapter stores each memory as one LanceDB row with:

- normalized lookup fields such as subject, scope, type, and state
- `search_text` and `consumable_text` for retrieval and prompt-safe consumption
- a `vector` column for semantic recall
- `memory_json` containing the full canonical MGP memory object

This preserves unknown `extensions` across round trips while still giving the adapter efficient filter columns.

## Mapping Rules

- `backend_ref.adapter` is always `lancedb`
- `backend_ref.mgp_state` is one of `active`, `expired`, `revoked`, or `deleted`
- the full canonical MGP object is restored from `memory_json`
- hybrid search uses LanceDB FTS plus vector search when enabled
- delete is a soft-delete implemented by state transition
- purge is a hard delete implemented by removing the LanceDB row

## Capability Notes

- search modes are `semantic`, or `semantic` + `hybrid` when FTS setup succeeds
- prompt-safe views are still produced at the gateway policy layer
- TTL is adapter-managed and policy-enforced, not a LanceDB native expiration feature
- conflict detection, merge, and write-time dedupe remain gateway-level behaviors

## Running The Compliance Suite

For a deterministic local run:

```bash
export MGP_ADAPTER=lancedb
export MGP_LANCEDB_DIR=./data/lancedb
export MGP_LANCEDB_EMBEDDING_PROVIDER=fake
export MGP_LANCEDB_EMBEDDING_MODEL=mgp-fake-embedding-v1
make test
```

Or run the suite directly:

```bash
MGP_ADAPTER=lancedb ./.venv/bin/python -m pytest compliance
```

## Known Limitations

- graph-native relationship retrieval is not supported
- TTL is adapter-managed rather than native to LanceDB
- hybrid search depends on LanceDB FTS support and may fall back to semantic-only mode
- changing the embedding model or vector dimension for an existing non-empty table is treated as a configuration error
