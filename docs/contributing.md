# Contributing

Thanks for helping improve MGP.

This page is the documentation-site summary. The canonical contributor workflow, source-of-truth map, and broad-refactor baseline live in the repository-root `CONTRIBUTING.md`.

## Development Environment

From the repository root:

```bash
make install
```

This creates `.venv/` and installs the reference implementation, compliance suite, docs tooling, and the editable Python SDK.

## Common Commands

```bash
make lint
make test
make test-all
make test-sdk
make test-integrations
make security
make docs-build
make docs
make serve
```

Notes:

- `make test` uses the current `MGP_ADAPTER` value and defaults to `memory`
- `make test-all` runs the full compliance suite against `memory`, `file`, and `graph`
- `make test-sdk` runs the Python SDK tests
- `make test-integrations` runs the Nanobot, LangGraph, and minimal runtime integration tests
- `make serve` starts the reference gateway from `reference/`
- `make security` audits the locked dependency sets used by local development and CI

## Source-Of-Truth Reminders

- treat `spec/`, `schemas/`, and `openapi/` as the protocol contract surface
- keep the root `README.md` shorter than the detailed docs pages
- use `docs/getting-started.md` for quickstart details and `reference/README.md` for gateway install and CLI details
- use `docs/examples-overview.md` for runnable example commands and expected results

## Branching

- create a feature branch for each change
- keep changes scoped to a single protocol, adapter, docs, or tooling concern when possible
- open a pull request once local lint, tests, and docs build succeed

## Commit Expectations

- write clear commit messages that explain why the change exists
- keep generated files and unrelated cleanup out of the same commit when possible
- update relevant docs when behavior, schemas, or workflows change

## Testing

Minimum expectations before opening a pull request:

```bash
make lint
make test-all
make test-sdk
make test-integrations
make docs-build
```

If you are only touching documentation, run at least:

```bash
make docs-build
```

## Adding a New Adapter

Follow:

- `docs/adapter-guide.md`
- `schemas/adapter-manifest.schema.json`
- `schemas/backend-capabilities.schema.json`

Each adapter should ship with:

- `adapter.py`
- `manifest.json`
- `README.md`
- explicit capability declarations
- documented mapping rules
- documented limitations

Before proposing a new adapter, run the compliance suite against it and include the results in the pull request.

## Documentation

The documentation site is built with MkDocs Material.

- configuration: `mkdocs.yml`
- docs dependencies: `docs/requirements.txt`
- local preview: `make docs`

## Questions

If the intended protocol direction is unclear, open a discussion before implementing a broad change.
