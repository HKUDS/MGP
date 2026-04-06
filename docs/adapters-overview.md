# Adapters Overview

This page summarizes the adapter families that currently live in the MGP repository and explains how they relate to the protocol contract.

## Adapter Role

An MGP adapter bridges a concrete backend model into the MGP protocol surface. Every adapter is expected to:

- implement the base adapter interface
- publish a valid `manifest.json`
- declare capabilities explicitly
- preserve the canonical memory object shape
- expose clear limitations

See also: [Adapter Guide](adapter-guide.md).

## Production Note

The in-memory, file, and graph adapters included in this repository are **reference implementations**. They are designed for:

- protocol verification and compliance testing
- demonstrating how different backend shapes map to the MGP contract
- serving as starting points for adapter authors

They are **not intended for production use**. For production deployments, build or adopt adapters that target your actual storage infrastructure. See the [Adapter Guide](adapter-guide.md) for how to create your own adapter.

Mem0 and Zep are different: they are **service-backed adapters** that target real external memory services. They are suitable for real deployments when those services are configured and available.

The PostgreSQL adapter is different again: it is a **production-oriented baseline adapter** intended to show how a relational backend can be used as a real deployment path without tying MGP to one managed memory vendor.

The LanceDB adapter follows the same deployment shape as PostgreSQL, but for vector-native memory retrieval. It is a **production-oriented self-managed adapter** for teams that want semantic or hybrid recall over canonical MGP memory objects without depending on a hosted memory service.

For live usage:

- Mem0 requires API credentials and project scoping
- Zep requires API credentials and a shared graph namespace
- both adapters introduce a small amount of latency over direct SDK calls because they add MGP normalization and lifecycle semantics

## Reference Adapter Families

### In-Memory Adapter

Source:

- `adapters/memory/adapter.py`
- `adapters/memory/README.md`

Role:

- baseline reference adapter
- lowest-friction compliance target
- easiest place to inspect protocol behavior in memory

### File Adapter

Source:

- `adapters/file/adapter.py`
- `adapters/file/README.md`

Role:

- persistent JSON-file storage example
- simple proof that MGP is not tied to a database product

### Graph Adapter

Source:

- `adapters/graph/adapter.py`
- `adapters/graph/README.md`

Role:

- relationship-oriented reference adapter
- demonstrates extension-driven graph semantics

### PostgreSQL Adapter

Source:

- `adapters/postgres/adapter.py`
- `adapters/postgres/README.md`
- `adapters/postgres/migrations/`

Role:

- production-oriented SQL adapter baseline
- demonstrates persistent multi-tenant storage, indexed search, and lifecycle state handling
- suitable as a starting point for teams that want to run MGP against their own relational infrastructure

### LanceDB Adapter

Source:

- `adapters/lancedb/adapter.py`
- `adapters/lancedb/README.md`

Role:

- production-oriented vector adapter baseline
- demonstrates canonical memory storage, semantic search, and optional hybrid recall on LanceDB
- suitable as a starting point for teams that want to run MGP against self-managed vector infrastructure

### Mem0 Adapter

Source:

- `adapters/mem0/adapter.py`
- `adapters/mem0/README.md`

Role:

- service-backed Mem0 adapter
- uses Mem0 as the source of truth
- production-oriented integration path for teams already using Mem0

### Zep Adapter

Source:

- `adapters/zep/adapter.py`
- `adapters/zep/README.md`

Role:

- service-backed Zep adapter
- uses Zep episodes as the source of truth
- production-oriented integration path for teams already using Zep Cloud

## Verification Expectations

Current CI coverage:

- full compliance runs on `memory`
- full compliance runs on `file`
- full compliance runs on `graph`

Optional local validation paths:

- `postgres` can run the same suite when `MGP_POSTGRES_DSN` is configured
- `lancedb` can run the same suite when LanceDB and an embedding configuration are available
- external-service adapters require their corresponding service environments to validate end to end

Profile interpretation:

- `memory`, `file`, and `graph` participate in the default `Core` + `Lifecycle` + `Interop` reference matrix
- `postgres` is a production-oriented adapter path that can exercise the same profiles outside the default CI matrix
- `lancedb` is a production-oriented self-managed adapter path that can exercise the same profiles outside the default CI matrix
- `mem0` and `zep` are `ExternalService` adapters whose validation depends on real provider environments

See also: [Conformance Profiles](conformance-profiles.md).

## Manifest And Capability Model

Every adapter ships a `manifest.json` that declares:

- backend kind
- supported MGP version
- supported memory types and scopes
- backend capabilities
- extension namespaces

Interpretation rule:

- these capabilities describe backend-native or adapter-native support
- they do not expand or shrink the HTTP surface that a gateway may expose through policy or emulation layers

Primary contract files:

- `schemas/adapter-manifest.schema.json`
- `schemas/backend-capabilities.schema.json`
- `adapters/*/manifest.json`

## Implementation Boundary

Adapters are allowed to differ in storage layout, indexing strategy, conflict support, TTL support, and graph support. They are not allowed to silently redefine the core protocol contract.

That means:

- protocol semantics stay stable
- backend-specific behavior must be declared
- vendor-specific fields belong in `extensions`
