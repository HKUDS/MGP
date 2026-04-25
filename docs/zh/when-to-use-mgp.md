# 什么时候适合用 MGP

本页回答两个问题：什么时候 MGP 是合适抽象，什么时候直接用轻量库或 provider SDK 就够了。

## 适合用 MGP 的情况

当你满足下面任意一类需求时，MGP 往往是更合适的选择：

- 多个 runtime 或多个团队需要共享一套 governed memory contract
- 你需要 `expire`、`revoke`、`delete`、`purge` 这类 lifecycle control
- 你需要让 auditability 与 policy context 一起进入 memory operation
- 你希望 backend 可替换，而 runtime 侧 memory 代码不跟着重写
- 你需要 compliance-style verification，而不是只信任某个 provider SDK

一句话概括：

- 当 memory 变成基础设施时，用 MGP
- 当 memory 只是实现细节时，用轻量库也可以

## 对 Runtime 团队来说

如果你在做 agent runtime，MGP 适合这些场景：

- prompt 组装依赖跨 session 的 durable recall
- 你需要 `consumable_text` 这类统一的 prompt-safe result shape
- 你想先通过 sidecar 低风险接入，再演进到 native SDK
- 你预计后面会在自管理后端和外部服务之间切换

## 对平台团队来说

如果你在做平台层，MGP 适合这些场景：

- 你需要让 file、relational、graph、service-backed memory systems 共用一套合同
- 你希望 adapter 对 capability 做真实声明
- 你需要在不绑定某个 vendor 的前提下治理 memory 行为
- 你希望有可版本化的 reference gateway、OpenAPI surface 与 schema

## 对协议实现者来说

如果你想实现 gateway 或 adapter，MGP 提供的是一整套材料：

- `spec/` 中的语义说明
- `schemas/` 中的机器可读合同
- `openapi/` 中的 HTTP binding
- `compliance/` 中的可执行验证

这也是 MGP 相比内部私有 API 更有价值的地方。

## 什么时候轻量库就够了

如果你的场景是下面这样，可能暂时不需要 MGP：

- 一个 Python 应用只接一个 memory provider
- 你只想要一层很薄的 provider abstraction
- audit、lifecycle、compatibility claim 不是当前重点
- 你还在探索产品形态，不想先引入协议层复杂度

这种时候，直接用轻量库或 provider SDK 可能会更快。

## 它和 Provider SDK / 轻量库的关系

MGP 不是想替代所有应用层 memory SDK。

更合适的理解方式是：

- direct provider SDK 优化的是单一 backend
- lightweight library 优化的是应用接入便利性
- MGP 优化的是 runtime 与 backend 之间的 governed interoperability

所以，当治理与可移植性变重要时，MGP 可以通过 adapter 建在 provider SDK 或轻量库之上。

## 采纳路径

常见的起步方式：

1. 先用 reference gateway 和 `mgp-client` 跑通。
2. 先通过 sidecar 以 `shadow` mode 接入。
3. 稳定后再切换到 native SDK 路径。
4. 当需要自管理生产部署时，引入 PostgreSQL 或 OceanBase 这类生产导向 backend。
