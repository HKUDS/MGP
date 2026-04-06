# Protocol Behavior

This document defines cross-cutting wire-level behavior for `MGP v0.1`.

## Purpose

The core operation and governance specs define operation semantics. This document defines the behavioral rules that apply across endpoints so that clients and servers can behave consistently in real deployments.

## Request ID

Every request must carry a `request_id` in the request envelope.

Required behavior:

- clients generate it
- servers echo it in the response body
- implementations may also mirror it as `MGP-Request-Id` in HTTP headers

This enables correlation across retries, logs, audits, and distributed traces.

## Pagination

Pagination is cursor-based.

Recommended request fields:

- `pagination_token`
- `limit`

Recommended response fields:

- `next_token`

Behavior rules:

- absence of `next_token` means there are no further pages
- pagination tokens are opaque to clients
- servers may reject expired or invalid tokens with `MGP_INVALID_OBJECT`

## Timeout

Implementations should support an optional `timeout_ms` request field where relevant.

Behavior rules:

- timeout is advisory, not guaranteed
- if omitted, timeout defaults are implementation-defined
- servers may clamp unreasonably large timeout values

## Async Tasks

Some operations may support an async execution mode.

Reference behavior:

- callers may request async execution where the operation definition allows it
- servers may respond with a task handle instead of an immediate final result
- task state should be retrievable through a polling endpoint
- cancellation should be best-effort

See:

- `spec/async-operations.md`

## Retry

Retry safety follows the semantic rules from [spec/core-operations.md](core-operations.md):

- `SearchMemory` is safe to retry
- `GetMemory` is safe to retry
- `UpdateMemory`, `ExpireMemory`, and `RevokeMemory` rely on their idempotency rules
- `WriteMemory` is not safe to blindly retry without caller awareness of duplicate behavior

If a backend failure occurs after partial processing, callers should inspect the returned `request_id` and error details before retrying mutating operations.

## Partial Failure

When a gateway fans out to multiple backends, a request may partially succeed.

Recommended response shape when useful results are still returned:

```json
{
  "request_id": "req_123",
  "status": "ok",
  "error": null,
  "data": {
    "results": [],
    "partial_failure": {
      "failed_backends": [
        {
          "backend": "zep-primary",
          "error_code": "MGP_BACKEND_ERROR",
          "message": "backend timeout",
          "retryable": true
        }
      ]
    }
  }
}
```

Behavior rules:

- partial failure does not necessarily require top-level `status: error`
- the top-level response may still be `ok` if useful results are returned
- operation-specific response schemas should place partial-failure details inside `data`
- clients should inspect `data.partial_failure` when present

## Backend Unavailable

When a backend is unavailable, the response should use:

- `error.code = MGP_BACKEND_ERROR`

Recommended `details` fields:

- `backend`
- `reason`
- `retryable`

Example:

```json
{
  "request_id": "req_123",
  "status": "error",
  "error": {
    "code": "MGP_BACKEND_ERROR",
    "message": "backend unavailable",
    "details": {
      "backend": "file-adapter",
      "reason": "connection refused",
      "retryable": true
    }
  },
  "data": null
}
```

## Sorting

MGP does not define a universal sort algorithm for search results.

Behavior rules:

- search responses should be ordered according to implementation ranking
- `score` should be included so callers can inspect ranking intent
- pagination should preserve the same ordering semantics across pages

## Non-Goals

This document does not define:

- transport-level streaming
- distributed consensus
- backend selection policies
- server-side cache semantics
