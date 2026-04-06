# 运维指南

本页关注的是参考网关的 day-2 运维问题。

## 需要监控什么

- 通过 `/healthz` 监控 gateway 进程健康
- 通过 `/readyz` 监控 adapter readiness
- 通过 `/version` 查看当前运行版本与 adapter 选择
- audit sink 的增长与轮转
- adapter 对应后端的健康，例如 PostgreSQL 可用性

## 日志

参考网关现在会通过 middleware 输出结构化请求日志，并传播 request ID。

建议保留这些字段：

- request ID
- method
- path
- status code
- environment

这样更容易把 runtime 错误、gateway 行为和 audit record 串起来。

## Audit Sink

默认行为：

- audit event 会追加到 JSON Lines 文件
- 路径可通过 `MGP_AUDIT_LOG` 配置

运维建议：

- 在日志无限增长之前做好轮转或采集
- 防止 audit 文件被跨租户访问
- audit retention 应按部署策略管理，而不只是跟着 memory retention 走

## Adapter 运维

### File

- 确保存储目录存在且可写
- 如果把它用于真实环境，应和 audit log 一起纳入备份

### Graph

- 把 SQLite 文件视为有状态基础设施
- 如果超出本地测试用途，就应纳入备份

### PostgreSQL

- 监控连接、磁盘增长和索引健康
- 按正常 PostgreSQL 流程完成备份
- 对 schema migration 保持变更可追踪

## Lifecycle 与删除

当运维处理 delete 或 purge 相关问题时，建议确认：

- gateway 调用是否成功
- adapter 是否持久化了预期状态转换
- 下游副本或导出物是否也需要清理
- audit record 是否记录了这次操作和关联 request

## 事件响应清单

1. 先确认受影响的 adapter 和 tenant scope。
2. 找到对应的 request 或 audit correlation identifier。
3. 查看该请求附近的 gateway 日志。
4. 查看 adapter 本地状态或 backend 状态。
5. 如果修复触及协议行为，再补跑 focused compliance 或 smoke test 后恢复服务。
