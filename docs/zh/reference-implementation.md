# 参考实现

本页介绍当前的 Python 参考网关，它是 MGP 参考行为的可运行实现。

## `reference/` 里有什么

当前参考实现主要由以下模块构成：

- `reference/gateway/`：FastAPI app、routing、request/response 校验、config、middleware、task handling
- `reference/policy/`：最小 policy hook
- `reference/audit/`：JSON Lines 审计 sink

参考网关会按已发布 schema 对 request body 与 response body 做校验。

## 运维使用说明

安装、CLI、adapter 参数和配置项的权威说明统一放在仓库内的 `reference/README.md`。

把它作为以下内容的单一事实来源：

- 仓库路径与包路径安装
- `mgp-gateway` CLI 用法
- 各 adapter 的运行参数
- 容器启动与 smoke test 命令

当前参考网关已经提供官方 middleware 接入点，用于：

- API key 认证
- bearer token 认证
- tenant header 与 `policy_context.tenant_id` 的一致性校验
- request ID 传播与结构化请求日志

这些控制仍然是最小实现，目的是提供真实部署可以接入的形状，而不是替代完整的安全体系。另见 [安全基线](security-baseline.md)。

## 运维端点

除 MGP 协议端点外，参考网关还暴露：

- `GET /healthz`
- `GET /readyz`
- `GET /version`

这些端点属于运维辅助面，不属于 governed-memory 协议合同本身。

## 当前协议端点

完整端点列表、cURL 示例和运维说明请参阅 `reference/README.md`。

## 如何理解它的定位

这个实现的目标不是替代真实生产网关，而是提供一个足够清晰、可运行、可测试的协议行为基线。阅读时建议把它和以下内容一起看：

- `spec/`
- `schemas/`
- `openapi/mgp-openapi.yaml`
- `compliance/`

这样可以同时看到“协议怎么写”“消息怎么校验”“HTTP 怎么绑定”“行为怎么被验证”。
