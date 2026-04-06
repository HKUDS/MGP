# Schema Reference

This page collects the machine-readable protocol assets that sit alongside the markdown specifications.

## JSON Schemas

- `schemas/memory-object.schema.json`
- `schemas/memory-content-preference.schema.json`
- `schemas/memory-content-semantic-fact.schema.json`
- `schemas/memory-content-relationship.schema.json`
- `schemas/memory-content-procedural-rule.schema.json`
- `schemas/memory-candidate.schema.json`
- `schemas/memory-evidence.schema.json`
- `schemas/memory-merge-hint.schema.json`
- `schemas/recall-intent.schema.json`
- `schemas/search-result-item.schema.json`
- `schemas/redaction-info.schema.json`
- `schemas/partial-failure.schema.json`
- `schemas/error-code.schema.json`
- `schemas/return-mode.schema.json`
- `schemas/retrieval-mode.schema.json`
- `schemas/score-kind.schema.json`
- `schemas/policy-context.schema.json`
- `schemas/request-envelope.schema.json`
- `schemas/response-envelope.schema.json`
- `schemas/protocol-capabilities.schema.json`
- `schemas/runtime-capabilities.schema.json`
- `schemas/negotiated-capabilities.schema.json`
- `schemas/initialize.request.schema.json`
- `schemas/initialize.response.schema.json`
- `schemas/async-task.schema.json`
- `schemas/progress-event.schema.json`
- `schemas/get-task.request.schema.json`
- `schemas/get-task.response.schema.json`
- `schemas/cancel-task.request.schema.json`
- `schemas/cancel-task.response.schema.json`
- `schemas/audit-event.schema.json`
- `schemas/lineage-link.schema.json`
- `schemas/backend-capabilities.schema.json`
- `schemas/adapter-manifest.schema.json`
- `schemas/write-memory.request.schema.json`
- `schemas/write-memory.response.schema.json`
- `schemas/search-memory.request.schema.json`
- `schemas/search-memory.response.schema.json`
- `schemas/get-memory.request.schema.json`
- `schemas/get-memory.response.schema.json`
- `schemas/update-memory.request.schema.json`
- `schemas/update-memory.response.schema.json`
- `schemas/expire-memory.request.schema.json`
- `schemas/expire-memory.response.schema.json`
- `schemas/revoke-memory.request.schema.json`
- `schemas/revoke-memory.response.schema.json`
- `schemas/delete-memory.request.schema.json`
- `schemas/delete-memory.response.schema.json`
- `schemas/purge-memory.request.schema.json`
- `schemas/purge-memory.response.schema.json`
- `schemas/write-batch.request.schema.json`
- `schemas/write-batch.response.schema.json`
- `schemas/export.request.schema.json`
- `schemas/export.response.schema.json`
- `schemas/import.request.schema.json`
- `schemas/import.response.schema.json`
- `schemas/sync.request.schema.json`
- `schemas/sync.response.schema.json`
- `schemas/audit-query.request.schema.json`
- `schemas/audit-query.response.schema.json`
- `schemas/capabilities.response.schema.json`

## API Assets

- `openapi/mgp-openapi.yaml`

## How To Use These Assets

Recommended reading order:

1. Start with the relevant `spec/` document to understand the intended behavior.
2. Check the matching request, response, or object schema in `schemas/`.
3. If you are implementing HTTP, confirm the endpoint mapping in `openapi/mgp-openapi.yaml`.
4. Verify the executable behavior in `reference/gateway/` and `compliance/`.

## Notes

- The schemas are the canonical machine-readable source for MGP object validation.
- `schemas/response-envelope.schema.json` defines the shared outer response shell, while operation-specific response schemas define the exact `data` contract for each endpoint.
- The OpenAPI file mirrors the HTTP binding defined in `spec/http-binding.md`.
