# Reference Implementation

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](../LICENSE)

The runnable Python reference gateway for MGP. It maps the full protocol surface to pluggable adapters while validating every request and response against published JSON Schemas.

Key features:

- package metadata in `reference/pyproject.toml`
- a CLI entrypoint through `mgp-gateway`
- configurable adapter, audit, auth, and tenant-binding settings
- operational endpoints for health, readiness, and version inspection

## Requirements

- Python 3.11+
- dependencies from `requirements.txt` or `pyproject.toml`

## Install

### Repository Development Path

```bash
make install
```

### Gateway Package Path

```bash
python3 -m pip install ./reference
```

That install exposes the `mgp-gateway` command.

If you want the LanceDB adapter available in the installed gateway, install the optional extra:

```bash
python3 -m pip install "./reference[lancedb]"
```

## Run

### Source Path

```bash
make serve
```

Or manually:

```bash
cd reference
python3 -m gateway.app
```

### Installed CLI Path

```bash
mgp-gateway --host 127.0.0.1 --port 8080
```

### File Adapter With Persistent Storage

```bash
mgp-gateway \
  --adapter file \
  --file-storage-dir ./data \
  --audit-log ./audit.jsonl
```

### PostgreSQL Adapter

```bash
mgp-gateway \
  --adapter postgres \
  --postgres-dsn postgresql://postgres:postgres@127.0.0.1:5432/mgp
```

### LanceDB Adapter

```bash
mgp-gateway \
  --adapter lancedb \
  --lancedb-dir /tmp/mgp-lancedb \
  --lancedb-table memories
```

You also need an embedding configuration, for example:

```bash
export MGP_LANCEDB_EMBEDDING_PROVIDER=openrouter
export MGP_LANCEDB_EMBEDDING_MODEL=openai/text-embedding-3-small
export MGP_LANCEDB_EMBEDDING_API_KEY=...
export MGP_LANCEDB_EMBEDDING_BASE_URL=https://openrouter.ai/api/v1
```

Repository smoke test helper:

```bash
./.venv/bin/python scripts/smoke_lancedb_gateway.py
```

If you want to validate the source-path gateway instead of an installed `mgp-gateway` command:

```bash
./.venv/bin/python scripts/smoke_lancedb_gateway.py \
  --gateway-cmd "../.venv/bin/python -m gateway.__main__" \
  --gateway-cwd reference
```

### Docker Path

```bash
docker compose up --build
```

See `examples/deploy/reference-gateway/.env.example` for a container-oriented environment file.

## Configuration Surface

Important environment variables:

- `MGP_ADAPTER`
- `MGP_AUDIT_LOG`
- `MGP_FILE_STORAGE_DIR`
- `MGP_GRAPH_DB_PATH`
- `MGP_POSTGRES_DSN`
- `MGP_LANCEDB_DIR`
- `MGP_LANCEDB_TABLE`
- `MGP_LANCEDB_ENABLE_HYBRID`
- `MGP_LANCEDB_EMBEDDING_PROVIDER`
- `MGP_LANCEDB_EMBEDDING_MODEL`
- `MGP_LANCEDB_EMBEDDING_API_KEY`
- `MGP_LANCEDB_EMBEDDING_BASE_URL`
- `MGP_LANCEDB_EMBEDDING_DIM`
- `MGP_GATEWAY_AUTH_MODE`
- `MGP_GATEWAY_API_KEY`
- `MGP_GATEWAY_BEARER_TOKEN`
- `MGP_GATEWAY_TENANT_HEADER`
- `MGP_GATEWAY_REQUIRE_TENANT_HEADER`

Authentication modes:

- `off`
- `api_key`
- `bearer`

The auth and tenant-binding middleware is intentionally minimal, but it provides an official place to plug deployment-specific enforcement into the reference gateway.

## What Is Included

- FastAPI gateway covering the current reference HTTP surface
- operational endpoints at `/healthz`, `/readyz`, and `/version`
- in-memory, file, graph, postgres, lancedb, and service-backed adapter routing
- minimal policy hook
- JSON Lines audit sink

The gateway validates operation-specific request and response payloads against the published schemas.

Current protocol endpoints:

- `POST /mgp/initialize`
- `POST /mgp/write`
- `POST /mgp/search`
- `POST /mgp/get`
- `POST /mgp/update`
- `POST /mgp/expire`
- `POST /mgp/revoke`
- `POST /mgp/delete`
- `POST /mgp/purge`
- `POST /mgp/write/batch`
- `POST /mgp/export`
- `POST /mgp/import`
- `POST /mgp/sync`
- `POST /mgp/tasks/get`
- `POST /mgp/tasks/cancel`
- `GET /mgp/capabilities`
- `POST /mgp/audit/query`

## cURL Examples

### Write

```bash
curl -X POST http://127.0.0.1:8080/mgp/write \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_write_1",
    "policy_context": {
      "actor_agent": "nanobot/main",
      "acting_for_subject": {"kind": "user", "id": "user_123"},
      "requested_action": "write",
      "tenant_id": "tenant_1"
    },
    "payload": {
      "memory": {
        "memory_id": "mem_1",
        "subject": {"kind": "user", "id": "user_123"},
        "scope": "user",
        "type": "preference",
        "content": {
          "statement": "User prefers dark mode.",
          "preference": "dark mode",
          "preference_key": "theme",
          "preference_value": "dark"
        },
        "source": {"kind": "human", "ref": "chat:1"},
        "sensitivity": "internal",
        "ttl_seconds": 3600,
        "created_at": "2026-03-17T12:00:00Z",
        "backend_ref": {"tenant_id": "tenant_1"},
        "extensions": {}
      }
    }
  }'
```

### Search

```bash
curl -X POST http://127.0.0.1:8080/mgp/search \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_search_1",
    "policy_context": {
      "actor_agent": "nanobot/main",
      "acting_for_subject": {"kind": "user", "id": "user_123"},
      "requested_action": "search",
      "tenant_id": "tenant_1"
    },
    "payload": {
      "query": "dark",
      "limit": 10
    }
  }'
```

### Get

```bash
curl -X POST http://127.0.0.1:8080/mgp/get \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_get_1",
    "policy_context": {
      "actor_agent": "nanobot/main",
      "acting_for_subject": {"kind": "user", "id": "user_123"},
      "requested_action": "read",
      "tenant_id": "tenant_1"
    },
    "payload": {
      "memory_id": "mem_1"
    }
  }'
```

### Update

```bash
curl -X POST http://127.0.0.1:8080/mgp/update \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_update_1",
    "policy_context": {
      "actor_agent": "nanobot/main",
      "acting_for_subject": {"kind": "user", "id": "user_123"},
      "requested_action": "update",
      "tenant_id": "tenant_1"
    },
    "payload": {
      "memory_id": "mem_1",
      "patch": {
        "content": {
          "statement": "User prefers light mode.",
          "preference": "light mode",
          "preference_value": "light"
        },
        "updated_at": "2026-03-17T12:05:00Z"
      }
    }
  }'
```

### Expire

```bash
curl -X POST http://127.0.0.1:8080/mgp/expire \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_expire_1",
    "policy_context": {
      "actor_agent": "nanobot/main",
      "acting_for_subject": {"kind": "user", "id": "user_123"},
      "requested_action": "expire",
      "tenant_id": "tenant_1"
    },
    "payload": {
      "memory_id": "mem_1",
      "expired_at": "2026-03-17T13:00:00Z",
      "reason": "manual_expire"
    }
  }'
```

### Revoke

```bash
curl -X POST http://127.0.0.1:8080/mgp/revoke \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_revoke_1",
    "policy_context": {
      "actor_agent": "nanobot/main",
      "acting_for_subject": {"kind": "user", "id": "user_123"},
      "requested_action": "revoke",
      "tenant_id": "tenant_1"
    },
    "payload": {
      "memory_id": "mem_1",
      "revoked_at": "2026-03-17T13:05:00Z",
      "reason": "user_removed"
    }
  }'
```

### Capabilities

```bash
curl http://127.0.0.1:8080/mgp/capabilities
```

### Audit Query

```bash
curl -X POST http://127.0.0.1:8080/mgp/audit/query \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_audit_1",
    "policy_context": {
      "actor_agent": "nanobot/main",
      "acting_for_subject": {"kind": "user", "id": "user_123"},
      "requested_action": "read",
      "tenant_id": "tenant_1"
    },
    "payload": {
      "action": "write",
      "limit": 20
    }
  }'
```

## Notes

- The in-memory adapter is the simplest path for local testing.
- The file adapter stores each memory object as a JSON file.
- Audit events are appended as JSON Lines and can be inspected directly.
- `initialize`, async tasking, and interop endpoints are implemented as optional protocol layers on top of the core governed-memory contract.
