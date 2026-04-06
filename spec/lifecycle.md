# Lifecycle

This document defines the minimal lifecycle contract for `MGP v0.1`.

## Purpose

MGP already defines rich memory semantics, but a mature protocol also needs a stable way to:

- discover protocol metadata
- initialize a connection or interaction
- decide when the peer is ready for normal operations
- leave room for future session, async, and notification features

This document introduces the first minimal lifecycle profile without forcing MGP to become a stateful protocol immediately.

## Lifecycle Phases

MGP currently recognizes these high-level phases:

1. `discover`
2. `initialize`
3. `ready`
4. `operation`
5. `shutdown`

In the current stateless HTTP profile:

- `discover` is performed with `GET /mgp/capabilities`
- `initialize` is performed with `POST /mgp/initialize`
- `ready` is represented by a successful initialize response
- `operation` covers normal memory requests such as `write`, `search`, `get`, and lifecycle operations
- `shutdown` has no explicit protocol message yet and is handled by normal HTTP connection teardown

## Discovery

Discovery is intentionally lightweight and remains separate from initialization.

Current behavior:

- clients may call `GET /mgp/capabilities` before any other request
- this returns adapter/backend discovery metadata plus protocol-layer discovery metadata
- discovery does not imply that a stateful protocol session was created

## Initialize

Machine-readable schemas:

- `schemas/initialize.request.schema.json`
- `schemas/initialize.response.schema.json`

The initialize request is the first explicit lifecycle handshake for MGP.

Minimum request fields:

- `request_id`
- `client`

Version selection fields:

- legacy shorthand: `protocol_version`
- negotiated form: `supported_versions`
- optional negotiated preference: `preferred_version`

Optional request fields:

- `requested_capabilities`
- `runtime_capabilities`
- `requested_profiles`
- `transport_profile`

Minimum successful response fields:

- `chosen_version`
- `supported_versions`
- `lifecycle_phase`
- `session_mode`
- `transport_profile`
- `protocol_capabilities`
- `negotiated_capabilities`
- `negotiated_profiles`
- `server_info`

## Stateless HTTP Profile

The reference gateway currently implements a minimal `stateless_http` profile.

Behavior rules:

- `initialize` is supported
- `initialize` is recommended before advanced capabilities or future profile-gated behavior
- `initialize` is not required before normal CRUD-style MGP operations
- a successful initialize response means the peer is logically in `ready` state for that interaction
- the initialize response does not currently establish a protocol-level session identifier
- each subsequent operation remains independently processable as a normal stateless HTTP request

This keeps current integrations backward compatible while still creating a proper lifecycle surface for future protocol growth.

## Readiness

The current ready signal is:

- `status: ok`
- `data.lifecycle_phase = "ready"`

Future transport profiles may define:

- persistent protocol sessions
- resumed ready states
- server-initiated notifications after initialization

## Version Handling

At this stage, initialize supports both:

- exact version shorthand
- explicit multi-version negotiation

Reference behavior:

- if `preferred_version` is present and supported, it should be chosen
- otherwise, the server should choose the first mutually supported version from `supported_versions`
- if there is no mutual version, initialization should fail with `MGP_UNSUPPORTED_VERSION`

Further evolution rules remain defined in `spec/versioning.md`.

## Capability Handling

The initialize response returns protocol-layer capabilities in:

- `data.protocol_capabilities`

This is distinct from backend and adapter discovery metadata exposed through:

- `GET /mgp/capabilities`

Current lifecycle capability scope includes:

- initialize support
- stateless transport support
- session support
- async support
- notification support
- subscription support

The initialize request may also include:

- `runtime_capabilities`

This lets the server compute an effective negotiated surface for features such as:

- `consumable_text`
- `redaction_info`
- mixed return modes
- prompt-safe views
- future async or subscription features

For `MGP v0.1.0`, this negotiation clarifies which runtime-facing features are safe to rely on. It does not remove required fields from the published request or response schemas.

## Ordering Rules

For the current stateless HTTP profile:

- clients may call `capabilities` without calling `initialize`
- clients may call normal core memory operations and `audit/query` without calling `initialize`
- clients should call `initialize` before relying on negotiated protocol behavior

Practical decision rule:

- skip `initialize` when the client only needs the baseline HTTP surface and can operate without negotiation
- call `initialize` before depending on negotiated version selection, runtime capability negotiation, profile-gated behavior, or future transport-specific behavior

This deliberately keeps the first lifecycle implementation non-breaking.

Future stateful profiles may strengthen these rules and require:

- initialize before all normal operations
- explicit session identifiers
- stricter shutdown behavior

## Error Handling

Initialization failures should use the normal response envelope:

- `status: error`
- `error.code`
- `data: null`

Typical failure cases:

- malformed initialize payload
- unsupported requested transport profile
- unsupported requested protocol version

## Non-Goals

This document does not yet define:

- stream resumability
- protocol-level shutdown messages
- bidirectional notifications
- task progress or cancellation
- full version negotiation across multiple supported versions
- stateful protocol session behavior
