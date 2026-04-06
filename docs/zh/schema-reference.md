# Schema 参考

本页汇总 MGP 的机器可读协议资产，并说明这些资产与代码和文档的关系。

## JSON Schema

MGP 的 JSON Schema 主要分成几类：

### 核心对象与上下文

- `schemas/memory-object.schema.json`
- `schemas/memory-candidate.schema.json`
- `schemas/policy-context.schema.json`
- `schemas/request-envelope.schema.json`
- `schemas/response-envelope.schema.json`

### Memory 内容与搜索

- `schemas/memory-content-preference.schema.json`
- `schemas/memory-content-semantic-fact.schema.json`
- `schemas/memory-content-relationship.schema.json`
- `schemas/memory-content-procedural-rule.schema.json`
- `schemas/recall-intent.schema.json`
- `schemas/search-result-item.schema.json`
- `schemas/redaction-info.schema.json`
- `schemas/partial-failure.schema.json`
- `schemas/error-code.schema.json`
- `schemas/return-mode.schema.json`
- `schemas/retrieval-mode.schema.json`
- `schemas/score-kind.schema.json`

### 能力与协商

- `schemas/backend-capabilities.schema.json`
- `schemas/protocol-capabilities.schema.json`
- `schemas/runtime-capabilities.schema.json`
- `schemas/negotiated-capabilities.schema.json`
- `schemas/adapter-manifest.schema.json`

### Lifecycle 与 Async

- `schemas/initialize.request.schema.json`
- `schemas/initialize.response.schema.json`
- `schemas/async-task.schema.json`
- `schemas/progress-event.schema.json`
- `schemas/get-task.request.schema.json`
- `schemas/get-task.response.schema.json`
- `schemas/cancel-task.request.schema.json`
- `schemas/cancel-task.response.schema.json`

### 核心 Operation 的请求响应

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

## OpenAPI 资产

- `openapi/mgp-openapi.yaml`

## 如何使用这些资产

建议的阅读顺序是：

1. 先看 `spec/` 中的相关语义文档。
2. 再看 `schemas/` 中对应的 request、response 或 object schema。
3. 如果是 HTTP 实现，再看 `openapi/mgp-openapi.yaml`。
4. 最后核对 `reference/gateway/` 与 `compliance/` 中的实际行为与测试。

## 说明

- Schema 是 MGP object validation 的 canonical machine-readable source。
- `schemas/response-envelope.schema.json` 只描述共享外壳；每个 operation-specific response schema 决定对应 endpoint 的精确 `data` 合同。
- OpenAPI 描述的是 `spec/http-binding.md` 对应的 HTTP surface。
- 文档、schema 与代码必须互相印证，不能只有其中一层存在。
