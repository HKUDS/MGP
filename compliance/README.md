# Compliance Test Suite

This directory contains the runnable compliance suite for MGP.

The canonical test commands, profile interpretation, and verification scope live in:

- [docs/compliance-suite.md](../docs/compliance-suite.md)
- [docs/zh/compliance-suite.md](../docs/zh/compliance-suite.md)

Use those pages as the single source of truth for:

- install and run commands
- adapter-specific validation paths
- profile terminology
- what the suite proves when it passes

## Recommended Entry Points

From the repository root:

- `make test` runs `python -m pytest compliance` for the selected `MGP_ADAPTER`
- `make test-all` repeats the same full suite for `memory`, `file`, and `graph`

Direct invocation is still supported when you want a focused run:

```bash
MGP_ADAPTER=file ./.venv/bin/python -m pytest compliance
```

## What This Directory Contains

- executable schema, core, lifecycle, adapter, and interop verification
- shared fixtures for launching the reference gateway against different adapters
- focused tests that back the repository's MGP compliance claims
