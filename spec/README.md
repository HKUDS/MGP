# MGP Specification Index

This directory is the human-readable semantic source of truth for MGP.

Use `spec/` to understand what an operation means, what the protocol promises, and which behaviors are considered compatible across implementations. The machine-readable details live elsewhere, but they are subordinate to the semantic intent described here.

## Contract Stack

Read the protocol assets in this order:

1. `spec/` defines semantic meaning, invariants, and compatibility intent.
2. `schemas/` defines the canonical request and response shapes.
3. `openapi/mgp-openapi.yaml` defines the HTTP binding for the published wire surface.
4. `reference/` and `compliance/` show the contract in executable form.

If those layers disagree:

- `spec/` wins for semantic interpretation
- `schemas/` wins for exact machine-readable payload shape
- `openapi/` must be brought back into alignment with both
- executable behavior and tests must be updated so compatibility claims remain true

## Reading Paths

### Core governed memory

- `core-operations.md`
- `protocol-behavior.md`
- `search-results.md`
- `errors.md`

### Governance

- `retention.md`
- `conflicts.md`
- `access-control.md`

### Lifecycle and interoperability

- `lifecycle.md`
- `async-operations.md`
- `http-binding.md`

### Runtime integration

- `runtime-client.md`
- `runtime-write-candidate.md`

### Evolution and extension

- `versioning.md`
- `extensions.md`

## Change Discipline

When you change protocol behavior, update all affected layers together:

- the relevant `spec/*.md`
- the impacted `schemas/*.json`
- `openapi/mgp-openapi.yaml`
- executable validation in `reference/` and `compliance/`
- user-facing documentation in `docs/` and `docs/zh/`

Run these checks before claiming the contract is aligned:

```bash
make lint
make test-all
make docs-build
```

## Version Streams

MGP has more than one version surface:

- the protocol version documented in `spec/versioning.md`
- reference gateway release/version metadata
- SDK package versions

Those streams should move together when the published contract changes, but they should still be documented separately so users know what they are upgrading.
