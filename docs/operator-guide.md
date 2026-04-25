# Operator Guide

This page focuses on day-2 concerns for running the reference gateway.

## What To Monitor

- gateway process health through `/healthz`
- adapter readiness through `/readyz`
- running version and adapter selection through `/version`
- audit sink growth and rotation behavior
- adapter-specific storage health such as PostgreSQL or OceanBase availability

## Logs

The reference gateway emits structured request logs and request IDs through middleware.

Operators should preserve:

- request ID
- method
- path
- status code
- environment

Those fields make it easier to connect runtime errors, gateway behavior, and audit records.

## Audit Sink

Default behavior:

- audit events are appended to a JSON Lines file
- the path is configurable through `MGP_AUDIT_LOG`

Operational considerations:

- rotate or ship the audit log before it grows without bounds
- protect the file from cross-tenant access
- align audit retention with deployment policy rather than memory retention alone

## Adapter Operations

### File

- ensure the storage directory exists and is writable
- back up the storage directory together with the audit log if you use it operationally

### Graph

- treat the SQLite database file as stateful infrastructure
- include it in backups if it is used outside local testing

### PostgreSQL

- monitor connectivity, disk growth, and index health
- back up the database using your normal PostgreSQL operational process
- keep schema migrations under change control

### OceanBase

- monitor MySQL-compatible connectivity (`MGP_OCEANBASE_DSN` / discrete `MGP_OCEANBASE_*` variables), tenant scope, and disk growth
- back up the database through OceanBase's standard operational tooling
- when running on `oceanbase/seekdb`, treat the single-node container as stateful infrastructure and snapshot its data volume

## Lifecycle And Deletion

When operators process delete or purge incidents, confirm:

- whether the gateway call succeeded
- whether the adapter persisted the intended state transition
- whether downstream copies or exports also need cleanup
- whether audit records capture the action and request correlation

## Incident Response Checklist

1. Confirm the affected adapter and tenant scope.
2. Locate the relevant request or audit correlation identifier.
3. Inspect the gateway logs around that request.
4. Inspect adapter-local state or backend state.
5. Re-run focused compliance or smoke tests before restoring service if the fix touched protocol behavior.
