# Protocol Reference

This page is the curated map of the MGP protocol surface. It explains how the protocol documents, schemas, and HTTP binding relate to one another.

## Canonical Protocol Assets

MGP keeps protocol source material in three coordinated forms:

- `spec/` explains semantics and expected behavior.
- `schemas/` defines the canonical validation contracts.
- `openapi/mgp-openapi.yaml` describes the HTTP binding.

An implementation is aligned only when those three layers and the observable runtime behavior point in the same direction.

## Alignment Rule

- `spec/` remains the semantic source of truth for what an operation means.
- Operation-specific schemas under `schemas/` are the canonical machine-readable source for exact request and response shapes.
- `schemas/response-envelope.schema.json` is the shared outer response shell; endpoint-specific response schemas narrow `data` for the exact operation contract.
- `openapi/mgp-openapi.yaml` should mirror the HTTP mapping without inventing alternative wire shapes.

Contract enforcement in this repository:

- `scripts/validate_schemas.py` checks published schema validity
- `scripts/validate_openapi.py` checks the OpenAPI document and its references
- `scripts/check_contract_drift.py` checks that `spec/` / `schemas/` / `openapi/` / reference gateway versions and routes have not drifted
- CI runs those checks before the compliance matrix

## Core Object Model

The protocol is centered on a canonical memory object and the supporting request and response envelopes around it.

Key schema assets:

- `schemas/memory-object.schema.json`
- `schemas/memory-candidate.schema.json`
- `schemas/policy-context.schema.json`
- `schemas/request-envelope.schema.json`
- `schemas/response-envelope.schema.json`

The protocol also includes structured content schemas for common memory types such as preferences, semantic facts, relationships, and procedural rules.

## Modeling Quick Reference

Use these defaults unless your runtime has a stronger domain-specific reason to model things differently:

| Situation | `subject.kind` | `scope` | `acting_for_subject` | `task_id` | `session_id` |
| --- | --- | --- | --- | --- | --- |
| durable user preference or fact | `user` | `user` | current user | optional | optional |
| conversation-local memory | `user` or `session` | `session` | current user or current session subject | optional | current session |
| workflow-local memory | `task` or `user` | `task` | current user | current workflow/task | optional |
| agent-owned operational memory | `agent` | `agent` | current operator or owning subject | optional | optional |

Interpretation rule:

- `acting_for_subject` describes who the runtime is acting on behalf of for policy evaluation
- `subject` describes what the memory is about
- `task_id` identifies runtime workflow or execution correlation, not the protocol async task object returned by `/mgp/tasks/*`
- `session_id` is tracing and conversation identity, not a replacement for `scope: session`

## Core Operations

The core operation semantics live in `spec/core-operations.md` and are exposed through the reference HTTP binding.

Required governed-memory operations:

- write
- search
- get
- update
- expire
- revoke
- delete
- purge
- audit query

Required discovery support:

- `GET /mgp/capabilities`

Each operation is backed by request and response schemas under `schemas/` and by reference behavior in `reference/gateway/app.py`.

## Search And Runtime Consumption

MGP does not stop at raw retrieval. The protocol also defines how search results should be consumed safely by runtimes.

Primary references:

- `spec/search-results.md`
- `spec/protocol-behavior.md`
- `spec/runtime-client.md`
- `schemas/partial-failure.schema.json`
- `schemas/return-mode.schema.json`
- `schemas/retrieval-mode.schema.json`
- `schemas/score-kind.schema.json`

These documents explain result normalization, `consumable_text`, return modes, redaction-aware behavior, partial-failure reporting, and runtime-side handling.

## Governance Semantics

MGP treats governance as part of the protocol contract rather than a backend-specific extension.

Primary references:

- `spec/retention.md`
- `spec/conflicts.md`
- `spec/access-control.md`
- `spec/errors.md`
- `schemas/audit-event.schema.json`
- `schemas/lineage-link.schema.json`
- `schemas/memory-evidence.schema.json`

These assets describe retention, conflict handling, access outcomes, audit records, and lineage evidence.

## Lifecycle, Discovery, And Async

The protocol includes a required discovery surface plus optional lifecycle and interoperability profiles that sit above core memory operations.

Compatibility claims for those optional surfaces should use the profile names defined in [Conformance Profiles](conformance-profiles.md).

Primary references:

- `spec/lifecycle.md`
- `spec/async-operations.md`
- `spec/http-binding.md`
- `schemas/capabilities.response.schema.json`
- `schemas/initialize.request.schema.json`
- `schemas/initialize.response.schema.json`
- `schemas/async-task.schema.json`
- `schemas/get-task.request.schema.json`
- `schemas/get-task.response.schema.json`
- `schemas/cancel-task.request.schema.json`
- `schemas/cancel-task.response.schema.json`
- `schemas/write-batch.request.schema.json`
- `schemas/write-batch.response.schema.json`
- `schemas/export.request.schema.json`
- `schemas/export.response.schema.json`
- `schemas/import.request.schema.json`
- `schemas/import.response.schema.json`
- `schemas/sync.request.schema.json`
- `schemas/sync.response.schema.json`

These assets cover:

- capability discovery
- initialize negotiation
- batch write as an interoperability extension
- async export, import, and sync task handles
- task polling and cancellation

Interaction rule of thumb:

- `GET /mgp/capabilities` describes the implementation's general discovery surface
- `POST /mgp/initialize` describes what was negotiated for one interaction

## Runtime Contracts

MGP defines explicit runtime-facing guidance so that a client can behave consistently even across different backends.

Primary references:

- `spec/runtime-client.md`
- `spec/runtime-write-candidate.md`
- `schemas/runtime-capabilities.schema.json`
- `schemas/negotiated-capabilities.schema.json`

These assets cover policy-context mapping, candidate extraction, return-mode handling, and initialize-time runtime capability declaration.

## Extensions, Compatibility, And Versioning

Protocol evolution is documented separately from the core operation surface.

Primary references:

- `spec/extensions.md`
- `spec/versioning.md`

This layer defines how new features are added without breaking compatibility.

Use [Conformance Profiles](conformance-profiles.md) together with `spec/versioning.md` when describing implementation scope. Version numbers tell users what changed; profile names tell them which optional surfaces are actually supported.

Current guidance:

- the `mgp` namespace remains reserved for protocol-level extensions
- vendor namespaces should be declared in adapter manifests and documented in the repository documentation
- compatibility claims should be backed by observable schema, gateway, and compliance behavior

## Implementation Rule Of Thumb

Use the protocol assets in this order:

1. Start with the relevant `spec/` document to understand the intended behavior.
2. Confirm the exact request or response shape in `schemas/`.
3. Verify the HTTP surface in `openapi/mgp-openapi.yaml`.
4. Check the reference gateway and compliance suite to see the contract in executable form.
