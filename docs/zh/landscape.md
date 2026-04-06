# 生态定位

本页说明 MGP 与周边标准、格式和产品的关系。

## 定位摘要

MGP 针对的是一个越来越明显的空白层：

- runtime 需要 durable memory
- 不同 backend 暴露的 API 与治理模型彼此不兼容
- 导出格式不能解决 runtime interoperability
- 工具连接协议不能解决 memory governance

MGP 通过定义一个 memory-specific protocol 来填补这层空白，并把 lifecycle、policy、conflict、audit 等语义一起纳入协议。

## 邻近标准与系统

### MCP

MCP 是 MGP 的 peer protocol，不是上层或下层。

MCP 标准化 runtime 如何连接 tools 与 resources。MGP 标准化 runtime 如何治理和访问 memory。两者可以在同一个 runtime 中并存，但互不从属。

### PAM

Portable AI Memory 关注 memory 数据的导出与导入可移植性。

它更像一种 vCard 风格的 interchange format，适合 portability、migration 和 archival，但不直接解决 governed write、search、lifecycle control、conflict handling 或 capability negotiation。

### MIF

Memory Interchange Format 同样偏向 portability，并带有 provenance 相关能力。

它对数据互换有价值，但范围仍然窄于 runtime-facing memory governance protocol。

### Mem0

Mem0 是托管记忆服务与产品。

它属于 backend 或 service layer，而不是 protocol-standard layer。在 MGP 生态里，它更适合作为 adapter 背后的实现目标。

### Zep

Zep 是 graph-native memory service。

它同样更接近实现层，而不是协议层。它的存在进一步说明 capability declaration 很重要，因为图原生后端与文件型或向量型后端的优势并不相同。

### MemGPT 与 Letta

MemGPT 与 Letta 更接近 runtime 或 framework 层。

它们说明了 agent memory management 的真实需求，但在 MGP 视角下，更适合作为潜在 runtime consumer，而不是协议替代品。

## 关系矩阵

| 名称 | 类别 | 主要关注点 | 与 MGP 的关系 |
| --- | --- | --- | --- |
| MCP | 协议 | 工具与资源连接 | Peer protocol |
| PAM | 格式 | 记忆导入导出可移植性 | Complementary format |
| MIF | 格式 | 记忆交换与 provenance | Complementary format |
| Mem0 | 产品或服务 | 托管记忆后端 | Potential backend |
| Zep | 产品或服务 | 图原生记忆后端 | Potential backend |
| MemGPT 或 Letta | 运行时或框架 | Runtime 内部的记忆管理 | Potential consumer |

## 为什么 MGP 仍然有价值

即使已经有这些系统，当前仍缺少一个被广泛采用的协议，同时标准化以下内容：

- canonical memory object
- governed runtime operation
- policy context propagation
- lifecycle semantics
- conflict contract
- audit 与 lineage contract
- backend capability declaration
- compatibility 与 compliance testing

这个缺口正是 MGP 值得推进的原因。
