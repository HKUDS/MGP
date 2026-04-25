# 快速入门

本指南带你完成 MGP 的环境搭建、启动参考网关、并跑通第一组 governed memory 操作——大约五分钟即可完成。

**你将学到：**

- 安装 MGP 参考网关和 Python SDK
- 使用 in-memory 适配器启动本地网关
- 执行记忆对象的写入、搜索、更新、过期和审计操作
- 理解核心概念：记忆对象、策略上下文、适配器、生命周期

## 前置条件

- Python 3.11+
- Git

## 1. 克隆与安装

```bash
git clone https://github.com/hkuds/MGP.git
cd MGP
make install
```

这会在 `.venv/` 下创建虚拟环境，并安装参考网关、合规测试套件、文档工具和 Python SDK。

如果你只想安装打包后的参考网关 CLI，而不需要整套仓库工具链：

```bash
python3 -m pip install .
```

## 2. 启动参考网关

```bash
make serve
```

网关默认在 `http://127.0.0.1:8080` 启动，使用 in-memory 适配器。确认运行状态：

```bash
curl http://127.0.0.1:8080/mgp/capabilities
```

你会收到一个 JSON 响应，包含后端能力声明（`backend_kind`、支持的操作、特性开关等）。这说明网关已就绪。

其他运行路径：

```bash
mgp-gateway --host 127.0.0.1 --port 8080
docker compose up --build
```

运维辅助端点：

- `GET /healthz`
- `GET /readyz`
- `GET /version`

## 3. 写入第一条记忆

每个 MGP 请求都需要一个 **policy context**，它描述了谁在操作、代表谁操作、以及操作目的。协议通过它承载 actor、subject、tenant 和请求意图这类治理输入，但 MGP 本身并不规定内部 policy engine 如何实现。

策略上下文最小必填字段：

- `actor_agent` — 执行操作的 agent 或服务
- `acting_for_subject` — 操作代表谁
- `requested_action` — 请求执行什么操作

### 使用 cURL

```bash
curl -X POST http://127.0.0.1:8080/mgp/write \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_001",
    "policy_context": {
      "actor_agent": "my-agent/v1",
      "acting_for_subject": {"kind": "user", "id": "user_alice"},
      "requested_action": "write",
      "tenant_id": "my_tenant"
    },
    "payload": {
      "memory": {
        "memory_id": "mem_001",
        "subject": {"kind": "user", "id": "user_alice"},
        "scope": "user",
        "type": "preference",
        "content": {
          "statement": "User prefers dark mode.",
          "preference_key": "theme",
          "preference_value": "dark"
        },
        "source": {"kind": "human", "ref": "chat:1"},
        "sensitivity": "internal",
        "created_at": "2026-01-01T00:00:00Z",
        "backend_ref": {"tenant_id": "my_tenant"},
        "extensions": {}
      }
    }
  }'
```

预期响应：

```json
{"status": "ok", "request_id": "req_001", ...}
```

### 使用 Python SDK

```python
from mgp_client import MGPClient, PolicyContextBuilder

context = PolicyContextBuilder(
    actor_agent="my-agent/v1",
    subject_id="user_alice",
    tenant_id="my_tenant",
)

with MGPClient("http://127.0.0.1:8080") as client:
    response = client.write_memory(
        context.build("write"),
        {
            "memory_id": "mem_001",
            "subject": {"kind": "user", "id": "user_alice"},
            "scope": "user",
            "type": "preference",
            "content": {
                "statement": "User prefers dark mode.",
                "preference_key": "theme",
                "preference_value": "dark",
            },
            "source": {"kind": "human", "ref": "chat:1"},
            "sensitivity": "internal",
            "created_at": "2026-01-01T00:00:00Z",
            "backend_ref": {"tenant_id": "my_tenant"},
            "extensions": {},
        },
    )
    print(response.status)  # "ok"
```

## 4. 搜索记忆

现在来回忆刚写入的内容。MGP 搜索返回结构化结果，包含 `consumable_text`，运行时可以安全地注入到 prompt 中。

### 使用 cURL

```bash
curl -X POST http://127.0.0.1:8080/mgp/search \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_002",
    "policy_context": {
      "actor_agent": "my-agent/v1",
      "acting_for_subject": {"kind": "user", "id": "user_alice"},
      "requested_action": "search",
      "tenant_id": "my_tenant"
    },
    "payload": {
      "query": "dark mode",
      "limit": 10
    }
  }'
```

响应包含 `results` 数组。每个结果项包括匹配的记忆对象、可安全注入 prompt 的 `consumable_text` 字符串，以及 `return_mode` 指示符。

### 使用 Python SDK

```python
from mgp_client import MGPClient, PolicyContextBuilder, SearchQuery

search_context = PolicyContextBuilder(
    actor_agent="my-agent/v1",
    subject_id="user_alice",
    tenant_id="my_tenant",
).build("search")

with MGPClient("http://127.0.0.1:8080") as client:
    result = client.search_memory(
        search_context,
        SearchQuery(query="dark mode", limit=10),
    )
    for item in result.data.get("results", []):
        print(item["consumable_text"])
```

## 5. 完整生命周期演示

下面的流程演示了 governed memory 的完整生命周期：write → search → get → update → expire → audit。

```python
from mgp_client import MGPClient, PolicyContextBuilder, SearchQuery, AuditQuery

context = PolicyContextBuilder(
    actor_agent="my-agent/v1",
    subject_id="user_alice",
    tenant_id="my_tenant",
)

with MGPClient("http://127.0.0.1:8080") as client:
    # 写入一条偏好
    client.write_memory(
        context.build("write"),
        {
            "memory_id": "mem_lifecycle",
            "subject": {"kind": "user", "id": "user_alice"},
            "scope": "user",
            "type": "preference",
            "content": {
                "statement": "User prefers Python.",
                "preference": "Python",
                "preference_key": "language",
                "preference_value": "python",
            },
            "source": {"kind": "human", "ref": "chat:2"},
            "created_at": "2026-01-01T00:00:00Z",
            "backend_ref": {"tenant_id": "my_tenant"},
            "extensions": {},
        },
    )

    # 搜索 — 应该能找到这条偏好
    results = client.search_memory(
        context.build("search"),
        SearchQuery(query="python", limit=5),
    )
    print(f"搜索到 {len(results.data.get('results', []))} 条结果")

    # 按 ID 获取
    mem = client.get_memory(context.build("read"), "mem_lifecycle")
    print(f"获取到记忆: {mem.data['memory']['type']}")

    # 更新内容
    client.update_memory(
        context.build("update"),
        "mem_lifecycle",
        {
            "content": {
                "statement": "User prefers Rust.",
                "preference": "Rust",
                "preference_key": "language",
                "preference_value": "rust",
            }
        },
    )

    # 过期该记忆
    client.expire_memory(
        context.build("expire"),
        "mem_lifecycle",
        reason="user_changed_mind",
    )

    # 再次搜索 — 过期的记忆不应出现
    after = client.search_memory(
        context.build("search"),
        SearchQuery(query="python", limit=5),
    )
    print(f"过期后: {len(after.data.get('results', []))} 条结果")

    # 审计追踪 — 查看这条记忆发生了什么
    audit = client.query_audit(
        context.build("read"),
        AuditQuery(target_memory_id="mem_lifecycle", limit=20),
    )
    for event in audit.data.get("events", []):
        print(f"  {event['action']} at {event.get('timestamp', 'N/A')}")
```

预期控制台输出：

```
搜索到 1 条结果
获取到记忆: preference
过期后: 0 条结果
  write at 2026-01-01T00:00:00Z
  update at ...
  expire at ...
```

也可以直接运行仓库自带的端到端演示：

```bash
make serve  # 在一个终端
./.venv/bin/python examples/e2e_demo.py  # 在另一个终端
```

## 核心概念

### Memory Object（记忆对象）

governed memory 的基本单位。每个 memory object 都有 `subject`（关于谁）、`scope`（适用范围）、`type`（记忆类别）和结构化 `content`。

### Policy Context（策略上下文）

每个请求都携带 policy context，告诉网关谁在操作、代表谁、以及受什么治理约束。它为审计、访问控制和策略结果提供统一的协议合同，但具体的策略引擎仍由实现方决定。

### Adapter（适配器）

适配器把具体的存储后端桥接到 MGP 协议面。仓库内置了 in-memory、file、graph（SQLite）、PostgreSQL、OceanBase、LanceDB、Mem0 和 Zep 适配器。你可以按照 [适配器编写指南](adapter-guide.md) 编写自己的适配器。

### Capability（能力声明）

每个适配器通过 `manifest.json` 声明它能做什么、不能做什么。运行时利用能力声明来理解后端行为，无需反复试错。

### Lifecycle（生命周期）

MGP 中的记忆不只是 CRUD。对象可以被 expire（过期）、revoke（撤销）、delete（删除）或 purge（清除）——每种操作都有不同的治理语义，审计追踪会记录每一次状态变迁。

## 关于参考适配器

本指南使用的 in-memory 适配器（以及 file 和 graph 适配器）是**参考实现**，用于协议验证和学习，不建议直接用于生产环境。生产部署时，请针对实际存储后端构建或选用适配器——参见 [适配器编写指南](adapter-guide.md)。

## 下一步

| 目标 | 资源 |
| --- | --- |
| 深入理解协议 | [协议参考](protocol-reference.md) |
| 查看所有 JSON Schema | [Schema 参考](schema-reference.md) |
| 编写自定义适配器 | [适配器编写指南](adapter-guide.md) |
| 了解现有适配器 | [适配器总览](adapters-overview.md) |
| 使用 Python SDK | [Python SDK](python-sdk.md) |
| 运行合规测试 | [合规测试](compliance-suite.md) |
| 通过 Sidecar 接入 | [Sidecar 接入](sidecar-integration.md) |
| 理解 MGP 与 MCP 的关系 | [MGP 与 MCP](mgp-vs-mcp.md) |
| 尝试不同后端 | `make serve` 配合 `MGP_ADAPTER=file` 或 `MGP_ADAPTER=graph` |
