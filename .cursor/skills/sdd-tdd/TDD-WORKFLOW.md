# TDD 工作流详解

> **实施规范**：本文件中所有代码规范要求，均以 [coding-standards SKILL.md](../coding-standards/SKILL.md) 为准。

## TDD 核心原则

1. **红（Red）**：先写一个会失败的测试
2. **绿（Green）**：写最简实现让测试通过
3. **重构（Refactor）**：消除坏味道，保持测试通过

> 永远不要在没有测试的情况下写实现。
> 永远不要在测试失败时写新实现。

---

## 测试分层策略

### 单元测试（tests/unit/）

测试最小可测试单元：函数、类、节点（LangGraph）。

```python
# tests/unit/test_process_node.py
import pytest
from unittest.mock import AsyncMock, patch


class TestProcessNode:
    """process_node 节点单元测试"""

    @pytest.fixture
    def mock_state(self):
        """构造最小化测试状态"""
        from app.state import AgentState

        return AgentState(query="查询示例", keywords=[], user_id="test_user")

    @pytest.mark.asyncio
    async def test_process_node_success(self, mock_state):
        """AC-1.1：正常处理"""
        from app.nodes.process_node import process_node

        with patch("app.nodes.process_node.vector_repository") as mock_repo:
            mock_repo.search.return_value = [
                {"id": "item_001", "score": 0.95, "payload": {"name": "示例"}}
            ]
            result = await process_node(mock_state)

        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "示例"
```

### 集成测试（tests/integration/）

测试模块间交互：节点与节点、节点与工具。

```python
# tests/integration/test_routing.py
class TestRoutingIntegration:
    """两维度正交路由集成测试"""

    @pytest.mark.asyncio
    async def test_column_route_after_process(self):
        """验证 process 完成后正确路由到下一节点"""
        ...
```

### E2E 测试（tests/e2e/）

测试完整流程：入口 → 出口。

```python
# tests/e2e/test_query_flow.py
class TestQueryFlow:
    """查询全流程 E2E"""

    @pytest.mark.asyncio
    async def test_first_query_end_to_end(self):
        """端到端：用户首次提问 → 返回结果"""
        ...
```

### Smoke Test（tests/smoke/）

快速冒烟：核心路径覆盖，不追求边界。

```bash
# 运行所有冒烟测试
cd backend && uv run pytest tests/smoke -x -q
```

### Playwright Smoke（tests/smoke_playwright/）

浏览器级冒烟：真实 UI 交互验证。

---

## Mock 策略

### LLM 调用

```python
@pytest.fixture
def mock_llm():
    from unittest.mock import AsyncMock
    llm = AsyncMock()
    llm.ainvoke.return_value = AIMessage(content="SELECT ...")
    return llm
```

### 外部服务（Redis/MySQL/VectorStore）

```python
@pytest.fixture
def mock_redis(monkeypatch):
    client = AsyncMock()
    monkeypatch.setattr("app.services.redis_client", client)
    return client
```

### VCR.py 录制

```python
# 首次运行录制
# cd backend && RECURSE=1 uv run pytest tests/integration/test_xxx.py --record-mode=new_episodes

# CI 使用录制
# cd backend && uv run pytest tests/integration/test_xxx.py --record-mode=none
```

---

## 覆盖率监控

```bash
# 生成覆盖率报告
cd backend && uv run pytest tests/unit --cov=app --cov-report=term-missing --cov-report=html

# 检查门槛
# rules/  >= 90%
# agents/  >= 80%
# tools/   >= 70%
# 整体     >= 60%
```

---

## 红-绿-重构循环示例

### 场景：实现 process_node 节点

**Step 1 — RED（写测试）**

```python
# tests/unit/test_process_node.py
from app.state import AgentState

class TestProcessNode:
    @pytest.mark.asyncio
    async def test_returns_results(self):
        state = AgentState(query="查询示例", keywords=[], user_id="test_user")
        runtime = MockRuntime()
        result = await process_node(state, runtime)
        assert "results" in result
```

运行：`uv run pytest tests/unit/test_process_node.py -x`
结果：**FAIL** — `process_node` 不存在

**Step 2 — GREEN（写最简实现）**

```python
# app/nodes/process_node.py
async def process_node(state: AgentState, runtime: Runtime[AgentContext]) -> dict:
    """处理查询（待补充完整实现）。"""
    return {"results": [], "error": None}
```

运行：`uv run pytest tests/unit/test_process_node.py -x`
结果：**PASS**

**Step 3 — 逐步完善 + 继续 RED**

添加下一个测试：

```python
async def test_searches_repository(self):
    state = AgentState(query="查询示例", keywords=["关键词"], user_id="test_user")
    runtime = MockRuntime()
    with patch("app.nodes.process_node.vector_repository") as mock:
        mock.search.return_value = [...]
        result = await process_node(state, runtime)
    assert len(result["results"]) > 0
```

运行：**FAIL** → 补充实现 → **PASS** → ...

**Step 4 — REFACTOR**

所有测试通过后，通过 [coding-standards L0-L6 质量门禁](../coding-standards/SKILL.md) 消除坏味道。参考规范：
- 单函数 ≤ **50 行**，单节点 ≤ 150 行（`radon -l`，口径见 coding-standards SKILL.md）
- 圈复杂度单函数 max A（`radon -a -i A`）
- 添加 docstring 和 loguru 日志，禁止 print

---

## 常见反模式

| 反模式 | 正确做法 |
|--------|----------|
| 先写实现后补测试 | 始终 RED → GREEN |
| 测试依赖实现细节 | 测试行为，不测实现 |
| 用 print 调试 | 用 loguru 日志 |
| 全局 mock 污染 | 每个测试 fixture 独立 |
| 不测异常路径 | 必须覆盖 2xx/4xx/5xx |
| State 用 dict | 用 TypedDict 注解字段 |
| 节点内直接修改 state | 节点返回状态增量 dict |
| agents/ 内写业务逻辑 | 业务写到 rules/ |
