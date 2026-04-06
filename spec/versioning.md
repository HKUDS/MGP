# Versioning

This document defines the versioning strategy for MGP.

## Purpose

MGP needs predictable evolution rules so that runtimes, adapters, gateways, and SDKs can upgrade without accidental breakage.

This document covers protocol compatibility first, but it also distinguishes the protocol version from repository release streams such as the reference gateway and SDK packages.

## Version Format

MGP uses semantic versioning:

- `major.minor.patch`

Examples:

- `0.1.0`
- `0.2.0`
- `1.0.0`

## Version Streams

The repository currently exposes multiple version surfaces:

- **Protocol version**: the semantic contract described by `spec/`, `schemas/`, and `openapi/`
- **Reference gateway version**: the runnable gateway release/version metadata
- **SDK version**: package versions such as `mgp-client`

These streams should stay visibly aligned, but they are not the same thing:

- a protocol change may require gateway and SDK releases
- a gateway packaging or deployment change may not change the protocol version
- an SDK ergonomics improvement may not change protocol semantics

Repository rule:

- when the published wire contract changes, update the protocol version markers in `README.md`, `README.zh.md`, and `openapi/mgp-openapi.yaml`
- when only packaging or implementation ergonomics change, document the package release without overstating protocol change

## Major Version Changes

A major version change is required when a change breaks existing compliant implementations.

Examples:

- removing an operation
- changing request or response envelope shape incompatibly
- removing a required schema field
- removing an enum value

## Minor Version Changes

A minor version change is used for additive, backward-compatible changes.

Examples:

- adding optional schema fields
- adding new operations
- adding new capability flags
- adding new governance modes
- adding new enum values that older implementations can safely ignore or reject explicitly

Compatibility guidance for newly added enum values:

- older implementations should not silently reinterpret an unknown enum value as a different known value
- if the unknown value appears in an optional field the implementation does not rely on, it may ignore that field
- if the unknown value appears in a request field that affects behavior, the implementation should reject the request explicitly, typically with `MGP_INVALID_OBJECT` or `MGP_UNSUPPORTED_CAPABILITY` depending on context

## Patch Version Changes

A patch version change is used when protocol semantics do not materially change.

Examples:

- documentation fixes
- typo corrections
- clarifications
- compliance suite fixes that do not redefine protocol meaning

Current repository policy:

- alignment work that reconciles `spec/`, `schemas/`, `openapi/`, reference behavior, and examples without changing protocol meaning remains part of `v0.1.0`

## Release Documentation Expectations

Whenever compatibility-relevant changes land:

- update the repository release notes or tagged release description
- update any affected protocol version markers
- update compliance or conformance-profile documentation if the supported surface changed
- keep release notes clear about whether the change affects protocol, gateway packaging, SDK packaging, or all three

## Schema Backward Compatibility Rules

Allowed in a backward-compatible release:

- adding optional fields
- adding new compatibility badges
- adding new extension namespaces
- adding enum values when existing behavior remains valid

Not allowed without a major version:

- removing required fields
- renaming fields
- changing the meaning of existing fields
- making an optional field required

## Protocol Version Negotiation

Lifecycle initialization supports two request styles:

1. legacy shorthand

- `protocol_version`

2. negotiated form

- `supported_versions`
- optional `preferred_version`

Reference negotiation rules:

- if `preferred_version` is present, it must also appear in `supported_versions`
- if the server supports `preferred_version`, it should choose it
- otherwise, the server should choose the first mutually supported version from the client-declared `supported_versions`
- if there is no mutual version, the server should return `MGP_UNSUPPORTED_VERSION`

The initialize response should return:

- `chosen_version`
- `supported_versions`
- optional `minimum_supported_version`
- optional `deprecation_warnings`

This keeps old single-version clients working while allowing future multi-version ecosystems to negotiate explicitly.

## Capability Deprecation

Capabilities may be deprecated before removal.

Recommended process:

1. mark the capability as deprecated in documentation
2. keep it available for at least one minor version
3. remove it only in a major release

## Extension Namespace Reservation

Reserved namespaces:

- `mgp` is reserved for protocol-level use

Vendor namespaces:

- should be documented in repository documentation and adapter manifests
- should not conflict with reserved namespaces

## Compatibility Principle

New protocol features should not break old ecosystems by surprise.

When in doubt:

- additive change -> minor
- breaking change -> major
- wording-only change -> patch

## Operational Rule Of Thumb

When announcing a release, answer these questions explicitly:

1. Did the protocol version change?
2. Did the reference gateway release change?
3. Did an SDK package release change?
4. Which conformance profiles are affected?

If those answers are not clear, the release documentation is incomplete.
