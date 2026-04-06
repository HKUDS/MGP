# Conformance Profile

本页定义 MGP 在描述兼容性与实现范围时使用的 profile 术语。

它的目的，是让兼容性声明变得明确。一个 gateway、adapter 或 SDK 应该说明自己支持哪些 profile，以及这些支持是如何被验证的。

## 为什么需要 Profile

MGP 的协议面不只是一个 CRUD API，还包括：

- core governed-memory operation
- lifecycle 控制
- interop 与 async transfer 流程
- 依赖真实 provider 环境的 external service adapter

有了 profile，我们就可以清楚地说“这个实现支持 `Core` 和 `Lifecycle`”，而不是模糊地暗示“全部都支持”。

## Profile 定义

### Core

`Core` profile 是声明一般 MGP 兼容性时的最低必需面。

它覆盖：

- canonical memory object 与 policy context
- request / response envelope
- `write`、`search`、`get`、`update`
- `audit query`
- `GET /mgp/capabilities`
- search result normalization 与 `consumable_text`
- 协议级错误处理

主要来源：

- `spec/core-operations.md`
- `spec/search-results.md`
- `spec/protocol-behavior.md`
- `schemas/memory-object.schema.json`
- `schemas/policy-context.schema.json`
- `schemas/request-envelope.schema.json`
- `schemas/response-envelope.schema.json`

### Lifecycle

`Lifecycle` profile 在 `Core` 之上补充 governed state transition。

它覆盖：

- `expire`
- `revoke`
- `delete`
- `purge`
- 通过 `POST /mgp/initialize` 进行 lifecycle initialize 与 version negotiation
- retention 与 revocation 语义

主要来源：

- `spec/lifecycle.md`
- `spec/retention.md`
- `spec/versioning.md`

### Interop

`Interop` profile 在 `Core` 之上补充 transfer-oriented 与 async protocol feature。

它覆盖：

- `/mgp/write/batch`
- `/mgp/export`
- `/mgp/import`
- `/mgp/sync`
- async task handle 与 polling
- 在适用时的 partial-failure reporting

主要来源：

- `spec/async-operations.md`
- `spec/http-binding.md`
- `schemas/async-task.schema.json`
- `schemas/partial-failure.schema.json`

### ExternalService

`ExternalService` profile 面向依赖真实 provider 环境的 service-backed adapter。

它覆盖：

- 以真实 provider 为后端的 adapter，例如 `Mem0` 与 `Zep`
- provider-specific capability declaration
- 不在默认仓库 CI 矩阵内、而是在外部环境中完成的验证

这个 profile 并不替代 `Core`、`Lifecycle` 或 `Interop`。它说明的是：当一个实现依赖真实外部后端时，这些 profile 是如何被验证的。

## 验证矩阵

| Profile | 声明前提 | 常见证据 |
| --- | --- | --- |
| `Core` | 一般 MGP 兼容性 | schema 校验、gateway 行为、core compliance tests |
| `Lifecycle` | governed state transition 支持 | lifecycle compliance tests、initialize negotiation 行为 |
| `Interop` | batch/export/import/sync 支持 | async 与 interop compliance tests、task contract validation |
| `ExternalService` | 真实 provider-backed adapter 支持 | manifest 审核、provider 文档、opt-in integration validation |

## 当前仓库覆盖

当前仓库的状态：

- reference gateway 覆盖 `Core`、`Lifecycle`、`Interop`
- CI 会对 `memory`、`file`、`graph` 跑完整 reference suite
- `postgres` 和 `lancedb` 是生产导向的自管 adapter 路径，可以在默认 CI 矩阵之外验证同一组 profile
- `mem0` 和 `zep` 是正式记录的 service-backed adapter，但它们需要真实 provider 环境，因此不在默认 CI 矩阵里

## 声明规则

实现方应使用 profile 名称来声明兼容性，而不是使用“fully compatible”这类模糊标签。

推荐写法：

- “Supports `Core`”
- “Supports `Core` + `Lifecycle`”
- “Supports `Core` + `Lifecycle` + `Interop`”
- “Supports `Core` through an `ExternalService` adapter validated in a provider environment”

只有在以下条件都成立时，才应该声明某个 profile：

- 相关 schema 已实现
- 相关 HTTP 或 SDK surface 已暴露
- 相关行为有可执行验证支撑，而不是只有文档描述
