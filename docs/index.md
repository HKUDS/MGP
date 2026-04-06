# MGP Documentation

Welcome to the **Memory Governance Protocol** documentation. MGP is an open protocol that standardizes how AI runtimes write, recall, govern, and audit persistent memory across heterogeneous backends.

**New here?** Jump straight to the **[Getting Started](getting-started.md)** guide — you'll have a governed memory gateway running in under five minutes.

## What Is MGP?

MGP defines a unified contract for governed memory without becoming a memory database itself. Your agent runtime talks to one protocol, and any compliant memory backend just works — whether it's in-memory, file-based, graph-oriented, relational, vector, or a managed service.

MGP is a **peer protocol to MCP**. MCP handles tools and resources; MGP handles persistent memory. They complement each other and can coexist in the same runtime.

## Reading Paths

### I want to build something quickly

1. [Getting Started](getting-started.md) — install, run the gateway, write & search your first memory
2. [Python SDK](python-sdk.md) — `MGPClient`, `AsyncMGPClient`, and helpers
3. [Examples Overview](examples-overview.md) — runnable end-to-end demos

### I want to understand the protocol

1. [Project Overview](project-overview.md) — goals, boundaries, and architecture
2. [Architecture](architecture.md) — layered view and request flow
3. [Protocol Reference](protocol-reference.md) — full operation semantics
4. [Schema Reference](schema-reference.md) — all JSON Schemas explained
5. [MGP vs MCP](mgp-vs-mcp.md) — how the two protocols relate

### I want to integrate or deploy

1. [Reference Implementation](reference-implementation.md) — the Python gateway
2. [Adapter Guide](adapter-guide.md) — build your own adapter
3. [Sidecar Integration](sidecar-integration.md) — bridge an existing runtime
4. [Deployment Guide](deployment-guide.md) — production deployment patterns
5. [Security Baseline](security-baseline.md) — security considerations

### I want to verify compliance

1. [Conformance Profiles](conformance-profiles.md) — `Core`, `Lifecycle`, `Interop`, `ExternalService`
2. [Compliance Suite](compliance-suite.md) — run the test suite
3. [Adapters Overview](adapters-overview.md) — adapter compatibility matrix

## Full Site Map

**Overview**

- [Project Overview](project-overview.md)
- [Architecture](architecture.md)
- [Scope](scope.md)
- [Non-Goals](non-goals.md)
- [Landscape](landscape.md)
- [Glossary](glossary.md)
- [MGP vs MCP](mgp-vs-mcp.md)
- [When To Use MGP](when-to-use-mgp.md)

**Protocol**

- [Protocol Reference](protocol-reference.md)
- [Schema Reference](schema-reference.md)
- [Conformance Profiles](conformance-profiles.md)

**Implementations**

- [Reference Implementation](reference-implementation.md)
- [Adapter Guide](adapter-guide.md)
- [Adapters Overview](adapters-overview.md)
- [Python SDK](python-sdk.md)

**Quality & Integration**

- [Compliance Suite](compliance-suite.md)
- [Sidecar Integration](sidecar-integration.md)
- [Examples Overview](examples-overview.md)
- [Deployment Guide](deployment-guide.md)
- [Operator Guide](operator-guide.md)
- [Security Baseline](security-baseline.md)
- [Contributing](contributing.md)
