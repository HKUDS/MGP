# Python SDK

本页介绍仓库中提供的 Python 客户端，它是当前最直接的 runtime-facing MGP client。

## SDK 提供什么

`sdk/python/` 当前提供：

- `MGPClient`：对参考 HTTP binding 的封装
- `PolicyContextBuilder`：帮助 runtime 构造一致的 `policy_context`
- search、audit、write-candidate 等类型化 helper
- 与协议错误码对齐的错误类型

## 适用场景

这个 SDK 的定位是 transport-focused client，不依赖参考网关内部实现。它适合：

- 在 Python runtime 中直接接入 MGP
- 作为 sidecar 或 integration harness 的客户端层
- 作为理解 MGP request shape 的最小运行时入口

## 与协议文档的关系

建议把 SDK 与以下文档一起看：

- `spec/runtime-client.md`
- `spec/runtime-write-candidate.md`
- `spec/http-binding.md`

这样可以同时理解“运行时应该怎样调用协议”和“SDK 实际提供了哪些入口”。

## 使用提示

- 当前 `v0.1.1` 响应面会稳定返回 `consumable_text`、`return_mode` 与 `redaction_info`
- runtime 侧应优先消费这些字段，而不是默认把原始 `memory.content` 当作总是 prompt-safe 的内容
