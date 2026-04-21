# Errors

This document defines the baseline protocol error model for `MGP v0.1`.

## Error Shape

When an operation fails, the response envelope should use this shape:

```json
{
  "request_id": "req_123",
  "status": "error",
  "error": {
    "code": "MGP_INVALID_OBJECT",
    "message": "memory object failed schema validation",
    "details": {
      "field": "subject.kind"
    }
  },
  "data": null
}
```

## Error Model Rules

- `code` is the stable protocol identifier.
- `message` is human-readable and implementation-specific.
- `details` is optional structured metadata for debugging.
- HTTP bindings may map these errors to status codes, but the MGP error code remains the canonical contract.

## Baseline Error Codes

| Code | HTTP-equivalent hint | Retryable | Meaning |
| --- | --- | --- | --- |
| `MGP_INVALID_OBJECT` | `400 Bad Request` | No | Request payload or memory object failed validation |
| `MGP_UNSUPPORTED_VERSION` | `400 Bad Request` | No | The requested protocol version is not supported or no mutually supported version exists |
| `MGP_UNSUPPORTED_CAPABILITY` | `501 Not Implemented` | No | Backend or adapter does not support the requested feature |
| `MGP_POLICY_DENIED` | `403 Forbidden` | No | Policy evaluation rejected the request |
| `MGP_MEMORY_NOT_FOUND` | `404 Not Found` | No | Target memory does not exist |
| `MGP_TASK_NOT_FOUND` | `404 Not Found` | No | Target async task does not exist |
| `MGP_SCOPE_VIOLATION` | `403 Forbidden` | No | Request attempts to cross or violate an allowed scope boundary |
| `MGP_CONFLICT_UNRESOLVED` | `409 Conflict` | Sometimes | A conflict exists and the implementation cannot resolve it automatically |
| `MGP_BACKEND_ERROR` | `502 Bad Gateway` or `500 Internal Server Error` | Yes | Adapter or backend failed while processing the request |

## MGP_INVALID_OBJECT

### MGP_INVALID_OBJECT When It Applies

Use this error when the request or normalized memory object does not conform to the required schema or semantic constraints.

### MGP_INVALID_OBJECT Example Scenario

A runtime sends a memory object with an unsupported `subject.kind` or omits a required field such as `memory_id`.

### MGP_INVALID_OBJECT Retryability

Not retryable until the caller corrects the request payload.

## MGP_UNSUPPORTED_CAPABILITY

### MGP_UNSUPPORTED_CAPABILITY When It Applies

Use this error when the target adapter or backend does not support a requested operation or feature that the caller attempted to use.

### MGP_UNSUPPORTED_CAPABILITY Example Scenario

A caller requests native expiration behavior from a backend that only supports plain write and read semantics.

### MGP_UNSUPPORTED_CAPABILITY Retryability

Not retryable unless the caller changes the request or routes it to a different backend.

## MGP_UNSUPPORTED_VERSION

### MGP_UNSUPPORTED_VERSION When It Applies

Use this error when lifecycle initialization cannot choose a mutually supported protocol version from the client's request and the server's supported version set.

### MGP_UNSUPPORTED_VERSION Example Scenario

A client sends `supported_versions = ["0.3.0", "0.2.0"]`, but the target gateway currently supports only `0.1.1`.

### MGP_UNSUPPORTED_VERSION Retryability

Not retryable unless the caller changes the requested versions or reconnects to an implementation that supports one of them.

## MGP_POLICY_DENIED

### MGP_POLICY_DENIED When It Applies

Use this error when policy evaluation denies access, mutation, or retrieval based on the provided `policy_context`.

### MGP_POLICY_DENIED Example Scenario

A runtime attempts to access restricted memory for a different tenant or requests a read action that the acting subject is not permitted to perform.

### MGP_POLICY_DENIED Retryability

Not retryable unless policy context or authorization state changes.

## MGP_MEMORY_NOT_FOUND

### MGP_MEMORY_NOT_FOUND When It Applies

Use this error when an operation references a `memory_id` that does not exist or is not resolvable by the target implementation.

### MGP_MEMORY_NOT_FOUND Example Scenario

An `UpdateMemory` request targets `mem_404`, but no such memory object exists.

### MGP_MEMORY_NOT_FOUND Retryability

Not retryable unless the missing memory is later created or the caller corrects the identifier.

## MGP_TASK_NOT_FOUND

### MGP_TASK_NOT_FOUND When It Applies

Use this error when an async task endpoint references a `task_id` that does not exist or is no longer available.

### MGP_TASK_NOT_FOUND Example Scenario

A caller polls `POST /mgp/tasks/get` for `task_missing`, but the gateway has no record of that task.

### MGP_TASK_NOT_FOUND Retryability

Not retryable unless the caller corrects the identifier or creates a new async task first.

## MGP_SCOPE_VIOLATION

### MGP_SCOPE_VIOLATION When It Applies

Use this error when a request crosses protocol-defined or implementation-defined scope boundaries in a way that is not allowed.

### MGP_SCOPE_VIOLATION Example Scenario

A session-scoped operation attempts to mutate a user-scoped memory without an allowed cross-scope rule.

### MGP_SCOPE_VIOLATION Retryability

Not retryable unless the caller changes scope, context, or target memory selection.

## MGP_CONFLICT_UNRESOLVED

### MGP_CONFLICT_UNRESOLVED When It Applies

Use this error when the implementation detects a conflict and no configured resolution strategy can safely decide the outcome.

### MGP_CONFLICT_UNRESOLVED Example Scenario

Two writes attempt to store contradictory high-confidence facts for the same subject and key, and the backend does not have a policy to choose one automatically.

### MGP_CONFLICT_UNRESOLVED Retryability

Potentially retryable if the caller changes the payload, attaches conflict metadata, or retries after human review.

## MGP_BACKEND_ERROR

### MGP_BACKEND_ERROR When It Applies

Use this error when the adapter, gateway, or underlying backend fails for reasons not attributable to caller input.

### MGP_BACKEND_ERROR Example Scenario

The backend becomes unavailable, times out, or returns an internal execution error while processing a valid request.

### MGP_BACKEND_ERROR Retryability

Usually retryable with backoff, depending on the transport binding and backend failure mode.
