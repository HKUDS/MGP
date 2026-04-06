# 适配器编写指南

本页给希望实现 MGP-compatible adapter 的作者一个最小模板。

## 目标

MGP adapter 的职责，是把一个具体 backend 映射到统一的 MGP protocol surface。

一个合格的 adapter 应当：

- 实现 `adapters/base.py` 中的 adapter interface
- 发布合法的 `manifest.json`
- 明确声明 capability
- 保持 canonical memory object shape
- 通过 compliance suite

## 推荐文件结构

```text
adapters/your-adapter/
  __init__.py
  adapter.py
  manifest.json
  README.md
```

## 必须实现的接口

你的 adapter 应实现以下方法：

- `write(memory)`
- `search(query, subject, scope, types, limit)`
- `get(memory_id)`
- `update(memory_id, patch)`
- `expire(memory_id, expired_at, reason)`
- `revoke(memory_id, revoked_at, reason)`
- `delete(memory_id, deleted_at, reason)`
- `purge(memory_id, purged_at, reason)`
- `list_memories(...)`
- `get_manifest()`

## Manifest 要求

`manifest.json` 必须通过：

- `schemas/adapter-manifest.schema.json`

它至少应声明：

- adapter name
- backend kind
- supported MGP version
- supported memory type
- supported scope
- capability
- extension namespace

## Capability 声明原则

不要把 capability 写得含糊不清。若某个能力后端不原生支持，就应明确声明为 `false`，即使 gateway 可以在外层模拟它。

主要参考：

- `schemas/backend-capabilities.schema.json`

## Extension 处理原则

- 不要改变核心字段的既有语义
- 厂商私有数据放进 `extensions`
- 使用带命名空间的 key，例如 `vendor:key_name`
- 尽量保留未知 extension，不要无故丢弃

边界说明：

- 可移植的厂商语义放进 `extensions`
- `backend_ref` 只保留给 adapter-local 的 opaque handle 或路由元数据

## README 最低要求

每个 adapter README 至少应说明：

- purpose
- storage model
- mapping rule
- supported capability
- known limitation
- compliance command

## 验证

建议在 `compliance/` 目录下运行适配器验证：

```bash
cd compliance
MGP_ADAPTER=your-adapter ../.venv/bin/python -m pytest
```

能通过套件，是一个 adapter 达到 MGP-compatible baseline 的最低证明。
