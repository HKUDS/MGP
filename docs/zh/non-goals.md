# 非目标

本页记录 MGP 明确不打算解决的问题。

## MGP 不是 Memory Store

MGP 不提供自己的 canonical database engine。它是一个面向 governed memory interoperability 的协议，不是新的存储产品。

## MGP 不替代现有数据库

MGP 不替代以下系统：

- vector database
- graph database
- relational database
- document store
- file-backed memory system

这些系统都可以继续作为 MGP adapter 或 gateway 背后的实际实现。

## MGP 不定义 Retrieval Science

MGP 不定义：

- embedding algorithm
- similarity function
- ranking model
- relevance scoring model
- summarization quality metric

实现方只要在协议层呈现出 MGP 兼容行为，就可以自由选择内部检索栈。

## MGP 不定义厂商内部策略引擎

MGP 统一的是 policy context 和 policy outcome 的合同面，而不是指定某种 authorization engine、rule language 或内部权限模型。

## MGP 不是 Agent Framework

MGP 不提供 orchestration、planning、chat UX、tool routing 或 multi-agent runtime 行为。它服务于 runtime，而不是替代 runtime。

## MGP 不是 Hosted Service

MGP 不是 SaaS 平台、control plane，也不是 admin console。

## MGP 不是静态导出格式

MGP 不试图替代 PAM、MIF 这类 interchange format。那些格式主要解决数据导出导入与可移植性问题，MGP 关注的是运行时治理与后端互操作。

## MGP 不是 MCP 的子层

MGP 是独立的 peer protocol，不是 MCP 的 extension、transport profile 或从属层。

MCP 处理工具与资源连接，MGP 处理 governed memory。一个 runtime 可以同时实现两者，但两套协议各自拥有自己的合同边界。

## MGP 不强行归一化所有原生高级能力

MGP 不会试图把每个厂商后端的高级特性都纳入 core protocol。实现方可以通过 extension 暴露额外能力，但核心协议必须保持可移植与稳定。
