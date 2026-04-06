# 术语表

本页提供 MGP 的核心术语定义。

## memory object

memory object 是通过 MGP 交换的 canonical governed memory 单元。

示例：一个存储的用户偏好（如"偏好简洁回复"）就是一个 memory object。

## subject

subject 是 memory 所归属或所描述的实体，可以是 user、agent、organization、task 或 session。

示例：关联到用户 `u_123` 的偏好，其 subject 就是该用户。

## scope

scope 定义 memory 生效、可见或应当适用的边界。

示例：scope 为 `session` 的 memory 不应被当作持久的用户级事实。

## type

type 标识 memory object 的语义类别。

示例：用户偏好与情节事件属于不同的 memory type。

## policy context

policy context 是请求侧的上下文元数据，用来说明谁在操作、代表谁操作、在什么任务下操作，以及操作受什么治理约束。

示例：一个 write 请求可以包含 acting agent、tenant、risk level 和 task identifier 作为 policy context。

## retention

retention 描述 memory 应该被保留多久，以及何时进入 review、expiration 或 deletion 流程。

示例：session 级 memory 可能有较短的 retention，而经过验证的用户档案事实可能是持久的。

## expiration

expiration 是 memory 不再被视为 active 的协议事件或状态迁移，通常因为有效期或 retention window 结束。

示例：任务范围的 memory 可能在任务关闭后自动过期。

## revocation

revocation 是在原 retention 周期之外，对 memory 的显式撤销。

示例：用户在纠正偏好后可以撤销之前存储的旧偏好。

## supersede

supersede 表示一个 memory 被更新或更权威的 memory 所替代，同时保留两者之间的关系。

示例：纠正后的城市信息可以 supersede 之前错误的城市值。

## conflict

conflict 表示两个或多个 memory 无法在不澄清、不排序或不定义共存规则的前提下同时成立。

示例：同一 subject 的两个 memory 声称不同的生日就构成 conflict。

## lineage

lineage 记录 memory 如何被创建、派生、更新，或与其他 memory 发生关联。

示例：从对话记录中派生的摘要 memory 应保留指向原始来源的 lineage link。

## adapter

adapter 负责把具体 backend 的原生模型与行为映射到 MGP-compatible contract。

示例：一个 file-backed adapter 可以将 markdown 笔记转化为 canonical memory object。

## capability

capability 是实现方声明的一项协议能力，用来告诉 runtime 某个 adapter 或 backend 可以做什么、不能做什么。

示例：一个 backend 可以声明支持 search 但不支持原生 TTL。

## runtime

runtime 是在代表用户或其他主体执行任务时调用 MGP 的 agent-side system。

示例：一个 agent runtime 可以使用 MGP 来 recall 和 commit governed memory。

## backend

backend 是最终持久化或提供 memory 数据的具体存储系统。

示例：graph database、vector database 或 file-based store 都可以作为 MGP 背后的 backend。
