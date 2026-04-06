# 安全基线

本页记录了部署或接入 MGP 时应满足的最低安全预期。

MGP 定义的是治理合同，而不是一个完整的安全产品。认证、传输保护、密钥管理和基础设施隔离仍然属于部署系统本身的职责。本页的作用，是明确真实部署时至少应该补上的安全控制。

## 范围

MGP 本身会标准化：

- policy context 传递
- delete、purge、revoke、expire 这类 lifecycle intent
- audit 与 lineage 结构
- capability declaration 与 negotiation

MGP 不会标准化：

- 唯一必选的认证协议
- 唯一必选的身份提供者
- 唯一必选的 policy engine 实现
- 唯一必选的存储安全模型

这个边界是刻意设计的，但并不意味着可以忽略部署层的安全控制。

## 传输安全

部署时应当：

- 所有远程 MGP 流量都走 TLS
- 不要在跨信任边界场景下使用明文传输
- 在生产环境中固定内部证书或使用受管信任根
- 明确说明 sidecar、runtime 与 gateway 之间是走 loopback、私有网络还是公网入口

如果没有 TLS，就应当把它视为仅限本地开发场景。

## 认证与身份

MGP 请求总会携带 `policy_context`，但 `policy_context` 本身不是认证机制。

部署时应当：

- 在信任请求内容之前先认证调用方
- 把已认证身份与 `policy_context.actor_agent`、tenant 字段建立绑定
- 当传输层身份与声明的 policy context 不一致时，根据部署规则拒绝请求
- 明确记录 gateway 信任的是上游 identity header、API key、JWT、mTLS 还是其他机制

推荐理解方式：

- 传输层身份证明“谁在调用”
- `policy_context` 说明“runtime 声称代表谁操作”
- policy evaluation 决定“这次操作是否允许”

## Tenant 隔离

多租户部署应当：

- 要求稳定的 tenant identifier
- 按 tenant 对 adapter 存储与 audit 记录做隔离
- 除非显式建模并可审计，否则跨租户读取必须不可能发生
- 对缺失或含糊的 tenant 标识采取拒绝策略，而不是默认放行

即使某个 adapter 支持多 subject 或多 scope，部署层也应显式绑定 tenant，而不是依赖自由元数据去猜测。

## 审计保留与完整性

Audit 数据本身就是 governed-memory 的一部分，也应得到相应保护。

部署时应当：

- 把 audit event 写入适合追加写的存储
- 将 audit retention 与 memory retention 分开定义
- 防止 audit sink 被静默篡改或跨租户读取
- 记录足够的 correlation 标识，以便串起 runtime 请求、adapter 行为与 backend 错误

如果需要做 audit redaction，也应使用明确、可审查的规则，而不是静默丢弃记录。

## Delete、Purge 与责任边界

`delete`、`purge` 这类 lifecycle 请求会带来明确的责任要求。

部署时应当：

- 清楚记录哪些字段是 soft delete，哪些是 hard delete
- 在 audit trail 中记录 purge 结果
- 定义如何清理下游缓存、导出副本或复制链路
- 明确 gateway、adapter、external provider 谁才是最终删除责任方

不要在没有真实保证的情况下暗示“协议层 purge 成功就等于所有外部系统都已删除”。

## 密钥管理

部署时应当：

- 不把 provider credential 提交到仓库
- 通过环境注入或 secret store 管理凭证
- 尽可能按项目、tenant 或环境隔离 provider credential
- 允许在不修改协议的前提下完成密钥轮换

参考集成应使用占位符、`.env.example` 或仓库外配置路径，而不是提交真实凭证。

## 外部 Provider 信任边界

Service-backed adapter 会引入第二层信任边界。

在使用外部 provider adapter 之前，应明确记录：

- 哪些数据字段会离开你的环境
- provider 如何处理 retention 与 deletion
- provider 侧的 graph extraction、indexing 或 deduplication 是否会改变原始内容
- 哪些失败模式会造成 partial result 或 delayed consistency

对于会把内容发送到 provider 侧模型或索引流水线的 adapter，这一点尤为重要。

## 运维控制

生产部署还应定义：

- rate limit 与 abuse control
- request timeout 与 retry 规则
- structured logging 与 request identifier
- 有状态 adapter 的备份与恢复流程
- policy 或 deletion 失败时的 incident response

## 实际部署规则

把 MGP 看成更大系统中的一层：

- 传输与身份控制负责保护边界
- policy context 与 audit 负责保留治理意图
- adapter 与 backend 负责落实存储行为
- 部署文档负责解释这些层之间的责任边界与剩余风险
