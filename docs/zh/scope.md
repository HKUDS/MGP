# 范围定义

本页定义 MGP 在当前协议阶段真正负责的内容。

## 范围声明

MGP 负责 AI 系统中的 persistent 与 semi-persistent memory interaction。它统一的是 runtime 与 memory backend 之间的合同，让 memory 能够在异构实现之间以一致的方式被写入、搜索、读取、更新、过期、撤销和审计。

## 范围内

### Memory Object

MGP 定义 canonical memory object，用来表示用户事实、偏好、情节事件、语义知识以及其他需要治理的记忆单元。

### Memory Operation

MGP 在协议层定义以下操作：

- write
- search
- get
- update
- expire
- revoke
- delete
- purge

这些操作是协议合同，不是某个后端的私有 API。

### Policy Context 传递

MGP 规定 runtime 如何表达一个记忆操作发生时的上下文，包括谁在操作、代表谁操作，以及请求所处的任务或风险背景。

### Lifecycle 语义

MGP 把 retention、expiration、supersession、revocation 这类治理语义纳入协议层，不把记忆退化成单纯 CRUD。

### Conflict 语义

MGP 规定 runtime 与 backend 如何表达冲突记忆、矛盾处理和冲突解决模式。

### Audit 与 Lineage

MGP 定义 audit event 与 lineage link 的 schema 与合同，使读写行为可以被追踪、解释和回溯。

### Capability 声明

MGP 规定 backend 或 adapter 如何声明自己支持哪些协议能力，避免 runtime 假设所有后端都具备一致能力。

### Protocol Binding

MGP 拥有自己的 wire format 与 transport binding。当前首个 binding 是 JSON over HTTP，未来可以扩展到其他绑定方式。

## 范围外

### Prompt Window 管理

MGP 不定义 prompt context window 如何组装、压缩或裁剪。

### 通用日志系统

MGP 不替代应用日志、可观测性系统或 tracing 系统。

### 全量工作流状态

MGP 不尝试建模 workflow engine、orchestration framework 或一般应用状态机的完整语义。

### Memory 生成算法

MGP 不决定什么内容应该成为 memory，也不规定何时提取 memory 或采用什么 summarization pipeline。

### Embedding 与 Ranking

MGP 不定义 embedding 算法、相似度计算、排序模型或检索打分逻辑。

### Tool 与 Resource 连接

MGP 不负责工具调用或通用资源访问。这类问题属于 MCP 等其他协议的范围。

## 设计原则

- governed memory 是协议层面的第一类问题。
- 协议必须能跨多种 backend 形态工作。
- 即使 backend 能力不同，核心语义也必须保持稳定。
- MGP 应标准化合同，而不是强制单一实现方式。
