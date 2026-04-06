# HTTP Binding

This document defines the reference HTTP binding for `MGP v0.1`.

## Purpose

The MGP semantic specification defines what operations exist and what they mean. This document defines how those operations are transported over HTTP so that clients and servers can interoperate concretely.

`MGP v0.1` defines JSON over HTTP as the first transport binding. Future transports such as gRPC may be added later without changing the protocol semantics.

## Contract Alignment

- `spec/` defines operation meaning and transport rules
- operation-specific schemas under `schemas/` define the exact request and response body shape
- `openapi/mgp-openapi.yaml` mirrors the HTTP mapping and should not introduce wire shapes that disagree with the schemas

## Transport Rules

### Content Type

Requests and responses use:

- `Content-Type: application/json`
- `Accept: application/json`

### Method Mapping

All protocol operations use `POST` except capability discovery, which uses `GET`.

This keeps the wire format aligned with the transport-agnostic operation model defined in [spec/core-operations.md](core-operations.md).

### Lifecycle Initialization

The reference HTTP binding now exposes an explicit lifecycle handshake:

- `POST /mgp/initialize`

This endpoint is used to:

- request a protocol version
- advertise client identity
- request protocol profiles and capabilities
- receive a `ready` response before advanced protocol behavior is used

For the current stateless HTTP profile:

- `initialize` is supported
- `initialize` is recommended
- `initialize` is not mandatory before normal CRUD-style memory operations
- a successful initialize response does not create a protocol-level session yet

### Version Header

Implementations may accept an optional request header:

- `MGP-Version`

When lifecycle initialization is used:

- clients should mirror the negotiated version in `MGP-Version` on subsequent requests when practical
- servers may reject header / body mismatches during initialize when both are present, preferably using `MGP_INVALID_OBJECT`

For the current stateless HTTP profile, implementations may treat the header as informational on non-initialize requests unless they explicitly persist negotiation state.

### Request Correlation

Implementations may mirror the request envelope `request_id` in an HTTP header:

- `MGP-Request-Id`

If both are present, they should match. The canonical protocol field remains `request_id` inside the JSON envelope.

### Authentication

Authentication is intentionally out of scope for `MGP v0.1`.

Implementations may use:

- Bearer tokens
- mTLS
- API keys
- session-based auth

But these mechanisms are deployment concerns, not part of the core MGP protocol contract.

## Endpoint Mapping

| Endpoint | Method | Operation | Request Body | Response Body |
| --- | --- | --- | --- | --- |
| `/mgp/initialize` | `POST` | Lifecycle initialize | Initialize request | Initialize response |
| `/mgp/write` | `POST` | `WriteMemory` | Request envelope | Response envelope |
| `/mgp/write/batch` | `POST` | `BatchWriteMemory` | Request envelope | Response envelope |
| `/mgp/search` | `POST` | `SearchMemory` | Request envelope | Response envelope |
| `/mgp/get` | `POST` | `GetMemory` | Request envelope | Response envelope |
| `/mgp/update` | `POST` | `UpdateMemory` | Request envelope | Response envelope |
| `/mgp/expire` | `POST` | `ExpireMemory` | Request envelope | Response envelope |
| `/mgp/revoke` | `POST` | `RevokeMemory` | Request envelope | Response envelope |
| `/mgp/delete` | `POST` | `DeleteMemory` | Request envelope | Response envelope |
| `/mgp/purge` | `POST` | `PurgeMemory` | Request envelope | Response envelope |
| `/mgp/export` | `POST` | `ExportMemories` | Request envelope | Response envelope |
| `/mgp/import` | `POST` | `ImportMemories` | Request envelope | Response envelope |
| `/mgp/sync` | `POST` | `SyncMemories` | Request envelope | Response envelope |
| `/mgp/tasks/get` | `POST` | Get async task | Task request | Task response |
| `/mgp/tasks/cancel` | `POST` | Cancel async task | Task request | Task response |
| `/mgp/capabilities` | `GET` | Capability discovery | None | JSON capability document |
| `/mgp/audit/query` | `POST` | Audit query | Request envelope | Response envelope |

## Error Mapping

MGP error codes remain canonical. HTTP status codes are transport hints.

Recommended mappings:

| MGP Error Code | Suggested HTTP Status |
| --- | --- |
| `MGP_INVALID_OBJECT` | `400 Bad Request` |
| `MGP_UNSUPPORTED_VERSION` | `400 Bad Request` |
| `MGP_UNSUPPORTED_CAPABILITY` | `501 Not Implemented` |
| `MGP_POLICY_DENIED` | `403 Forbidden` |
| `MGP_MEMORY_NOT_FOUND` | `404 Not Found` |
| `MGP_TASK_NOT_FOUND` | `404 Not Found` |
| `MGP_SCOPE_VIOLATION` | `403 Forbidden` |
| `MGP_CONFLICT_UNRESOLVED` | `409 Conflict` |
| `MGP_BACKEND_ERROR` | `502 Bad Gateway` or `500 Internal Server Error` |

The HTTP code must not replace the MGP error code in the response body.

## Required And Optional Endpoints

Required core memory endpoints:

- `/mgp/write`
- `/mgp/search`
- `/mgp/get`
- `/mgp/update`
- `/mgp/expire`
- `/mgp/revoke`
- `/mgp/delete`
- `/mgp/purge`

Requirement note:

- this list describes the gateway surface that a compliant HTTP implementation exposes
- it does not imply that every backend supports every operation natively
- adapter manifests should continue to declare backend-native capability truthfully even when the gateway can emulate part of the surface

Required discovery and governance support endpoints:

- `/mgp/capabilities`
- `/mgp/audit/query`

Optional protocol profile endpoints:

- `/mgp/initialize`
- `/mgp/write/batch`
- `/mgp/export`
- `/mgp/import`
- `/mgp/sync`
- `/mgp/tasks/get`
- `/mgp/tasks/cancel`

### `/mgp/initialize`

Performs the lifecycle handshake defined in [spec/lifecycle.md](lifecycle.md).

For the current stateless HTTP profile, this endpoint returns:

- chosen protocol version
- protocol ready state
- negotiated profiles
- protocol-layer capabilities
- implementation metadata

Clients may skip `initialize` for core memory operations, capability discovery, and audit query when they do not rely on negotiated profiles or runtime capability negotiation.

Clients should call `initialize` before relying on:

- negotiated protocol versions
- negotiated runtime capabilities
- profile-gated behavior such as async or future transport extensions

### `/mgp/write`

Creates a new memory object. The request body follows the `WriteMemory` contract from [spec/core-operations.md](core-operations.md).

### `/mgp/search`

Searches memory objects and returns normalized results as defined in [spec/search-results.md](search-results.md).

When fan-out across multiple backends yields useful results plus backend-specific failures, the response may include `data.partial_failure`.

### `/mgp/get`

Fetches a single memory object by `memory_id`.

### `/mgp/update`

Updates an existing memory object. Implementations should honor the idempotency guidance from [spec/core-operations.md](core-operations.md).

### `/mgp/expire`

Marks a memory as expired using the retention semantics from [spec/retention.md](retention.md).

### `/mgp/revoke`

Revokes a memory from normal use without conflating revocation with expiration.

### `/mgp/delete`

Performs soft deletion and leaves a tombstone view according to the lifecycle semantics defined in [spec/core-operations.md](core-operations.md).

### `/mgp/purge`

Performs hard deletion from normal retrieval paths while allowing audit-related behavior to remain implementation-defined.

### `/mgp/capabilities`

Returns discovery metadata so that clients can inspect:

- adapter and backend capabilities via `manifest`
- protocol-layer capabilities via `protocol_capabilities`

This endpoint remains discovery-oriented and does not replace initialize-time negotiated capability output.

Discovery note:

- `/mgp/capabilities` tells clients what the implementation and current adapter expose in general
- `/mgp/initialize` tells clients what was negotiated for one interaction

### Async Interop Endpoints

`/mgp/export`, `/mgp/import`, and `/mgp/sync` may support:

- `execution_mode = "sync"`
- `execution_mode = "async"`

When async execution is accepted, the server may return:

- HTTP `202 Accepted`
- a normal MGP response envelope carrying a `task` object

Task polling endpoints:

- `/mgp/tasks/get`
- `/mgp/tasks/cancel`

### `/mgp/audit/query`

Queries audit events and may return zero or more audit entries in normalized form.

## HTTP Binding Non-Goals

This document does not define:

- authentication schemes
- deployment topology
- load balancing or service discovery
- gRPC bindings
