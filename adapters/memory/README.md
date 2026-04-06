# In-Memory Reference Adapter

In-memory reference adapter for MGP.

## Purpose

This is the simplest reference adapter. It exists to:

- provide the lowest-friction implementation of the MGP adapter contract
- make protocol behavior easy to inspect and debug
- serve as the baseline target for compliance testing

## Storage Model

- all memory objects live in a Python `dict`
- the key is `memory_id`
- adapter state is lost when the process exits

## Mapping Rules

- each stored record contains the canonical memory object plus lightweight state metadata
- `backend_ref.adapter` is normalized to `memory`
- `backend_ref.mgp_state` is set to `active`, `expired`, or `revoked`
- search performs simple substring matching against serialized `content`

## Supported Capabilities

See [manifest.json](manifest.json).

Highlights:

- `supports_write: true`
- `supports_update: true`
- `supports_search: true`
- `supports_native_ttl: false`

## Known Limitations

- no persistence across restarts
- no native TTL support
- no graph relations
- no native conflict detection
- search is simple substring matching, not semantic retrieval

## Compliance

This adapter is expected to pass the full compliance suite:

```bash
cd compliance
../.venv/bin/python -m pytest
```

The CI workflow also publishes a JUnit XML artifact for the in-memory adapter so compatibility results can be reviewed per run.
