# PostgreSQL Adapter

Production-oriented PostgreSQL adapter for MGP.

## Goal

This adapter provides a more deployment-shaped baseline than the in-memory, file, and graph reference adapters.

It is intended to show how a relational backend can support:

- persistent governed memory storage
- multi-tenant scoping fields
- soft delete and hard purge
- indexed search over normalized memory payloads
- idempotent upsert by `memory_id`

## Requirements

- PostgreSQL 14+
- `psycopg` installed in the Python environment
- a connection string in `MGP_POSTGRES_DSN`

Example:

```bash
export MGP_ADAPTER=postgres
export MGP_POSTGRES_DSN='postgresql://postgres:postgres@127.0.0.1:5432/mgp'
```

## Schema

The adapter applies SQL files from `migrations/` on startup.

Current schema includes:

- `mgp_memories` table for canonical memory payload storage
- tenant, subject, scope, type, and state columns for operational filtering
- JSONB storage for the full canonical memory object
- indexes for tenant/state, subject, scope/type, created time, and JSONB payload lookup

## Capability Notes

- search mode is `lexical`
- prompt-safe views are still produced at the gateway policy layer
- TTL is tracked through lifecycle and policy semantics rather than native database expiration
- conflict detection, dedupe, and merge remain gateway-level behaviors in this version

## Running The Compliance Suite

The default CI matrix does not run PostgreSQL automatically.

To validate locally:

```bash
export MGP_ADAPTER=postgres
export MGP_POSTGRES_DSN='postgresql://postgres:postgres@127.0.0.1:5432/mgp'
make test
```

Or run the full suite against the postgres adapter explicitly:

```bash
MGP_ADAPTER=postgres ./.venv/bin/python -m pytest compliance
```
