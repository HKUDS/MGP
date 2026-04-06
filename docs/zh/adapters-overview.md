# 适配器总览

本页总结了当前 MGP 仓库中的适配器家族，并说明它们与协议合同之间的关系。

## Adapter 的角色

MGP adapter 的作用，是把具体后端模型映射到统一的 MGP protocol surface。每个 adapter 都应当：

- 实现基础 adapter interface
- 提供合法的 `manifest.json`
- 明确声明 capability
- 保持 canonical memory object shape
- 明确写出限制条件

另见：[适配器编写指南](adapter-guide.md)。

## 生产环境说明

仓库内置的 in-memory、file 和 graph 适配器是**参考实现**，设计目的是：

- 协议验证与合规测试
- 展示不同后端形态如何映射到 MGP 合同
- 作为适配器开发者的起点

它们**不建议直接用于生产环境**。生产部署时，请针对实际存储基础设施构建或选用适配器。参见 [适配器编写指南](adapter-guide.md)。

Mem0 和 Zep 不同：它们是面向真实外部记忆服务的 **service-backed adapters**。当对应服务已经配置并可用时，它们可以作为真实部署路径使用。

PostgreSQL adapter 又是另一类：它是一个**生产导向的基线 adapter**，用来说明如何在不依赖某个托管记忆厂商的前提下，把 MGP 跑在关系型后端之上。

LanceDB adapter 与 PostgreSQL 更接近，但面向的是向量检索场景。它是一个**生产导向的自管 adapter**，适合希望在 canonical MGP memory object 之上获得 semantic / hybrid recall、同时又不依赖托管 memory service 的团队。

在真实使用时：

- Mem0 需要 API 凭证以及项目级配置
- Zep 需要 API 凭证以及共享 graph 命名空间
- 两者相较于直接调用原生 SDK 都会增加少量延迟，因为适配器还要补上 MGP 归一化与生命周期语义

## 参考适配器家族

### In-Memory Adapter

源码位置：

- `adapters/memory/adapter.py`
- `adapters/memory/README.md`

作用：

- 作为基线参考适配器
- 作为最容易通过 compliance 的目标
- 作为最容易观察协议行为的内存实现

### File Adapter

源码位置：

- `adapters/file/adapter.py`
- `adapters/file/README.md`

作用：

- 提供持久化 JSON 文件存储示例
- 证明 MGP 不依赖特定数据库产品

### Graph Adapter

源码位置：

- `adapters/graph/adapter.py`
- `adapters/graph/README.md`

作用：

- 提供面向关系语义的参考适配器
- 展示通过 extension 驱动的 graph semantics

### PostgreSQL Adapter

源码位置：

- `adapters/postgres/adapter.py`
- `adapters/postgres/README.md`
- `adapters/postgres/migrations/`

作用：

- 作为生产导向的 SQL adapter 基线
- 展示持久化多租户存储、索引化搜索与 lifecycle state handling
- 作为希望把 MGP 跑在自有关系型基础设施上的团队起点

### LanceDB Adapter

源码位置：

- `adapters/lancedb/adapter.py`
- `adapters/lancedb/README.md`

作用：

- 作为生产导向的向量 adapter 基线
- 展示 canonical memory storage、semantic search 与可选 hybrid recall 如何映射到 LanceDB
- 作为希望把 MGP 跑在自管向量基础设施上的团队起点

### Mem0 Adapter

源码位置：

- `adapters/mem0/adapter.py`
- `adapters/mem0/README.md`

作用：

- 作为面向 Mem0 的 service-backed adapter
- 以 Mem0 作为 source of truth
- 作为已采用 Mem0 团队的生产接入路径

### Zep Adapter

源码位置：

- `adapters/zep/adapter.py`
- `adapters/zep/README.md`

作用：

- 作为面向 Zep 的 service-backed adapter
- 以 Zep episode 作为 source of truth
- 作为已采用 Zep Cloud 团队的生产接入路径

## 验证预期

当前 CI 覆盖：

- `memory` 会跑完整 compliance
- `file` 会跑完整 compliance
- `graph` 会跑完整 compliance

额外的本地验证路径：

- 配好 `MGP_POSTGRES_DSN` 后，`postgres` 也可以跑同一套 compliance
- 安装 LanceDB 并提供 embedding 配置后，`lancedb` 也可以跑同一套 compliance
- 依赖外部服务的 adapter 仍然需要在对应服务环境可用时再做端到端验证

按 profile 来看：

- `memory`、`file`、`graph` 参与的是默认的 `Core` + `Lifecycle` + `Interop` 参考验证矩阵
- `postgres` 是生产导向的 adapter 路径，可以在默认 CI 之外覆盖同一组 profile
- `lancedb` 也是生产导向的自管 adapter 路径，可以在默认 CI 之外覆盖同一组 profile
- `mem0` 和 `zep` 属于 `ExternalService` adapter，验证需要真实 provider 环境

另见：[Conformance Profile](conformance-profiles.md)。

## Manifest 与 Capability 模型

每个 adapter 都会附带一个 `manifest.json`，用于声明：

- backend kind
- supported MGP version
- supported memory type 与 scope
- backend capability
- extension namespace

主要合同文件：

- `schemas/adapter-manifest.schema.json`
- `schemas/backend-capabilities.schema.json`
- `adapters/*/manifest.json`

解释规则：

- 这里的 capability 描述的是 backend-native 或 adapter-native support
- 它不会自动扩大或缩小 gateway 通过策略层或 emulation 暴露出来的 HTTP surface

## 实现边界

不同 adapter 可以在存储布局、索引策略、conflict support、TTL support 和 graph support 上存在差异，但不能悄悄改写核心协议合同。

这意味着：

- 协议语义必须保持稳定
- 后端差异必须被显式声明
- 厂商私有字段必须放在 `extensions` 中
