# Contributing to MGP

Thanks for helping improve MGP! This document covers the development workflow, testing expectations, and repository conventions.

## Development Environment

From the repository root:

```bash
make install
```

This creates `.venv/` and installs the reference implementation, compliance suite, docs tooling, and the editable Python SDK.

## Common Commands

| Command | What it does |
|---------|-------------|
| `make lint` | Contract validation + code quality (ruff, mypy) |
| `make test` | Compliance on current adapter (default: `memory`) |
| `make test-all` | Full compliance on `memory`, `file`, and `graph` |
| `make test-sdk` | Python SDK tests |
| `make test-integrations` | Nanobot, LangGraph, and minimal runtime tests |
| `make security` | Dependency audit against locked files |
| `make docs-build` | Verify MkDocs documentation builds |
| `make docs` | Local documentation preview |
| `make serve` | Start the reference gateway |

## Repository Guardrails

Treat these paths as the source-of-truth map for the repository:

- `spec/`, `schemas/`, and `openapi/` define the governed protocol contract; only change them when you are intentionally evolving the protocol surface
- `README.md` and `README.zh.md` are repository landing pages and should stay shorter than the detailed guides
- `docs/index.md` and `docs/zh/index.md` are the canonical reading maps for the documentation site
- `docs/getting-started.md` and `docs/zh/getting-started.md` are the canonical quickstart walkthroughs
- `reference/README.md` is the canonical install, CLI, adapter, and runtime-configuration guide for the reference gateway; `docs/reference-implementation.md` and `docs/zh/reference-implementation.md` stay conceptual
- `docs/examples-overview.md` and `docs/zh/examples-overview.md` are the canonical example runbooks; `examples/README.md` is only the directory entry page
- this root `CONTRIBUTING.md` is the canonical contributor workflow; the docs-site contributing pages summarize it for readers
- when touching mirrored English and Chinese pages, update both in the same change whenever the content is intended to stay equivalent

Notes:

- `make lint` is the local umbrella command for both contract validation (`validate_schemas.py`, `validate_openapi.py`, `check_contract_drift.py`) and Python quality checks (`ruff check`, `mypy`)
- formatting remains pre-commit-driven through `ruff-format`; use `pre-commit run --all-files` when you want to apply or verify repository formatting locally
- CI exposes that same split as two workflows: `Contract` covers the published asset checks and `Quality` covers Ruff + mypy
- running bare `pytest` from the repository root follows `pyproject.toml` `testpaths`, so it will run compliance, integration, and SDK tests together; use the `make test*` targets when you want narrower local feedback

## Broad Refactor Baseline

For repo-wide cleanups, routing splits, or shared-helper extractions, record a before/after baseline with:

```bash
make lint
make test-all
make test-sdk
make test-integrations
make docs-build
```

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
- docs dependencies: `docs/requirements.lock.txt`
- local preview: `make docs`

## Dependency Management

- `reference/requirements.lock.txt`
- `compliance/requirements.lock.txt`
- `docs/requirements.lock.txt`

Use those locked files for local environments and CI. Refresh them in a Python 3.11+ virtual environment when dependencies intentionally change.

## Questions

If the intended protocol direction is unclear, open a discussion before implementing a broad change.
