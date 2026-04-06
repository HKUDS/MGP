# Scope

This document defines what MGP is responsible for in its first protocol iterations.

## Scope Statement

MGP governs persistent and semi-persistent memory interactions in AI systems. It standardizes the contract between runtimes and memory backends so that memory can be written, searched, retrieved, updated, expired, revoked, and audited in a consistent way across heterogeneous implementations.

## In Scope

### Memory Objects

MGP defines a canonical shape for memory objects that can represent user facts, preferences, episodic events, semantic knowledge, and other governed memory units.

### Memory Operations

MGP defines protocol-level operations for:

- write
- search
- get
- update
- expire
- revoke
- delete
- purge

These operations are defined as protocol contracts, not backend-specific implementation details.

### Policy Context Propagation

MGP defines how a runtime communicates the context of a memory action, including who is acting, on whose behalf the action occurs, and the task or risk context attached to the request.

### Lifecycle Semantics

MGP defines protocol hooks for retention, expiration, supersession, and revocation so that memory governance is not reduced to raw CRUD.

### Conflict Semantics

MGP defines how runtimes and backends express conflicting memories, contradiction handling, and conflict resolution modes.

### Audit and Lineage

MGP defines schemas and contracts for audit events and lineage links so that memory reads and writes can be inspected, reasoned about, and traced over time.

### Capability Declaration

MGP defines how a backend or adapter declares supported protocol features, enabling runtimes to reason about partial support without assuming uniform backend behavior.

### Protocol Bindings

MGP owns its own wire format and transport bindings. The initial intended binding is JSON over HTTP, with future support for additional bindings such as gRPC.

## Out of Scope

### Prompt Window Management

MGP does not define how prompt context windows are assembled, compressed, or truncated at inference time.

### General Logging

MGP does not replace application logging, observability, or tracing systems.

### Full Workflow State

MGP does not attempt to model the full semantics of workflow engines, orchestration frameworks, or general-purpose application state machines.

### Memory Generation Algorithms

MGP does not decide what should become memory, when memory extraction should happen, or what summarization pipeline should be used.

### Embeddings and Ranking

MGP does not define embedding algorithms, similarity math, ranking models, or retrieval scoring logic.

### Tool and Resource Connectivity

MGP does not standardize tool invocation or generic resource access. That is a separate concern addressed by protocols such as MCP.

## Design Principles

- Governed memory is a first-class protocol concern.
- The protocol must work across multiple backend styles.
- Core semantics must remain stable even when backend capabilities differ.
- MGP should standardize contracts, not force a single implementation.
