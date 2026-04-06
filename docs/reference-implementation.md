# Reference Implementation

This page introduces the runnable Python gateway that demonstrates MGP reference behavior.

## What Lives In `reference/`

The reference implementation consists of:

- `reference/gateway/` — FastAPI app, routing, request/response validation, config, middleware, task handling
- `reference/policy/` — minimal policy hook
- `reference/audit/` — JSON Lines audit sink

The gateway validates both request bodies and response bodies against the published schemas.

## Operational Guide

The canonical install, CLI, adapter, and configuration guide lives in the repository README at `reference/README.md`.

Use that README as the single source of truth for:

- repository-path and package-path installation
- `mgp-gateway` CLI usage
- adapter-specific runtime flags
- container startup and smoke-test commands

The reference gateway now includes an official middleware hook for:

- API key authentication
- bearer token authentication
- tenant-header to `policy_context.tenant_id` consistency checks
- request ID propagation and structured request logging

These controls are intentionally minimal. They are there to demonstrate a production-shaped integration point, not to replace a full deployment security architecture. See [Security Baseline](security-baseline.md).

## Operational Endpoints

In addition to the MGP protocol endpoints, the gateway exposes:

- `GET /healthz`
- `GET /readyz`
- `GET /version`

These endpoints are operational helpers and are not part of the governed-memory protocol contract itself.

## Reference Protocol Endpoints

The full endpoint list, cURL examples, and operational notes are documented in `reference/README.md`.

## How To Read This Implementation

This implementation is not meant to replace a production gateway. It provides a clear, runnable, testable protocol behavior baseline. Read it alongside:

- `spec/` for protocol semantics
- `schemas/` for message validation
- `openapi/mgp-openapi.yaml` for the HTTP binding
- `compliance/` for verification

## Practical Notes

- the in-memory adapter is the simplest path for local testing
- the file adapter stores each memory object as a JSON file
- audit events are appended as JSON Lines and can be inspected directly
- `initialize`, async tasking, and interop endpoints are optional protocol layers implemented by the reference gateway
