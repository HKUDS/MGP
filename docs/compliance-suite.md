# Compliance Suite

This page introduces the runnable verification layer that backs MGP compatibility claims.

## Install

```bash
cd compliance
../.venv/bin/python -m pip install -r requirements.txt
```

Or install everything at once from the repository root:

```bash
make install
```

## Run

### In-Memory Adapter

```bash
cd compliance
../.venv/bin/python -m pytest
```

### File Adapter

```bash
cd compliance
MGP_ADAPTER=file ../.venv/bin/python -m pytest
```

### Graph Adapter

```bash
cd compliance
MGP_ADAPTER=graph ../.venv/bin/python -m pytest
```

### PostgreSQL Adapter

```bash
cd compliance
MGP_ADAPTER=postgres MGP_POSTGRES_DSN=postgresql://postgres:postgres@127.0.0.1:5432/mgp ../.venv/bin/python -m pytest
```

Or run all three at once:

```bash
make test-all
```

From the repository root:

- `make test` runs `python -m pytest compliance` for the selected `MGP_ADAPTER`
- `make test-all` repeats that same full suite for `memory`, `file`, and `graph`

## What This Verifies

- JSON schema conformance
- OpenAPI and schema alignment for shared wire-level fields
- contract drift checks across OpenAPI, README version markers, and reference gateway routes
- Core operation behavior
- Lifecycle and retention behavior
- Conflict behavior
- Access decision behavior
- Adapter compatibility and round-trip consistency
- Search result consumption contract
- Dedupe / upsert / merge reference behavior
- Delete / purge lifecycle semantics
- Audit correlation fields
- Interoperability endpoints for batch / export / import / sync

## Test Groups

Core compliance groups:

- `schema/test_schema_validation.py`
- `core/test_core_operations.py`
- `search/test_search_results.py`
- `lifecycle/test_lifecycle.py`
- `lifecycle/test_delete_purge.py`
- `conflicts/test_conflicts.py`
- `access/test_access_control.py`
- `audit/test_audit_contract.py`
- `dedupe/test_dedupe_upsert.py`
- `adapters/test_adapter_compat.py`

Optional protocol feature groups included in the reference suite:

- `interop/test_bulk_sync_export.py`
- `lifecycle/test_protocol_lifecycle.py`

These groups are optional at the ecosystem level, but the reference gateway and this repository's default pytest commands exercise them whenever the implementation supports the feature set under test.

## Conformance Profiles

When describing compatibility, prefer the profile names from [Conformance Profiles](conformance-profiles.md):

- `Core`
- `Lifecycle`
- `Interop`
- `ExternalService`

Repository interpretation:

- the in-repo `memory`, `file`, and `graph` matrix demonstrates `Core`, `Lifecycle`, and `Interop`
- `postgres` can validate the same profiles locally when `MGP_POSTGRES_DSN` is configured
- `ExternalService` applies to service-backed adapters such as `Mem0` and `Zep`, which require real provider environments for end-to-end validation

Capability interpretation note:

- the gateway may expose a broader HTTP surface than one backend supports natively
- adapter manifests must still report backend-native capability truthfully even when the gateway can emulate part of the behavior

## Interpreting Results

Passing the full suite means an implementation satisfies the MGP compliance expectations for:

- schema validity
- endpoint behavior
- governance semantics
- adapter manifest correctness

CI runs the full suite against:

- `memory`
- `file`
- `graph`

`make lint` complements the pytest suite by running schema validation, OpenAPI validation, and contract-drift checks before the broader test matrix.

## What "MGP Compliant" Means

Compliance means the implementation passes the published pytest suite in this directory against the defined MGP schemas and reference HTTP behavior.
