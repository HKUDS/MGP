# When To Use MGP

This page explains when MGP is the right abstraction and when a simpler library or direct provider SDK is enough.

## Use MGP When

MGP is a strong fit when you need one or more of the following:

- multiple runtimes or teams must share one governed memory contract
- you want memory lifecycle controls such as `expire`, `revoke`, `delete`, and `purge`
- you need auditability and policy context to travel with memory operations
- you want backend portability without rewriting runtime-side memory code
- you need compliance-style verification rather than trusting one provider SDK implicitly

In short:

- use MGP when memory is infrastructure
- use a lightweight library when memory is just an implementation detail

## A Good Fit For Runtime Teams

If you are building an agent runtime, MGP is useful when:

- prompt construction depends on durable recall across sessions
- you need a consistent prompt-safe result shape such as `consumable_text`
- you want to add memory through a sidecar first and move to a native SDK later
- you expect to switch between self-managed and external backends over time

## A Good Fit For Platform Teams

If you are building a platform, MGP is useful when:

- you need one contract for file, relational, graph, and service-backed memory systems
- you want adapters to declare capability truthfully
- you need to inspect or govern memory behavior without coupling to one vendor
- you want a reference gateway, OpenAPI surface, and schemas that can be versioned separately from app code

## A Good Fit For Protocol Implementers

If you want to implement a gateway or adapter, MGP gives you:

- semantic guidance in `spec/`
- machine-readable contracts in `schemas/`
- an HTTP binding in `openapi/`
- executable validation in `compliance/`

That combination is the main reason to use MGP instead of inventing an internal memory API.

## When A Simpler Library Is Enough

You may not need MGP yet if:

- one Python application talks to one memory provider
- you only need a small abstraction layer over provider APIs
- audit, lifecycle, and compatibility claims are not a requirement
- you are still exploring product shape and do not want protocol overhead

In those cases, a small library or direct SDK can be faster to adopt.

## Relationship To Provider SDKs And Libraries

MGP is not trying to replace every application-level memory SDK.

Think of the layers this way:

- direct provider SDKs optimize for one backend
- lightweight libraries optimize for app-level convenience
- MGP optimizes for governed interoperability across runtimes and backends

That means MGP can sit above a provider SDK or library through an adapter when governance and portability matter.

## Adoption Paths

Common starting points:

1. Start with the reference gateway and `mgp-client`.
2. Add MGP in `shadow` mode through a sidecar.
3. Move to a native SDK path once runtime behavior is stable.
4. Introduce a production-oriented backend such as PostgreSQL when you need a self-managed deployment path.
