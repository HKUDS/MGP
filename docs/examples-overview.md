# Examples Overview

This page points to the runnable Python examples that exercise the reference gateway and protocol surface.

## Prerequisites

- Python dependencies installed via `make install`
- reference gateway running (`make serve`)
- for `04_switch_backend.py`, two gateway instances running at different URLs

## Suggested Gateway Startup

### In-Memory Adapter

```bash
make serve
```

Equivalent explicit command from the repository root:

```bash
./.venv/bin/mgp-gateway --host 127.0.0.1 --port 8080
```

### File Adapter on a Second Port

```bash
cd reference
MGP_ADAPTER=file ../.venv/bin/python -m uvicorn gateway.app:app --host 127.0.0.1 --port 8081
```

## Run Examples

### 1. Write a profile

```bash
./.venv/bin/python examples/01_write_profile.py
```

Expected result:

- writes a `profile` memory
- fetches it back
- returns a structured canonical memory object

### 2. Search an episodic event

```bash
./.venv/bin/python examples/02_search_episodic.py
```

Expected result:

- writes an `episodic_event`
- returns at least one search result
- each result includes `consumable_text`, `retrieval_mode`, and `score_kind`

### 3. TTL expiry

```bash
./.venv/bin/python examples/03_ttl_expiry.py
```

Expected result:

- one result before expiry
- zero results after expiry

### 4. Switch backend

```bash
MGP_MEMORY_URL=http://127.0.0.1:8080 MGP_FILE_URL=http://127.0.0.1:8081 ./.venv/bin/python examples/04_switch_backend.py
```

Expected result:

- writes equivalent data through two gateways
- prints both returned memory objects
- demonstrates that normalized protocol shape survives backend switching

### 5. End-to-end demo

```bash
./.venv/bin/python examples/e2e_demo.py
```

Expected result:

- write
- search
- get
- expire
- search again
- audit query
- structured search results and richer audit metadata

### 6. SDK-only path

```bash
./.venv/bin/python examples/05_sdk_only.py
```

Expected result:

- capability discovery through the SDK
- write and get using only `mgp-client`

### 7. Gateway plus PostgreSQL

```bash
MGP_POSTGRES_URL=http://127.0.0.1:8080 ./.venv/bin/python examples/06_gateway_plus_postgres.py
```

Expected result:

- capability output from a postgres-backed gateway
- write plus search against a production-oriented adapter path

### 8. Sidecar shadow mode

```bash
./.venv/bin/python examples/07_sidecar_shadow_mode.py
```

Expected result:

- Nanobot sidecar recall in `shadow` mode
- governed commit through the sidecar bridge

### 9. Batch, export, and import

```bash
./.venv/bin/python examples/08_batch_export_import.py
```

Expected result:

- batched writes
- export of normalized memories
- import of the exported payload

### 10. Task polling

```bash
./.venv/bin/python examples/09_task_polling.py
```

Expected result:

- async export acceptance
- task polling through the SDK
- completed task payload

### 11. Audit query

```bash
./.venv/bin/python examples/10_audit_query.py
```

Expected result:

- focused audit query via the SDK
- event payloads ready for operator inspection
