# Architecture

This page maps the MGP protocol layers to the repository directories that implement or verify them.

## Layered View

```mermaid
flowchart LR
  subgraph runtimes ["Runtimes"]
    runtime[AgentRuntime]
    nativeClient[NativeClientOrSdk]
    sidecar[SidecarBridge]
  end

  subgraph contracts ["Contracts"]
    specs[SpecsInSpec]
    schemas[SchemasInSchemas]
    openapi[OpenApiInOpenapi]
  end

  subgraph gateway ["ReferenceGateway"]
    app[FastApiApp]
    router[AdapterRouter]
    validation[SchemaValidation]
    semantics[GatewaySemantics]
    tasks[AsyncTaskStore]
    policy[PolicyHook]
    audit[AuditSink]
  end

  subgraph adapters ["AdapterImplementations"]
    memory[MemoryAdapter]
    file[FileAdapter]
    graphAdapter[GraphAdapter]
    services[Mem0AndZepAdapters]
  end

  subgraph verification ["Verification"]
    compliance[ComplianceTests]
    examples[Examples]
    docs[DocsSite]
  end

  runtime --> nativeClient
  runtime --> sidecar
  nativeClient --> app
  sidecar --> app

  specs --> app
  schemas --> validation
  schemas --> compliance
  openapi --> app

  app --> router
  app --> validation
  app --> semantics
  app --> tasks
  app --> policy
  app --> audit

  router --> memory
  router --> file
  router --> graphAdapter
  router --> services

  compliance --> app
  compliance --> adapters
  examples --> app
  docs --> specs
  docs --> openapi
```

## Repository Mapping

| Layer | Repository paths | What they do |
| --- | --- | --- |
| Protocol semantics | `spec/` | define behavior, terms, and compatibility boundaries |
| Machine-readable contracts | `schemas/`, `openapi/` | define JSON validation rules and the HTTP binding surface |
| Runnable gateway | `reference/gateway/`, `reference/policy/`, `reference/audit/` | implement the reference FastAPI service, policy hook, audit sink, and async task support |
| Backend normalization | `adapters/` | normalize backend behavior into the MGP adapter contract |
| Runtime integration | `sdk/python/`, `integrations/nanobot/` | provide client-side helpers and the first runtime adoption path |
| Verification | `compliance/`, `examples/` | prove protocol behavior through tests and runnable examples |
| Reader-facing documentation | `docs/`, `README.md` | explain the system and map readers to the right source files |

## Reference Request Flow

The following sequence diagram shows how a typical `WriteMemory` request flows through the reference gateway:

```mermaid
sequenceDiagram
    participant R as AgentRuntime
    participant G as MGPGateway
    participant V as SchemaValidation
    participant P as PolicyHook
    participant A as AuditSink
    participant AR as AdapterRouter
    participant BE as Backend

    R->>G: POST /mgp/write
    G->>V: Validate request against schema
    V-->>G: Valid
    G->>P: Evaluate policy context
    P-->>G: Decision (allow/deny/transform)
    G->>AR: Dispatch write to adapter
    AR->>BE: Store memory object
    BE-->>AR: Stored
    AR-->>G: Normalized result
    G->>A: Record audit event
    G->>V: Validate response against schema
    V-->>G: Valid
    G-->>R: Response envelope
```

Step by step:

1. A runtime calls MGP through a native client or a sidecar bridge.
2. The reference gateway validates the request against published schemas.
3. The gateway evaluates the policy context through the policy hook.
4. The adapter router dispatches the operation to the selected adapter.
5. The adapter maps the request to a concrete backend model and returns normalized results.
6. The audit sink records the operation.
7. The response is validated and returned.

## Why This Split Exists

The repository separates protocol prose, schemas, runnable code, and tests so that each concern has a clear source of truth:

- `spec/` explains what the protocol means.
- `schemas/` and `openapi/` state what valid messages look like.
- `reference/` and `adapters/` show how the protocol behaves in code.
- `compliance/` proves whether an implementation actually conforms.
