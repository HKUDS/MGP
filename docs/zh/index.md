# MGP 文档

欢迎来到 **Memory Governance Protocol** 文档站。MGP 是一个开放协议，统一了 AI 运行时写入、召回、治理和审计持久化记忆的方式，适用于各种异构后端。

**第一次来？** 直接跳到 **[快速入门](getting-started.md)** 指南——五分钟内跑通一个受治理记忆网关。

## MGP 是什么？

MGP 定义了一套统一的受治理记忆契约，但本身不是记忆数据库。你的 Agent 运行时只需对接一套协议，任何兼容后端都能直接工作——无论是内存、文件、图、关系型、向量，还是托管服务。

MGP 与 **MCP 是对等协议**。MCP 管理工具和资源，MGP 管理持久化记忆。两者互补，可以在同一运行时中共存。

## 阅读路径

### 我想快速上手

1. [快速入门](getting-started.md) — 安装、启动网关、写入与搜索第一条记忆
2. [Python SDK](python-sdk.md) — `MGPClient`、`AsyncMGPClient` 及辅助工具
3. [示例总览](examples-overview.md) — 可运行的端到端示例

### 我想理解协议

1. [项目概览](project-overview.md) — 目标、边界与架构
2. [架构说明](architecture.md) — 分层视图与请求流程
3. [协议参考](protocol-reference.md) — 完整操作语义
4. [Schema 参考](schema-reference.md) — 所有 JSON Schema 说明
5. [MGP 与 MCP](mgp-vs-mcp.md) — 两个协议的关系

### 我想接入或部署

1. [参考实现](reference-implementation.md) — Python 网关
2. [适配器编写指南](adapter-guide.md) — 自建适配器
3. [Sidecar 接入](sidecar-integration.md) — 桥接已有运行时
4. [部署指南](deployment-guide.md) — 生产部署模式
5. [安全基线](security-baseline.md) — 安全考量

### 我想验证合规性

1. [Conformance Profile](conformance-profiles.md) — `Core`、`Lifecycle`、`Interop`、`ExternalService`
2. [合规测试](compliance-suite.md) — 运行测试套件
3. [适配器总览](adapters-overview.md) — 适配器兼容性矩阵

## 完整站点地图

**总览**

- [项目概览](project-overview.md)
- [架构说明](architecture.md)
- [范围定义](scope.md)
- [非目标](non-goals.md)
- [生态定位](landscape.md)
- [术语表](glossary.md)
- [MGP 与 MCP](mgp-vs-mcp.md)
- [什么时候适合用 MGP](when-to-use-mgp.md)

**协议**

- [协议参考](protocol-reference.md)
- [Schema 参考](schema-reference.md)
- [Conformance Profile](conformance-profiles.md)

**实现**

- [参考实现](reference-implementation.md)
- [适配器编写指南](adapter-guide.md)
- [适配器总览](adapters-overview.md)
- [Python SDK](python-sdk.md)

**质量与接入**

- [合规测试](compliance-suite.md)
- [Sidecar 接入](sidecar-integration.md)
- [示例总览](examples-overview.md)
- [部署指南](deployment-guide.md)
- [运维指南](operator-guide.md)
- [安全基线](security-baseline.md)
- [贡献指南](contributing.md)
