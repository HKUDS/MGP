# Conformance Profiles

This page defines the profile vocabulary MGP uses when describing compatibility and implementation scope.

The goal is to make compatibility claims precise. A gateway, adapter, or SDK should state which profiles it supports and how that support is verified.

## Why Profiles Exist

MGP has a wider surface than a single CRUD API:

- core governed-memory operations
- lifecycle controls
- interoperability and async transfer flows
- external service adapters that depend on real provider environments

Profiles make it possible to say "this implementation supports MGP Core and Lifecycle" without implying that every optional surface is available.

## Profile Definitions

### Core

The `Core` profile is the minimum surface required to claim general MGP compatibility.

It covers:

- canonical memory objects and policy context
- request and response envelopes
- `write`, `search`, `get`, `update`
- `audit query`
- `GET /mgp/capabilities`
- search result normalization and `consumable_text`
- contract-level error handling

Primary sources:

- `spec/core-operations.md`
- `spec/search-results.md`
- `spec/protocol-behavior.md`
- `schemas/memory-object.schema.json`
- `schemas/policy-context.schema.json`
- `schemas/request-envelope.schema.json`
- `schemas/response-envelope.schema.json`

### Lifecycle

The `Lifecycle` profile adds governed state transitions on top of `Core`.

It covers:

- `expire`
- `revoke`
- `delete`
- `purge`
- lifecycle initialization and version negotiation through `POST /mgp/initialize`
- retention and revocation semantics

Primary sources:

- `spec/lifecycle.md`
- `spec/retention.md`
- `spec/versioning.md`

### Interop

The `Interop` profile adds transfer-oriented and async protocol features on top of `Core`.

It covers:

- `/mgp/write/batch`
- `/mgp/export`
- `/mgp/import`
- `/mgp/sync`
- async task handles and polling
- partial-failure reporting where supported

Primary sources:

- `spec/async-operations.md`
- `spec/http-binding.md`
- `schemas/async-task.schema.json`
- `schemas/partial-failure.schema.json`

### ExternalService

The `ExternalService` profile is for service-backed adapters that rely on a real provider environment.

It covers:

- provider-backed adapters such as `Mem0` and `Zep`
- provider-specific capability declarations
- environment-specific validation outside the default in-repo CI matrix

This profile does not replace `Core`, `Lifecycle`, or `Interop`. It describes how those profiles are validated when a real external backend is required.

## Verification Matrix

| Profile | Required to claim | Typical evidence |
| --- | --- | --- |
| `Core` | general MGP compatibility | schema validation, gateway behavior, core compliance tests |
| `Lifecycle` | governed state transition support | lifecycle compliance tests, initialize negotiation behavior |
| `Interop` | batch/export/import/sync support | async and interop compliance tests, task contract validation |
| `ExternalService` | real provider-backed adapter support | manifest review, provider documentation, opt-in integration validation |

## Repository Coverage

Current repository behavior:

- the reference gateway implements `Core`, `Lifecycle`, and `Interop`
- CI runs the full reference suite against `memory`, `file`, and `graph`
- `postgres` and `lancedb` are self-managed production-oriented adapter paths that can validate the same profiles outside the default CI matrix
- `mem0` and `zep` are documented service-backed adapters, but they require provider environments and are not part of the default CI matrix

## Claim Rules

Implementations should make claims with profile names, not vague labels such as "fully compatible".

Recommended wording:

- "Supports `Core`"
- "Supports `Core` + `Lifecycle`"
- "Supports `Core` + `Lifecycle` + `Interop`"
- "Supports `Core` through an `ExternalService` adapter validated in a provider environment"

Do not claim a profile unless:

- the relevant schemas are implemented
- the relevant HTTP or SDK surface is exposed
- the behavior is covered by executable validation, not only documentation
