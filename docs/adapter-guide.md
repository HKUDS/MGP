# Adapter Guide

This guide is the minimum template for authors who want to build an MGP-compatible adapter.

## Goal

An MGP adapter bridges a concrete backend into the MGP protocol surface.

Your adapter should:

- implement the adapter interface in `adapters/base.py`
- publish a valid `manifest.json`
- declare capabilities explicitly
- preserve the canonical memory object shape
- pass the compliance suite

## Required Files

Recommended structure:

```text
adapters/your-adapter/
  __init__.py
  adapter.py
  manifest.json
  README.md
```

## Implement the Base Interface

Your adapter should implement these methods from `adapters/base.py`:

- `write(memory)`
- `search(query, subject, scope, types, limit)`
- `get(memory_id)`
- `update(memory_id, patch)`
- `expire(memory_id, expired_at, reason)`
- `revoke(memory_id, revoked_at, reason)`
- `get_manifest()`

## Manifest Requirements

Your `manifest.json` must validate against:

- `schemas/adapter-manifest.schema.json`

It must declare:

- adapter name
- backend kind
- supported MGP version
- supported memory types
- supported scopes
- capabilities
- extension namespaces

## Capability Declaration

Do not leave capabilities ambiguous.

Use:

- `schemas/backend-capabilities.schema.json`

If your backend cannot do something natively, declare it as `false` even if the gateway may emulate it.

## Extension Handling

Follow:

- `spec/extensions.md`

Rules:

- do not mutate core field meanings
- keep vendor-specific data in `extensions`
- use namespaced keys like `vendor:key_name`
- preserve unknown extensions when possible

Boundary note:

- keep portable vendor semantics in `extensions`
- reserve `backend_ref` for opaque adapter-local handles or routing metadata

## README Checklist

Each adapter README should include:

- purpose
- storage model
- mapping rules
- supported capabilities
- known limitations
- compliance command

## Compliance

Run the compliance suite against your adapter:

```bash
cd compliance
MGP_ADAPTER=your-adapter ../.venv/bin/python -m pytest
```

Passing the suite is the baseline proof that your adapter is MGP-compatible.

## Recommended Workflow

1. Implement the adapter interface.
2. Write `manifest.json`.
3. Run schema validation on the manifest.
4. Run the compliance suite.
5. Document known limitations clearly.
