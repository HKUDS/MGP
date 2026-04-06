# File Reference Adapter

File-backed reference adapter for MGP.

## Purpose

This adapter proves that MGP is not limited to database backends. It is intended to cover file-native and workspace-style memory storage.

## Storage Model

- each memory object is stored as one JSON file
- file path is derived from `memory_id`
- adapter state is persisted on disk under the configured storage directory

## Mapping Rules

- one file per `memory_id`
- the file contains the canonical memory object and lightweight state metadata
- `backend_ref.adapter` is normalized to `file`
- `backend_ref.mgp_state` is set to `active`, `expired`, or `revoked`
- search scans all files and performs substring matching on serialized `content`

## Supported Capabilities

See [manifest.json](manifest.json).

Highlights:

- `supports_write: true`
- `supports_update: true`
- `supports_search: true`
- `supports_native_ttl: false`

## Known Limitations

- search is scan-based and not indexed
- no native TTL support
- no graph relation support
- no native conflict detection
- stored format is JSON rather than markdown despite the file-based paradigm

## Compliance

This adapter is expected to pass the full compliance suite:

```bash
cd compliance
MGP_ADAPTER=file ../.venv/bin/python -m pytest
```

The CI workflow also publishes a JUnit XML artifact for the file adapter so compatibility results can be reviewed per run.
