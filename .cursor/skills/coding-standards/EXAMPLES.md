# 代码示例与反模式

本文档是 `SKILL.md` 的子文件。示例已全部去业务化，使用通用变量名和路径。

---

## 正确示例

### 节点（Node）

```python
# app/nodes/process_node.py
from dataclasses import asdict, is_dataclass
from pydantic import ValidationError
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.contracts.common import NodeInput, NodeOutput
from app.context import AgentContext
from app.llm import llm
from app.state import AgentState
from app.contracts.example import ToolInput, ToolOutput
from app.entities.item_info import ItemInfo
from app.prompt.prompt_loader import load_prompt
from app.core.log import logger


def _entity_to_dict(obj):
    """Convert dataclass / Pydantic model / TypedDict to plain dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if is_dataclass(obj):
        return asdict(obj)
    return dict(obj)


async def process_node(state: AgentState, runtime: Runtime[AgentContext]) -> dict:
    writer = runtime.stream_writer
    writer({"type": "thinking", "content": "正在检索信息..."})
    writer({"type": "progress", "step": "召回", "status": "running"})

    query = state.get("resolved_query") or state["query"]
    keywords = state["keywords"]

    # --- 入口校验 ---
    try:
        ToolInput.model_validate({"keywords": keywords, "query": query})
    except ValidationError as e:
        logger.warning(f"process_node input validation failed: {e}")
        return {"error": str(e), "results": []}

    prompt = PromptTemplate(
        template=load_prompt("extend_keywords"),
        input_variables=["query"],
    )
    output_parser = JsonOutputParser()
    chain = prompt | llm | output_parser

    try:
        result = await chain.ainvoke({"query": query})
    except asyncio.CancelledError:
        raise
    except Exception:
        writer({"type": "thinking", "content": "关键词扩展失败，使用原始关键词"})
        result = []

    keywords = list(set(keywords + result))

    # ... 检索逻辑 ...

    # --- 出口校验 ---
    try:
        output = ToolOutput.model_validate({
            "results": [_entity_to_dict(item) for item in retrieved_items],
        })
        return output.model_dump()
    except ValidationError as e:
        logger.warning(f"process_node output validation failed: {e}")
        return {"error": str(e), "results": []}
```

### 节点契约（Contract）

```python
# app/contracts/example.py
"""example contract."""
from app.contracts.common import NodeInput, NodeOutput


class ToolInput(NodeInput):
    query: str
    options: list[str] = []
    is_followup: bool = False
    previous_result: list[dict] | None = None


class ToolOutput(NodeOutput):
    results: list[dict] = []
    error: str | None = None


__all__ = ["ToolInput", "ToolOutput"]
```

### Base Class

```python
# app/contracts/common.py
"""Node contract base classes."""
from pydantic import BaseModel, ConfigDict


class NodeInput(BaseModel):
    """Base class for all node input contracts. Extra fields are forbidden."""
    model_config = ConfigDict(extra="forbid")


class NodeOutput(BaseModel):
    """Base class for all node output contracts. Extra fields are forbidden."""
    model_config = ConfigDict(extra="forbid")
```

### Entity（dataclass）

```python
# app/entities/item_info.py
from dataclasses import dataclass
from typing import Any


@dataclass
class ItemInfo:
    id: str
    name: str
    type: str
    role: str
    examples: list[Any]
    description: str
    alias: list[str]
    source_id: str
```

### Agent Context（TypedDict）

```python
# app/context.py
from typing import Callable, TypedDict
from langchain_core.embeddings import Embeddings
from sqlalchemy.ext.asyncio import AsyncSession


class AgentContext(TypedDict):
    vector_repository: "VectorRepository"
    embedding_client: Embeddings
    mysql_session_factory: Callable[[], AsyncSession] | None
    run_id: str
    session_id: str
    user_id: str
```

### 配置（dataclass）

```python
# app/conf/app_config.py
@dataclass
class LLMConfig:
    model_name: str = "{{LLM_MODEL}}"
    api_key: str = ""
    base_url: str = ""
    timeout: int = 30


@dataclass
class AppConfig:
    llm: LLMConfig
    redis: RedisConfig
    db: DBConfig
```

### Router with YAML

```python
# app/agent/routers/semantic_router.py
from pathlib import Path
from typing import Final
import yaml

ROUTE_A: Final[str] = "route_a"
ROUTE_B: Final[str] = "route_b"


def _load_routing_rules() -> dict:
    config_path = Path(__file__).parents[3] / "conf" / "routing_rules.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
```

---

## TDD 循环示例

### Step 1 — RED（先写测试）

```python
# tests/unit/test_process_node.py
"""TDD RED phase — tests written BEFORE implementation."""
from __future__ import annotations
from unittest.mock import AsyncMock, patch, MagicMock

import pytest


@pytest.fixture
def mock_state():
    from app.state import AgentState
    return AgentState(
        query="查询示例",
        keywords=["关键词A", "关键词B"],
        resolved_query="查询示例",
    )


@pytest.mark.asyncio
async def test_process_node_returns_results(mock_state):
    """AC-1.1: 正常返回结果"""
    from app.nodes.process_node import process_node

    with patch("app.nodes.process_node.llm") as mock_llm:
        mock_llm.ainvoke.return_value = AsyncMock(content='["关键词A", "关键词B"]')

        with patch("app.nodes.process_node.vector_repository") as mock_repo:
            mock_item = MagicMock()
            mock_item.id = "item_001"
            mock_item.name = "示例"
            mock_repo.search.return_value = [mock_item]

            result = await process_node(mock_state, MagicMock())

    assert "results" in result
    assert len(result["results"]) > 0


@pytest.mark.asyncio
async def test_process_node_handles_empty_keywords(mock_state):
    """AC-1.2: 空关键词返回空列表"""
    mock_state["keywords"] = []
    from app.nodes.process_node import process_node

    result = await process_node(mock_state, MagicMock())
    assert result["results"] == []
```

### Step 2 — GREEN（最简实现）

```python
# app/nodes/process_node.py
async def process_node(state: AgentState, runtime: Runtime[AgentContext]) -> dict:
    return {"results": []}  # 最简实现
```

### Step 3 — 逐步完善

添加更多测试 → 补充实现 → 所有测试 PASS → REFACTOR。

---

## 测试 Fixture 示例

```python
# tests/conftest.py
from __future__ import annotations
import pytest
from fakeredis import FakeAsyncRedis
from app.clients.redis_client_manager import redis_client_manager, CircuitBreaker, CircuitState


@pytest.fixture(autouse=True)
async def setup_fake_redis():
    """自动注入 FakeAsyncRedis，确保跨测试隔离。"""
    redis_client_manager.client = FakeAsyncRedis(decode_responses=True)
    redis_client_manager.circuit_breaker = CircuitBreaker()
    redis_client_manager.circuit_breaker.state = CircuitState.CLOSED
    yield
    # cleanup
    redis_client_manager.client = None
    redis_client_manager.circuit_breaker = CircuitBreaker()


# pytest.ini 标记
# phase2: 契约层测试（验证 Pydantic Input/Output）
# l5_e2e: E2E 测试（需要真实数据库/缓存）
# l6_smoke: Playwright 浏览器冒烟测试
```

### pytest.mark 完整示例

```python
import pytest


@pytest.mark.phase2
class TestToolContracts:
    """验证 Pydantic 契约层"""

    def test_tool_input_accepts_valid_data(self):
        from app.contracts.example import ToolInput
        inp = ToolInput(query="SELECT 1", options=[])
        assert inp.query == "SELECT 1"

    def test_tool_input_rejects_extra_fields(self):
        from app.contracts.example import ToolInput
        with pytest.raises(Exception):  # extra="forbid"
            ToolInput(query="SELECT 1", options=[], extra_field="boom")


@pytest.mark.l5_e2e
@pytest.mark.asyncio
async def test_end_to_end_flow():
    """端到端流程（需要真实服务）"""
    ...
```

---

## Async 工具函数示例

```python
# Async generator（会话管理）
from contextlib import asynccontextmanager
from typing import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def query_service_scope() -> AsyncIterator[QueryService]:
    async for session in _provide_session(mysql_session_manager.session_factory):
        yield QueryService(...)
        break  # 仅运行一次


async def _provide_session(
    session_factory: async_sessionmaker[AsyncSession] | None,
) -> AsyncIterator[AsyncSession]:
    if session_factory is None:
        raise DatabaseError("Session factory unavailable", None)
    for attempt in range(2):
        session = session_factory()
        try:
            yield session
            if session.in_transaction():
                await session.commit()
            return
        except asyncio.CancelledError:
            await _rollback_session(session)
            raise
        except Exception:
            await _rollback_session(session)
            if attempt == 0:
                continue
            raise
```

---

## 反模式对照表

| # | 优先级 | 反模式 | 正确做法 |
|---|--------|--------|----------|
| 1 | 🔴 高 | 多处缺少 Pydantic contracts 目录 | 节点必须配 `contracts/xxx.py` |
| 2 | 🔴 高 | 并行写竞争 | 串行写入或加锁 |
| 3 | 🔴 高 | SQL 注入风险 | 参数化查询 + 白名单校验 |
| 4 | 🔴 高 | LLM 调用无超时保护 | 加 `asyncio.timeout(30)` |
| 5 | 🔴 高 | 硬编码 Prompt | `load_prompt("name")` |
| 6 | 🔴 高 | State 滥用 `Any` 类型 | 补全具体类型注解 |
| 7 | 🟡 中 | 过度使用 `except Exception` | 捕获具体异常类型 |
| 8 | 🟡 中 | execute() 方法超 100 行 | 拆分为子方法 |
| 9 | 🟡 中 | 3 处重复工具函数 | 抽取为共享工具函数 |
| 10 | 🟡 中 | 死代码 | 删除未使用的代码 |
| 11 | 🟡 中 | 错误处理不完整 | 补全所有异常路径 |
| 12 | 🟡 中 | 未使用参数 | 删除未使用的参数 |
| 13 | 🟡 中 | 重试延迟 bug | 修正重试逻辑 |
| 14 | 🟡 中 | 背景任务不可持久化 | 接入 ProgressStore |
| 15 | 🟢 低 | 命名不一致 | 对齐 snake_case 规范 |

### 新增代码时的常见反模式

| 反模式 | 正确做法 |
|--------|----------|
| `except:` 裸捕获 | `except ValidationError as e:` |
| `print("debug")` | `logger.info("debug")` |
| 硬编码 `temperature=0` | 从 `app_config.llm` 读取 |
| 节点内拼接 Prompt | `load_prompt("name")` |
| 返回整个 state | 返回增量 `dict` |
| `dict` 作为 State | `TypedDict` / `BaseModel` |
| agents/ 内写业务 if/else | 写到 `rules/` |
| 前端写中文字符串 | `i18n/zh-CN.json` |
| 多处重复定义 Schema | 统一放 `contracts/` |
| 新增 import 不声明 | 写入 `pyproject.toml` |
| 单函数 > 50 行（口径见 coding-standards） | 拆分 |
| 单节点 > 150 行 | 拆分子节点 |

---

## 坏味道代码示例

### 超级节点（应拆分）

```python
# ❌ 坏味道：300 行超级节点
async def bad_node(state: AgentState, runtime: Runtime[AgentContext]):
    # 100 行检索逻辑...
    # 100 行处理逻辑...
    # 100 行验证逻辑...
    pass

# ✅ 好：拆分为 3 个节点
# extract_keywords → validate_extraction → merge_results
```

### 参数过多（应封装为 dataclass/Pydantic）

```python
# ❌ 坏味道：7 个参数的函数
async def generate_result(
    query: str,
    items: list,
    configs: dict,
    date_info: dict,
    enum_block: str,
    user_context: dict,
    options: dict,  # <-- 太多参数
) -> dict:
    ...

# ✅ 好：封装为参数对象
class QueryContext(NamedTuple):
    query: str
    items: list
    configs: dict
    date_info: dict
    enum_block: str
    user_context: dict


async def generate_result(ctx: QueryContext, options: dict) -> dict:
    ...
```

### 嵌套过深

```python
# ❌ 坏味道：5 层嵌套
if user:
    if user.is_active:
        if user.has_permission:
            if resource.exists:
                if resource.is_accessible:
                    do_action()

# ✅ 好：提前返回 + 扁平化
if not user or not user.is_active:
    return None
if not user.has_permission:
    return None
if not resource.exists or not resource.is_accessible:
    return None
do_action()
```

### 冗余类型转换

```python
# ❌ 坏味道：多余的中间变量
items_dict = {"items": items}
validated = SomeModel.model_validate(items_dict)
return validated.model_dump()

# ✅ 好：直接传递
return SomeModel.model_validate({"items": items}).model_dump()
```

---

## 一键质量门禁命令

```bash
# === L0 语法 & 导入 ===
cd backend && python -m py_compile app/xxx.py && python -c "import app.xxx"

# === L1 风格（自动修复）===
cd backend && uv run ruff check . --fix
cd backend && uv run ruff format --check .

# === L2 静态类型 ===
cd backend && uv run mypy --strict app/

# === L3 单元测试 ===
cd backend && uv run pytest tests/unit -x -q

# === L4 代码质量 ===
cd backend && uv run ruff check . --select=F401,F811,S608,S307,SEC
cd backend && uv run radon -a -i A app/ | grep ": A$" | wc -l  # 0 才合格

# === L5 架构 & 安全（人工）===
# 禁止项见 SKILL.md §质量门禁 L5

# === L6 反模式（人工）===
# 坏味道见 PATTERNS.md §反模式速查表
```
