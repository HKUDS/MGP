# Non-Goals

This document records the things MGP explicitly does not try to solve.

## MGP Is Not a Memory Store

MGP does not ship its own canonical database engine. It is a protocol for governed memory interoperability, not a new storage product.

## MGP Does Not Replace Existing Databases

MGP is not a replacement for:

- vector databases
- graph databases
- relational databases
- document stores
- file-backed memory systems

Those systems remain valid implementations behind MGP adapters or gateways.

## MGP Does Not Define Retrieval Science

MGP does not define:

- embedding algorithms
- similarity functions
- ranking models
- relevance scoring models
- summarization quality metrics

Implementations may use any suitable retrieval stack as long as they can present MGP-compatible behavior at the protocol layer.

## MGP Does Not Define Vendor-Internal Policy Engines

MGP standardizes the contract surface for policy context and policy outcomes. It does not require a specific authorization engine, rule language, or internal permission model.

## MGP Is Not an Agent Framework

MGP does not provide orchestration, planning, chat UX, tool routing, or multi-agent runtime behavior. It is intended to be consumed by runtimes, not replace them.

## MGP Is Not a Hosted Service

MGP is not a SaaS platform, control plane, or admin console.

## MGP Is Not a Static Export Format

MGP is not trying to replace interchange formats such as PAM or MIF. Those formats focus on portability across exports and imports. MGP focuses on live runtime governance and backend interoperability.

## MGP Is Not a Sub-Layer of MCP

MGP is an independent peer protocol, not an extension, transport profile, or subordinate layer of MCP.

MCP addresses tool and resource connectivity. MGP addresses governed memory. A runtime may implement both, but each protocol owns its own contract.

## MGP Does Not Normalize Every Native Feature

MGP will not attempt to expose every advanced, vendor-specific backend capability through the core protocol. Implementations may expose extensions, but the core protocol must remain portable and stable.
