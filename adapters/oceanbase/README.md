# OceanBase Adapter

Production-shaped OceanBase adapter for MGP, implemented on top of `pyobvector`.

## Goal

This adapter mirrors the `postgres` adapter's core lifecycle semantics while using
OceanBase as the backing SQL engine.

The primary target is standard OceanBase deployment. The adapter also supports
running on OceanBase seekdb, which is a lightweight, single-node, embeddable
variant of OceanBase suited to resource-constrained environments:

- canonical memory payload storage
- idempotent upsert by `memory_id`
- soft lifecycle states and hard purge
- lexical search over normalized memory payloads

## Requirements

- OceanBase reachable over the MySQL-compatible port
- `pyobvector` installed together with a compatible `sqlglot`
- connection settings provided through either `MGP_OCEANBASE_DSN` or granular env vars

Recommended installation:

```bash
pip install pyobvector sqlglot==26.0.1
```

Example environment:

```bash
export MGP_ADAPTER=oceanbase
export MGP_OCEANBASE_DSN='mysql://root:oblab@127.0.0.1:2881/test?tenant=sys'
```

Or with explicit fields:

```bash
export MGP_ADAPTER=oceanbase
export MGP_OCEANBASE_URI='127.0.0.1:2881'
export MGP_OCEANBASE_USER='root'
export MGP_OCEANBASE_PASSWORD='oblab'
export MGP_OCEANBASE_TENANT='sys'
export MGP_OCEANBASE_DATABASE='test'
```

## Docker Quick Start

For lightweight local validation, this repository uses the official
`OceanBase seekdb` image:

```bash
docker run -d --name oceanbase-test \
  -p 2881:2881 \
  -p 2886:2886 \
  -e ROOT_PASSWORD=oblab \
  oceanbase/seekdb:latest
```

This validates the OceanBase adapter against OceanBase seekdb compatibility.
The adapter uses the SQLAlchemy-compatible client exposed by `pyobvector`.

## Capability Notes

- search mode is `lexical`
- timestamps are stored as ISO-8601 strings for broad OceanBase compatibility
- lifecycle and prompt-safe behavior remain gateway-managed

## Running The Compliance Suite

```bash
export MGP_ADAPTER=oceanbase
export MGP_OCEANBASE_DSN='mysql://root:oblab@127.0.0.1:2881/test?tenant=sys'
./.venv/bin/python -m pytest compliance
```

Adapter-specific checks:

```bash
export MGP_ADAPTER=oceanbase
export MGP_OCEANBASE_DSN='mysql://root:oblab@127.0.0.1:2881/test?tenant=sys'
./.venv/bin/python -m pytest compliance/adapters/test_oceanbase_adapter.py
```
