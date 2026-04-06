# Landscape

This document positions MGP relative to adjacent standards, formats, and products in the AI memory ecosystem.

## Positioning Summary

MGP exists in a gap that is increasingly visible:

- runtimes need durable memory
- backends expose incompatible APIs and governance models
- export formats do not solve runtime interoperability
- tool connectivity standards do not solve memory governance

MGP targets that gap by defining a memory-specific protocol with lifecycle, policy, conflict, and audit semantics.

## Adjacent Standards and Systems

### MCP

MCP is a peer protocol, not a parent protocol.

MCP standardizes how runtimes connect to tools and resources. MGP standardizes how runtimes govern and access memory. They are complementary and can coexist in the same runtime, but one does not sit underneath the other.

### PAM

Portable AI Memory focuses on export and import portability for memory data.

PAM is closest to a vCard-style interchange format for memories. That makes it useful for data portability, migration, and archival. It does not by itself solve live runtime operations such as governed write, search, lifecycle control, conflict handling, or backend capability negotiation.

### MIF

Memory Interchange Format is another portability-oriented format with provenance features.

Like PAM, it is useful reference material for portability concerns, but it is narrower than a runtime memory governance protocol.

### Mem0

Mem0 is a managed memory service and platform.

It occupies the backend or service layer, not the protocol-standard layer. In an MGP ecosystem, Mem0 is the kind of system that could sit behind an adapter or direct backend integration.

### Zep

Zep is a graph-native memory service.

Like Mem0, it represents an implementation target rather than a protocol peer. Its existence reinforces the need for capability declarations because graph-native backends expose different strengths from file or vector-backed memory systems.

### MemGPT and Letta

MemGPT and Letta are runtime and framework-level systems with their own memory models.

They are relevant because they show the demand for structured memory management in agents. In an MGP ecosystem, they are better understood as potential runtime consumers than as protocol substitutes.

## Relationship Matrix

| Name | Category | Primary concern | Relationship to MGP |
| --- | --- | --- | --- |
| MCP | Protocol | Tool and resource connectivity | Peer protocol |
| PAM | Format | Memory export and import portability | Complementary format |
| MIF | Format | Memory interchange and provenance | Complementary format |
| Mem0 | Product / service | Managed memory backend | Potential backend |
| Zep | Product / service | Graph-native memory backend | Potential backend |
| MemGPT / Letta | Runtime / framework | Agent memory management inside a runtime | Potential consumer |

## Why MGP Still Has Value

Even with the systems above, there is still no widely adopted protocol that simultaneously standardizes:

- canonical memory objects
- governed runtime operations
- policy context propagation
- lifecycle semantics
- conflict contracts
- audit and lineage contracts
- backend capability declarations
- compatibility and compliance testing

That gap is the reason MGP is worth pursuing.
