# 贡献指南

本页说明如何在本地开发、验证和提交对 MGP 的改动。

仓库级的权威贡献流程、single source of truth 约定，以及大范围重构前后的回归基线，都以仓库根目录的 `CONTRIBUTING.md` 为准；本页只保留文档站内的摘要说明。

## 本地环境

在仓库根目录执行：

```bash
make install
```

该命令会创建 `.venv/`，并安装参考实现、compliance suite、文档依赖以及可编辑安装的 Python SDK。

## 常用命令

```bash
make lint
make test
make test-all
make test-sdk
make test-integrations
make security
make docs-build
make docs
make serve
```

说明：

- `make test` 使用当前的 `MGP_ADAPTER`，默认值是 `memory`
- `make test-all` 会对 `memory`、`file`、`graph` 跑完整 compliance
- `make test-sdk` 会运行 Python SDK 测试
- `make test-integrations` 会运行 Nanobot、LangGraph 和 minimal runtime 集成测试
- `make serve` 会从 `reference/` 启动参考网关
- `make security` 会对本地开发和 CI 使用的锁定依赖做安全审计

## Source Of Truth 提醒

- `spec/`、`schemas/`、`openapi/` 是协议合同面，除非明确在演进协议，否则不要把普通清理混进这些目录
- 根目录 `README.md` / `README.zh.md` 应保持为仓库入口页，详细说明应放在 `docs/`
- 快速上手以 `docs/zh/getting-started.md` 为准，参考网关安装与 CLI 以 `reference/README.md` 为准
- 示例启动命令与预期结果以 `docs/zh/examples-overview.md` 为准

## 提交前的最低验证

如果你修改了实现、schema 或协议文档，至少应完成：

```bash
make lint
make test-all
make test-sdk
make test-integrations
make docs-build
```

如果你只修改文档，至少运行：

```bash
make docs-build
```

## 新增 Adapter 时的要求

一个新的 adapter 至少应包含：

- `adapter.py`
- `manifest.json`
- `README.md`
- 明确的 capability 声明
- 明确的映射规则
- 明确的限制说明

在提交前，应针对该 adapter 跑通 compliance，并在 PR 中说明验证结果。

## 问题与讨论

如果协议方向不明确，请先开启讨论，然后再实现大范围改动。
