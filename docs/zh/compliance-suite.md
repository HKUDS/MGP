# 合规测试

本页介绍 MGP 的可运行验证层。MGP 的兼容性声明必须落到测试，而不是停留在文档口号上。

## Compliance Suite 验证什么

`compliance/` 目录中的 pytest 套件会验证：

- JSON schema conformance
- OpenAPI 与 schema 的共享字段对齐
- OpenAPI、README 版本标记与 reference gateway 路由之间的 contract drift
- core operation behavior
- lifecycle 与 retention behavior
- conflict behavior
- access decision behavior
- adapter compatibility 与 round-trip consistency
- search result consumption contract
- dedupe、upsert、merge 语义
- delete 与 purge 语义
- audit correlation fields
- interop 相关 endpoint 行为

## 测试分组

核心 compliance 分组：

- `schema/test_schema_validation.py`
- `core/test_core_operations.py`
- `search/test_search_results.py`
- `lifecycle/test_lifecycle.py`
- `lifecycle/test_delete_purge.py`
- `conflicts/test_conflicts.py`
- `access/test_access_control.py`
- `audit/test_audit_contract.py`
- `dedupe/test_dedupe_upsert.py`
- `adapters/test_adapter_compat.py`

参考套件中默认包含的可选协议特性分组：

- `interop/test_bulk_sync_export.py`
- `lifecycle/test_protocol_lifecycle.py`

这些分组在协议生态层面是可选特性，但仓库里的参考网关与默认 pytest 命令会在适用时一并覆盖它们。

## Conformance Profile

描述兼容性时，建议统一使用 [Conformance Profile](conformance-profiles.md) 中定义的 profile：

- `Core`
- `Lifecycle`
- `Interop`
- `ExternalService`

当前仓库中的解释方式：

- 仓库内 `memory`、`file`、`graph` 的验证矩阵共同证明 `Core`、`Lifecycle`、`Interop`
- 配好 `MGP_POSTGRES_DSN` 后，`postgres` 也可以在本地覆盖同一组 profile
- 配好 `MGP_OCEANBASE_DSN`（或 `MGP_OCEANBASE_*` 一组离散变量）后，`oceanbase` 也可以在本地覆盖同一组 profile，也支持 `oceanbase/seekdb`
- `ExternalService` 适用于 `Mem0`、`Zep` 这类 service-backed adapter，它们需要真实 provider 环境才能完成端到端验证

能力解释说明：

- gateway 暴露的 HTTP surface 可能比某个 backend 的 native capability 更宽
- 即使 gateway 能模拟部分行为，adapter manifest 仍应如实声明 backend-native capability

## 当前验证矩阵

CI 会对以下适配器执行完整 compliance：

- `memory`
- `file`
- `graph`

如果配置了 `MGP_POSTGRES_DSN`，`postgres` 也可以在本地跑同一套 suite：

```bash
cd compliance
MGP_ADAPTER=postgres MGP_POSTGRES_DSN=postgresql://postgres:postgres@127.0.0.1:5432/mgp ../.venv/bin/python -m pytest
```

如果配置了 `MGP_OCEANBASE_DSN`，`oceanbase` 也可以在本地跑同一套 suite：

```bash
cd compliance
MGP_ADAPTER=oceanbase MGP_OCEANBASE_DSN='mysql://root:oblab@127.0.0.1:2881/test?tenant=sys' ../.venv/bin/python -m pytest
```

`make lint` 会作为 pytest 之外的补充校验，执行 schema 校验、OpenAPI 校验以及 contract-drift 检查。

从仓库根目录执行时：

- `make test` 会对当前 `MGP_ADAPTER` 运行 `python -m pytest compliance`
- `make test-all` 会把这套完整 suite 依次跑在 `memory`、`file`、`graph` 上

## 阅读建议

如果你想判断"某个功能是否真的已经完成"，建议同时查看：

- `compliance/README.md`
- `compliance/**/test_*.py`
- `reference/gateway/app.py`

这三处合起来，能够说明某个协议面是否已有实际行为与测试支撑。
