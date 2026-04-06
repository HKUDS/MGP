# Security Baseline

This page records the minimum security expectations for deploying or integrating MGP.

MGP defines governance contracts, not a full security product. Authentication, transport protection, secret management, and infrastructure isolation still belong to the deploying system. This page explains the baseline controls a real deployment should put around the protocol.

## Scope

MGP itself standardizes:

- policy context propagation
- lifecycle intent such as delete, purge, revoke, and expire
- audit and lineage structures
- capability declaration and negotiation

MGP does not standardize:

- one mandatory authentication protocol
- one mandatory identity provider
- one mandatory policy engine implementation
- one mandatory storage security model

That boundary is intentional, but it does not remove the need for deployment-level controls.

## Transport Security

Deployments should:

- terminate all remote MGP traffic over TLS
- avoid plaintext traffic across trust boundaries
- pin internal certificates or use managed trust roots in production environments
- document whether sidecars, runtimes, and gateways communicate over loopback, private networks, or public ingress

If HTTP is used without TLS, treat it as local development only.

## Authentication And Identity

MGP requests always carry `policy_context`, but `policy_context` is not authentication by itself.

Deployments should:

- authenticate the caller before trusting request contents
- bind authenticated identity to `policy_context.actor_agent` and tenant fields
- reject requests where transport identity and declared policy context do not match deployment rules
- document whether the gateway trusts upstream identity headers, API keys, JWTs, mTLS, or another mechanism

Recommended rule:

- transport identity proves who is calling
- `policy_context` explains who the runtime claims to be acting for
- policy evaluation decides whether that action is allowed

## Tenant Isolation

Multi-tenant deployments should:

- require a stable tenant identifier
- scope adapter storage and audit records by tenant
- ensure cross-tenant reads are impossible unless explicitly modeled and audited
- treat missing or ambiguous tenant identifiers as a denial condition, not a default-open case

When an adapter supports multiple subjects or scopes, the deployment should still make tenant binding explicit rather than inferring it from free-form metadata.

## Audit Retention And Integrity

Audit data is part of the governed-memory story and should be protected accordingly.

Deployments should:

- write audit events to append-friendly storage
- document audit retention periods separately from memory retention periods
- protect audit sinks from silent mutation or cross-tenant access
- capture correlation identifiers that allow runtime requests, adapter actions, and backend errors to be traced together

If audit redaction is required, do it in a documented and reviewable way rather than dropping audit records silently.

## Delete, Purge, And Responsibility Boundaries

Lifecycle requests such as `delete` and `purge` create accountability requirements.

Deployments should:

- document which backend fields are soft-deleted versus hard-deleted
- record purge outcomes in audit trails
- define how downstream caches, exports, or replicas are cleaned up
- make clear whether the gateway, adapter, or external provider is the final deletion authority

Do not imply that a successful protocol-level purge automatically guarantees deletion from every external system unless that behavior is actually enforced and documented.

## Secret Management

Deployments should:

- keep provider credentials out of the repository
- inject secrets through environment management or secret stores
- scope provider credentials by project, tenant, or environment where possible
- rotate credentials without requiring protocol changes

Reference integrations should use placeholders, `.env.example` files, or external configuration paths rather than committed credentials.

## External Provider Trust Boundaries

Service-backed adapters introduce a second trust boundary.

Before using an external provider adapter, document:

- which data fields leave your environment
- how the provider handles retention and deletion
- whether provider-side graph extraction, indexing, or deduplication changes your original content
- which failures can leave partial results or delayed consistency

This is especially important for adapters that send content to provider-side models or indexing pipelines.

## Operational Controls

Production deployments should also define:

- rate limits and abuse controls
- request timeouts and retry rules
- structured logging and request identifiers
- backup and restore procedures for stateful adapters
- incident response for policy or deletion failures

## Practical Deployment Rule

Treat MGP as one layer inside a larger system:

- transport and identity controls protect the perimeter
- policy context and audit preserve governance intent
- adapters and backends enforce storage behavior
- deployment documentation explains the gaps between those layers
