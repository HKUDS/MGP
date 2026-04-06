# 示例总览

本页指向仓库内可直接运行的 Python 示例，这些示例会直接打到参考网关，并覆盖 MGP 的主要协议面。

## 前置条件

- 已通过 `make install` 安装 Python 依赖
- 参考网关已启动（推荐用 `make serve`）
- 对于 `04_switch_backend.py`，需要有两个不同 URL 的网关实例

## 推荐的网关启动方式

### In-Memory Adapter

```bash
make serve
```

等价的显式启动命令：

```bash
./.venv/bin/mgp-gateway --host 127.0.0.1 --port 8080
```

### 第二个端口上的 File Adapter

```bash
cd reference
MGP_ADAPTER=file ../.venv/bin/python -m uvicorn gateway.app:app --host 127.0.0.1 --port 8081
```

## 运行示例

### 1. 写入 profile

```bash
./.venv/bin/python examples/01_write_profile.py
```

预期结果：

- 写入一条 `profile` memory
- 再把它读回来
- 返回结构化的 canonical memory object

### 2. 搜索 episodic event

```bash
./.venv/bin/python examples/02_search_episodic.py
```

预期结果：

- 写入一条 `episodic_event`
- 至少返回一条搜索结果
- 每条结果都包含 `consumable_text`、`retrieval_mode` 和 `score_kind`

### 3. TTL 过期

```bash
./.venv/bin/python examples/03_ttl_expiry.py
```

预期结果：

- 过期前有一条结果
- 过期后为零条结果

### 4. 切换 backend

```bash
MGP_MEMORY_URL=http://127.0.0.1:8080 MGP_FILE_URL=http://127.0.0.1:8081 ./.venv/bin/python examples/04_switch_backend.py
```

预期结果：

- 通过两个不同网关写入等价数据
- 打印两个返回的 memory object
- 证明 backend 切换后协议形状仍然保持稳定

### 5. 端到端演示

```bash
./.venv/bin/python examples/e2e_demo.py
```

预期结果：

- write
- search
- get
- expire
- search again
- audit query
- 结构化搜索结果与更丰富的 audit metadata

### 6. 纯 SDK 路径

```bash
./.venv/bin/python examples/05_sdk_only.py
```

预期结果：

- 通过 SDK 完成 capability discovery
- 只用 `mgp-client` 跑通 write 和 get

### 7. Gateway + PostgreSQL

```bash
MGP_POSTGRES_URL=http://127.0.0.1:8080 ./.venv/bin/python examples/06_gateway_plus_postgres.py
```

预期结果：

- 查看 postgres-backed gateway 的 capability 输出
- 在生产导向 adapter 路径上完成 write 和 search

### 8. Sidecar shadow mode

```bash
./.venv/bin/python examples/07_sidecar_shadow_mode.py
```

预期结果：

- 通过 Nanobot sidecar 跑通 `shadow` mode recall
- 通过 sidecar bridge 完成 governed commit

### 9. Batch、export 与 import

```bash
./.venv/bin/python examples/08_batch_export_import.py
```

预期结果：

- batched write
- 导出归一化 memory
- 再把导出的 payload 导回去

### 10. Task polling

```bash
./.venv/bin/python examples/09_task_polling.py
```

预期结果：

- 异步 export 被接受
- 通过 SDK 轮询 task
- 返回完成后的 task payload

### 11. Audit query

```bash
./.venv/bin/python examples/10_audit_query.py
```

预期结果：

- 通过 SDK 执行 focused audit query
- 得到便于运维查看的 event payload
