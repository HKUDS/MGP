# 协议参考

本页是对 MGP 协议面的正式导览，用来说明协议文档、Schema 和 HTTP 绑定之间的对应关系。

## Canonical Protocol Assets

MGP 的协议源材料分成三类，并且必须保持一致：

- `spec/` 负责解释语义和预期行为。
- `schemas/` 负责给出 canonical validation contract。
- `openapi/mgp-openapi.yaml` 负责描述 HTTP binding。

只有当这三层与实际运行行为一致时，协议实现才算真正对齐。

## 对齐原则

- `spec/` 是解释协议语义的主来源。
- `schemas/` 下的 operation-specific schema 是精确 request / response shape 的 canonical machine-readable source。
- `schemas/response-envelope.schema.json` 只定义共享外壳；每个 endpoint 的精确 `data` 结构以对应的 response schema 为准。
- `openapi/mgp-openapi.yaml` 负责映射 HTTP surface，不应发明与 schema 冲突的 wire shape。

当前仓库中的合同对齐检查：

- `scripts/validate_schemas.py` 校验已发布 schema 的合法性
- `scripts/validate_openapi.py` 校验 OpenAPI 文档及其引用
- `scripts/check_contract_drift.py` 校验 `spec/`、`schemas/`、`openapi/` 与 reference gateway 的版本和路由没有漂移
- CI 会在跑 compliance 矩阵之前先执行这些检查

## 核心对象模型

协议围绕 canonical memory object 以及包裹它的 request 和 response envelope 展开。

关键 schema 资产包括：

- `schemas/memory-object.schema.json`
- `schemas/memory-candidate.schema.json`
- `schemas/policy-context.schema.json`
- `schemas/request-envelope.schema.json`
- `schemas/response-envelope.schema.json`

协议还包含常见 memory type 的结构化 content schema，例如 preference、semantic fact、relationship 和 procedural rule。

## 建模速查

除非你的 runtime 在业务上有更强约束，否则建议优先采用下面这些默认搭配：

| 场景 | `subject.kind` | `scope` | `acting_for_subject` | `task_id` | `session_id` |
| --- | --- | --- | --- | --- | --- |
| 长期用户偏好或事实 | `user` | `user` | 当前用户 | 可选 | 可选 |
| 会话内临时记忆 | `user` 或 `session` | `session` | 当前用户或当前 session subject | 可选 | 当前会话 |
| 工作流内局部记忆 | `task` 或 `user` | `task` | 当前用户 | 当前 workflow/task | 可选 |
| agent 自身的操作性记忆 | `agent` | `agent` | 当前操作者或拥有者 | 可选 | 可选 |

解释规则：

- `acting_for_subject` 表示 runtime 在策略评估时“代表谁在操作”
- `subject` 表示“这条 memory 是关于谁的”
- `task_id` 表示 runtime 内部的 workflow / execution correlation，不是 `/mgp/tasks/*` 返回的协议异步任务对象
- `session_id` 用于 tracing 与会话身份标识，不等于直接替代 `scope: session`

## 核心操作

核心操作语义定义在 `spec/core-operations.md`，并通过参考 HTTP binding 对外暴露。

必须支持的 governed-memory operation 包括：

- write
- search
- get
- update
- expire
- revoke
- delete
- purge
- audit query

必需的 discovery 支撑面：

- `GET /mgp/capabilities`

每个 operation 都同时对应 `schemas/` 下的 request 与 response schema，以及 `reference/gateway/app.py` 里的参考行为。

## 搜索与运行时消费

MGP 不只定义"搜出来什么"，还定义"运行时应该怎样安全地消费搜索结果"。

主要参考：

- `spec/search-results.md`
- `spec/protocol-behavior.md`
- `spec/runtime-client.md`
- `schemas/partial-failure.schema.json`
- `schemas/return-mode.schema.json`
- `schemas/retrieval-mode.schema.json`
- `schemas/score-kind.schema.json`

这些文档共同说明了结果归一化、`consumable_text`、return mode、redaction-aware 行为、partial failure 表达，以及运行时侧的消费方式。

## 治理语义

MGP 把治理语义直接纳入协议合同，而不是把它留给各后端私自解释。

主要参考：

- `spec/retention.md`
- `spec/conflicts.md`
- `spec/access-control.md`
- `spec/errors.md`
- `schemas/audit-event.schema.json`
- `schemas/lineage-link.schema.json`
- `schemas/memory-evidence.schema.json`

这些资产共同覆盖 retention、conflict handling、access outcome、audit record 和 lineage evidence。

## Lifecycle、Discovery 与 Async

协议包含一个必需的 discovery 面，以及位于核心记忆操作之上的可选 lifecycle / interop 增强层。

当你要描述这些可选协议面的支持范围时，建议统一使用 [Conformance Profile](conformance-profiles.md) 中定义的 profile 名称。

主要参考：

- `spec/lifecycle.md`
- `spec/async-operations.md`
- `spec/http-binding.md`
- `schemas/capabilities.response.schema.json`
- `schemas/initialize.request.schema.json`
- `schemas/initialize.response.schema.json`
- `schemas/async-task.schema.json`
- `schemas/get-task.request.schema.json`
- `schemas/get-task.response.schema.json`
- `schemas/cancel-task.request.schema.json`
- `schemas/cancel-task.response.schema.json`
- `schemas/write-batch.request.schema.json`
- `schemas/write-batch.response.schema.json`
- `schemas/export.request.schema.json`
- `schemas/export.response.schema.json`
- `schemas/import.request.schema.json`
- `schemas/import.response.schema.json`
- `schemas/sync.request.schema.json`
- `schemas/sync.response.schema.json`

这一层覆盖：

- capability discovery
- initialize negotiation
- batch write 这类 interop 扩展
- async export、import、sync task handle
- task polling 与 cancellation

理解规则：

- `GET /mgp/capabilities` 用来描述实现和当前 adapter 的通用 discovery surface
- `POST /mgp/initialize` 用来描述某次交互里真正协商出来的可用面

## Runtime Contract

MGP 明确规定了运行时侧应该如何接入协议，这样不同后端下的 client 行为才不会失去一致性。

主要参考：

- `spec/runtime-client.md`
- `spec/runtime-write-candidate.md`
- `schemas/runtime-capabilities.schema.json`
- `schemas/negotiated-capabilities.schema.json`

这一层覆盖 policy context 映射、candidate extraction、return mode handling，以及 initialize 阶段的 runtime capability declaration。

## Extension、Compatibility 与 Versioning

协议演进与核心操作面是分开定义的。

主要参考：

- `spec/extensions.md`
- `spec/versioning.md`

这一层解决的是如何在不破坏兼容性的前提下扩展协议。

描述实现范围时，建议把 [Conformance Profile](conformance-profiles.md) 与 `spec/versioning.md` 一起使用：版本号说明“变更到了哪一版”，profile 名称说明“实际支持了哪些可选协议面”。

当前约束原则：

- `mgp` namespace 保留给协议级 extension 使用
- vendor namespace 应写入 adapter manifest，并在仓库文档中说明
- 兼容性声明必须由 schema、gateway 行为和 compliance 结果共同支撑

## 实现时的阅读顺序

推荐按下面的顺序理解某个协议特性：

1. 先读对应的 `spec/` 文档，理解行为语义。
2. 再看 `schemas/`，确认精确的 request 或 response shape。
3. 再核对 `openapi/mgp-openapi.yaml`，确认 HTTP surface。
4. 最后查看 reference gateway 和 compliance suite，验证这个合同在代码里是如何被执行与测试的。
