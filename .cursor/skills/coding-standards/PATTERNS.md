# PATTERNS — 设计模式与反模式速查

本文档是 `SKILL.md` 的子文件，按需加载。

---

## 一、设计模式速查表

| 滥用 | 正确做法 |
|------|----------|
| 用继承实现复用（子类膨胀） | 用组合 + Strategy |
| 万能类（什么都能做） | 单一职责，拆分为多个小类 |
| God Object（某个类持有太多状态） | 状态分片到对应的节点/工具/实体 |
| 过度抽象（一个接口一个类） | 接口和实现一一对应 |
| 循环依赖 | 依赖倒置，通过注入打破环 |

---

## 二、异常类规范（Result / Either / 4 级 ErrorSeverity）

### Result 类型

```python
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    value: T


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    error: E


Result = Ok[T] | Err[E]


def validate_input(input_data: dict) -> Result[ValidatedData, InputError]:
    if not input_data.get("query"):
        return Err(InputError("query is empty"))
    return Ok(ValidatedData(text=input_data["query"].strip()))


match result:
    case Ok(value):
        return value
    case Err(e):
        logger.warning(f"user_error: {e}")
        return fallback
```

### 错误分级（4 级）

```python
from enum import Enum


class ErrorSeverity(str, Enum):
    TRANSIENT = "transient"    # 可重试：网络超时、限流
    DEGRADED = "degraded"      # 降级返回：数据库挂了走缓存
    PERMANENT = "permanent"    # 不可恢复：SQL 语法错、权限拒绝
    USER_ERROR = "user_error"  # 用户输入问题：列名不存在、参数格式错


class AppError(Exception):
    severity: ErrorSeverity = ErrorSeverity.PERMANENT
    user_message: str = "服务异常，请稍后重试"
    retry_after: int | None = None
```

### 禁止的异常模式

| 禁止 | 正确做法 |
|------|----------|
| 裸 `except:` | `except ValidationError as e:` |
| except 块内空 `pass` | 必须有处理逻辑或 `raise` |
| 重复捕获同类异常 | 合并为一个 except 或用 `except (A, B)` |
| `except Exception` 吞 `CancelledError` | 先 `except asyncio.CancelledError` 再 raise |

### 不变量断言（防退化）

```python
def compute_aggregate(rows: list[Row]) -> float:
    assert rows, "rows must not be empty"  # noqa: S101
    for row in rows:
        assert "amount" in row, f"row missing amount: {row}"
    return sum(r["amount"] for r in rows)
```

---

## 三、反模式速查表（定量 + 定性）

### 定量检查（L4 自动）

| 坏味道 | 描述 | 检查工具 |
|--------|------|----------|
| 超级节点 | 单节点 > 150 行 | `radon -l` |
| 函数过长 | 单函数 > 50 行 | `radon -l` |
| 参数过多 | > 5 个参数 | `ruff --select=PLR0913` |
| 嵌套过深 | if 嵌套 > 4 层 | `ruff --select=PLR1702` |
| 重复代码 | 3 处以上相似逻辑 | `jscpd`（<=4%）+ `ruff --select=F601` |

### 定性检查（L5/L6 人工）

| 坏味道 | 描述 | 检查方法 |
|--------|------|----------|
| 散弹式修改 | 改一个需求需要改多个类 | 人工审查 |
| 发散式变化 | 一个类因不同原因频繁修改 | 人工审查 |
| 神秘命名 | 变量/函数名无意义或过渡缩写 | 人工审查 |
| 注释滥用 | 用注释掩盖逻辑而非提取函数 | 人工审查 |
| 保留注释掉的废弃代码 | 交付前未清理废弃代码 | 人工审查 |
| 调试代码残留 | 交付前未清理 `pdb.set_trace()` / `breakpoint()` / `TODO` / `XXX` / `FIXME` / `console.log` | `ruff --select=T201,T100` + 人工审查 |
| 过早优化 | 不必要的缓存/池化 | 人工审查 |
| YAGNI | 写了不需要的功能 | 人工审查 |
| 平行继承 | 两个树平行添加类 | 人工审查 |
| 循环依赖 | A→B→C→A | `python -c "import app"` |

### 常见反模式案例

| 反模式 | 正确做法 |
|--------|----------|
| `except:` 裸捕获 | `except ValidationError as e:` |
| `print("debug")` | `logger.info("debug")` |
| `pdb.set_trace()` / `breakpoint()` / `TODO` / `XXX` 残留 | 交付前清理，调试用 `logger.debug()` |
| 硬编码 `temperature=0` | 从 `app_config.llm` 读取 |
| 节点内拼接 Prompt | `load_prompt("name")` |
| 返回整个 state | 返回增量 `dict` |
| `dict` 作为 State | `TypedDict` / `BaseModel` |
| agents/ 内写业务 if/else | 写到 `rules/` |
| 前端写中文字符串 | `i18n/zh-CN.json` |
| 多处重复定义 Schema | 统一放 `contracts/` |
| 新增 import 不声明 | 写入 `pyproject.toml` |

### 全局可变数据滥用（Global Mutable State）

> **症状**：模块顶层 `cache = {}` / `stats = []` / 单例对象属性在调用过程中被各处隐式修改。
> **后果**：并发不安全（race condition）、测试不可隔离、调用顺序耦合、debug 时无法定位写入点。

```python
# ❌ 坏味道：模块级可变状态，谁都能改
_cache: dict[str, Any] = {}
_call_count = 0


def query_user(uid: str) -> dict:
    global _call_count
    _call_count += 1
    if uid in _cache:
        return _cache[uid]
    data = _fetch(uid)
    _cache[uid] = data  # 跨请求共享
    return data


# ✅ 好：显式容器 + 注入 + 不可变返回值
from types import MappingProxyType
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class UserCache:
    """通过依赖注入传递，作用域由调用方控制。"""
    _data: MappingProxyType[str, dict] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def get(self, uid: str) -> dict | None:
        return self._data.get(uid)


async def query_user(uid: str, cache: UserCache, repo: UserRepo) -> dict:
    cached = cache.get(uid)
    if cached is not None:
        return cached
    return await repo.fetch(uid)
```

**禁止模式**：

| 场景 | 反模式 | 推荐 |
|------|--------|------|
| 模块顶层 `dict/list/set` | `stats = {}` 累计 | 用类封装 + 依赖注入 |
| 函数内 `global x` | `global _counter; _counter += 1` | 用类属性 / `ContextVar` |
| 单例对象 set 属性 | `Service.instance.flag = True` | 不可变对象 + 函数返回新实例 |
| 函数修改传入的可变参数 | `def f(items: list): items.append(...)` | 返回新值，不修改入参 |
| 模块级可变默认值 | `def f(items=[])` | `def f(items: list | None = None)` + 函数内初始化 |

**自审检查**：

```bash
# 揪出模块级可变状态
grep -rn '^[A-Za-z_]*: *\(dict\|list\|set\|MutableMapping\) *= *{\|=\[\|=(set()' backend/app/

# 揪出 global 声明
grep -rn '^global ' backend/app/

# ruff B006 已覆盖 mutable 默认参数；跨模块场景手动再扫
ruff check backend/ --select=B006
```

### 数据泥团（Data Clump）

> **症状**：同一组字段总是成群结队出现在函数签名、参数列表、dict 键里（例如 `(uid, name, avatar)`、`(start_date, end_date, tz)`），却从未被封装成一个独立类型。
> **后果**：新增字段时全网要改、字典键错拼没人发现、IDE 无法跳转引用、测试构造重复样板。

```python
# ❌ 坏味道：uid + name + avatar 永远一起出现
def render_user_card(uid: str, name: str, avatar: str) -> str: ...
def update_profile(uid: str, name: str, avatar: str) -> None: ...
def build_search_index(uid: str, name: str, avatar: str) -> dict: ...

# 调用处也到处是「三件套」
render_user_card(uid, name, avatar)
update_profile(uid, name, avatar)


# ✅ 好：抽出领域类型，三件套不再四散
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserProfile:
    uid: str
    name: str
    avatar: str


def render_user_card(profile: UserProfile) -> str: ...
def update_profile(profile: UserProfile) -> None: ...
def build_search_index(profile: UserProfile) -> dict: ...

# 调用处干净
render_user_card(profile)
update_profile(profile)
```

**判定标准**（满足任一即视为数据泥团）：

| 条件 | 含义 |
|------|------|
| 同组字段在 ≥ 3 个函数签名中一起出现 | 应封装为类型 |
| 同组字段作为 dict 键频繁出现（如 `ctx["uid"]`、`ctx["name"]`） | 应封装为 `TypedDict` / Pydantic |
| 新增字段时全仓 grep 改 ≥ 5 处 | 缺少领域模型 |
| 测试中频繁用 `dict(uid=..., name=...)` 构造 fixture | 应有显式 factory |

**识别 + 自审**：

```bash
# 揪出可疑 dict 键泥团
grep -rn '"uid".*"name"\|"start_date".*"end_date"' backend/app/

# 揪出疑似泥团函数（参数全是同类型基元）
ruff check backend/ --select=PLR0913  # 参数过多 + 没封装

# 用 pylint 检测：DataClumpCheck
pylint --disable=all --enable=R0903 backend/app/
```

**与「参数 > 2 强制封装」的关系**：参数封装解决「函数签名」，数据泥团解决「概念边界」。前者是症状，后者是根因 —— 经常同时出现，应一并修。

---

## 四、前后端契约规范

### OpenAPI 自动生成（必选）

```python
app = FastAPI(
    title="{{PROJECT_NAME}} API",
    version="2.0.0",
    openapi_tags=[...],
)
# ✅ 后端任何路径变更都必须 commit openapi_snapshot.json
```

### 命名一致性

| 后端（Python） | 前端（TypeScript） | 命名规则 |
|----------------|--------------------|----------|
| snake_case | camelCase | API 层做转换 |
| `user_id` | `userId` | |
| `is_followup` | `isFollowup` | |

### 错误码规范（对齐 RFC 7807 Problem Details）

```python
class ErrorCode(str, Enum):
    USER_QUERY_INVALID = "USER_QUERY_INVALID"
    USER_QUERY_TOO_LONG = "USER_QUERY_TOO_LONG"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    QUERY_VALIDATION_FAILED = "QUERY_VALIDATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
```

### SSE 事件契约

```typescript
type SSEEvent =
  | { type: "thinking"; content: string }
  | { type: "progress"; step: string; status: "running" | "done" | "error" }
  | { type: "tool_call"; name: string; args: unknown; result?: unknown }
  | { type: "final"; result: unknown; metrics: LLMCallMetrics }
  | { type: "interrupt"; payload: unknown }
  | { type: "error"; code: ErrorCode; message: string };
```

---

## 五、Interrupt 与幂等性规范（LangGraph 1.x）

### 强制规则

| 操作 | 必须在 interrupt 之前/之后 | 原因 |
|------|--------------------|------|
| 数据库 INSERT | ❌ 之前 | 重入会产生重复行 |
| 数据库 UPSERT | ✅ 之前 | 幂等 |
| 外部 API POST(创建) | ❌ 之前 | 重入会重复创建 |
| 外部 API PUT/DELETE | ✅ 之前 | 幂等 |
| 写日志 | ✅ 之前（但要绑 trace_id） | 重复无害但会污染日志 |
| 读操作 | ✅ 之前 | 无副作用 |
| LLM 调用 | ✅ 之前（配 cache key） | 同一 query 应命中缓存 |

### 代码模板

```python
# ✅ 正确：把副作用挪到 interrupt() 之后
async def confirm_node(state, runtime):
    user_input = state.get("user_choice")
    if not user_input:
        options = compute_options(state)
        user_input = interrupt({"type": "select", "options": options})
        await db.execute(
            "INSERT INTO confirm_log (...) VALUES (...)",
            {"user_id": user_id, "choice": user_input},
        )
    return {"confirmed": True}
```

---

## 六、日志模式速查

> 完整规范：[RULES.md §五](RULES.md#五日志系统规范loguru--json-sink--trace_id-关联)；质量门禁：[GATES.md §七 L5 日志专项](GATES.md#七l5--架构--安全人工审查)。

### 6.1 Node 入口出口

```python
async def sql_gen_node(state: AgentState, runtime: Runtime[AgentContext]) -> dict:
    """节点入口自动带 trace_id（middleware 注入），无需手动 bind。"""

    writer = runtime.stream_writer
    writer({"type": "thinking", "content": "正在生成 SQL..."})

    try:
        sql = await _do_generate(state["query"])
    except SqlGenError as e:
        # ✅ 用 exception 自动抓 traceback；error_code 与 docs/api/error-codes.md 对齐
        logger.exception(
            "sql_gen_failed",
            error_code=e.code,                  # E_SQL_GEN_AST_INVALID 等
            query_len=len(state["query"]),
        )
        return {"error": e.code, "results": []}

    logger.info(
        "sql_gen_succeeded",
        sql_len=len(sql),
        ast_validated=True,
    )
    return {"sql": sql}
```

### 6.2 Tool 异常包装装饰器

```python
import functools
from typing import Callable

from app.core.log import logger


def log_tool_errors(tool_name: str):
    """统一给 Tool 包装一层 logger.exception，避免每个 Tool 都写 try/except。"""

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception:
                logger.exception("tool_failed", tool_name=tool_name)
                raise

        return wrapper

    return decorator


@log_tool_errors(tool_name="run_query")
async def run_query(query: str) -> list[dict]:
    ...
```

### 6.3 LLM 重试 + 日志

```python
from tenacity import (
    AsyncRetrying,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
from app.core.log import logger

# before_sleep 用 logger.warning 打"还差几次失败就重试"
async def call_llm(prompt: str) -> str:
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        before_sleep=before_sleep_log(logger, "WARNING"),
    ):
        with attempt:
            return await chain.ainvoke({"prompt": prompt})
```

### 6.4 Request-scoped 用户上下文

```python
# 仅在已经登录且有 pseudo_user_id 之后调用
with logger.contextualize(user_id=pseudo_id, session_id=sid):
    result = await handle_turn(state, runtime)
# 离开 with 后，user_id 自动从 contextvars 清掉
```

### 6.5 节点 Duration 自动测量（可选）

```python
import time
from contextlib import asynccontextmanager
from app.core.log import logger


@asynccontextmanager
async def log_step(name: str, **fields):
    start = time.perf_counter()
    try:
        yield
    except Exception:
        logger.exception("step_failed", step=name, duration_ms=int((time.perf_counter() - start) * 1000), **fields)
        raise
    else:
        logger.info("step_done", step=name, duration_ms=int((time.perf_counter() - start) * 1000), **fields)


async def some_node(...):
    async with log_step("sql_gen", query_len=len(q)):
        ...
```

### 6.6 测试时 logger 替身（不污染 stdout）

```python
import pytest
from app.core.log import logger

@pytest.fixture
def log_capture():
    msgs: list[dict] = []
    sink_id = logger.add(lambda m: msgs.append(m.record), format="{message}")
    yield msgs
    logger.remove(sink_id)


def test_audit_event_emitted(log_capture):
    handle_medical_reject(...)
    [record] = log_capture
    assert record["message"].startswith("audit_medical_reject")
    assert record["extra"]["score"] == 0.83
    assert record["level"].name == "WARNING"
```

### 6.7 反模式速查（loguru 专属）

| 反模式 | 后果 | 正确写法 |
|--------|------|----------|
| `logger.info(f"x={x}")` | message 不可被 Loki 聚合 | `logger.info("event", x=x)` |
| `from loguru import logger` | 测试替身失效 / 配置散落 | `from app.core.log import logger` |
| `logger.configure(...)` 在请求处理中调用 | race + 缓存失效 | 启动期一次性 `setup_logging()` |
| `logger.add(file)` 把日志写文件 | 违反 12-Factor | 只写 `sys.stdout` |
| `except Exception: logger.warning(str(e))` | 丢 traceback | `except Exception: logger.exception(...)` |
| `serialize=True` 仍拼 `format="{message}..."` | renderer 失效 | JSON sink 别写 format |
| `enqueue=False` + 多 worker | stdout 交错 | 始终 `enqueue=True` |
| `diagnose=True` 生产 | 泄漏本地变量 | `diagnose=False` |
| `logger.opt(colors=True)` 在 JSON sink | ANSI 转义进入日志 | 靠 sink 而不是 logger 层 |
| PII 字段 `.bind(email=user.email)` | 黑名单拦的是 kwargs；走通 | 用 `pseudo_user_id()` 包装 |

---

## 七、feedback_service 服务层 caller 白名单（核心安全约束）

> 来源：ADR-0016 §3.4-3.5 + `tech-arch §3.9.4` 行 1313-1318 + `error-codes.md:186` `E_ASSISTANT_FORBIDDEN_CALLER`
> 强约束：**feedback_service.list_for_user() 这一个方法必须物理拦截越权调用**（M5 SmartRouter / PersonaEngine / ModuleDispatcher 误读 photo_url → 触发医美/评判违规）。

### 7.1 关键澄清（容易踩的坑）

| 误区 | 实际 |
|------|------|
| ❌ "白名单 = 服务名" | ✅ 白名单 = **调用方法名**（`mood_diary_list` / `recall_retrieve` 等字符串） |
| ❌ "feedback_service 整体受限" | ✅ **仅 `list_for_user()` 方法受限**（其它 feedback 写方法不受限） |
| ❌ "拦截所有 feedback 读取" | ✅ 仅读 `feedback` 的方法受限；M8 召回白名单（`recall_retrieve`）允许读 text_content + photo_url 元数据，但**不喂给图片 LLM** |
| ❌ "白名单 = 4 个 service 枚举" | ✅ 白名单 = 4 个调用方名称字符串（与 ADR-0016 §3.4 完全一致） |

### 7.2 模块骨架（`backend/app/services/feedback_service.py`，≤ 40 行；新增 `caller_guard.py` ≤ 30 行）

```python
# backend/app/services/feedback_service.py
"""feedback 服务 — 严格读权限（仅 list_for_user 受限）"""
from app.errors.codes import E_ASSISTANT_FORBIDDEN_CALLER

class FeedbackService:
    # ADR-0016 §3.4 白名单（仅调用方名称字符串，非枚举）
    ALLOWED_CALLERS = frozenset({
        "mood_diary_list",      # P08 列表页
        "recall_retrieve",      # M8 主动回忆召回（仅 text_content + photo_url 元数据）
        "time_album_list",      # P09 我的时光
        "feedback_create_own",  # 自身 CRUD（写方法不受限）
    })

    @caller_required_for_read  # 装饰器（见下）
    async def list_for_user(self, user_id: str, caller: str) -> list[Feedback]:
        if caller not in self.ALLOWED_CALLERS:
            raise E_ASSISTANT_FORBIDDEN_CALLER  # 引用 error-codes.md:186
        return await self.db.query(Feedback).filter(
            Feedback.user_id == user_id,
            Feedback.deleted_at.is_(None),
        ).order_by(Feedback.created_at.desc()).all()

    # create / update / soft_delete 写方法不受白名单限制（仅校验 user_id 匹配）
```

```python
# backend/app/core/caller_guard.py
"""caller 白名单装饰器（与 error-codes.md 错误码对齐）"""
from functools import wraps
from fastapi import Request
from app.errors.codes import E_ASSISTANT_FORBIDDEN_CALLER

def caller_required_for_read(func):
    """装饰器：从 request.state.caller 取 caller，缺失或不合法即抛 403 错误码"""
    @wraps(func)
    async def wrapper(*args, request: Request, caller: str, **kwargs):
        if not caller:
            raise E_ASSISTANT_FORBIDDEN_CALLER
        return await func(*args, request=request, caller=caller, **kwargs)
    return wrapper
```

### 7.3 反模式

| 坏味道 | 后果 | 正确做法 |
|--------|------|----------|
| 函数内 `if caller not in ALLOWED: raise` | 每个读函数都要写一遍，易漏 | **必须**走 `@caller_required_for_read` 装饰器 |
| 把 `ALLOWED_CALLERS` 写在 feedback_service 内（不在 `caller_guard.py`）| 跨 service 看不到 | 严格按 ADR-0016 §3.4 写在 `FeedbackService` 类内 |
| M5 SmartRouter / PersonaEngine / ModuleDispatcher 调 `list_for_user` | 读 photo_url → 触发医美违规 | **白名单不含这 3 个**（按 ADR-0016 §3.5 强约束） |
| 用 `Enum` 写 caller 名 | 与 ADR 不一致；CI diff 检测失败 | 用字符串字面量 |
| 拦截所有 feedback 写方法 | 写自身数据也被拒 | **只拦截 list_for_user 读方法** |

### 7.4 白名单矩阵（与 `error-codes.md:186` + ADR-0016 §3.4 完全一致）

| 被调方法 | 合法 callers | 受限范围 |
|---------|------------|---------|
| `feedback_service.list_for_user()` | `mood_diary_list` / `recall_retrieve` / `time_album_list` / `feedback_create_own` | **仅此方法** |
| `feedback_service.create()` / `update()` / `soft_delete()` | （不限，仅校验 user_id 匹配）| — |

**红线**（ADR-0016 §3.5）：M5 输入框 3 个组件（SmartRouter / PersonaEngine / ModuleDispatcher）**永远不调** `list_for_user()`。

### 7.5 自审命令

```bash
# L4：业务代码不得内联 caller 判断（必须走装饰器）
grep -rn "caller not in\|caller ==\|caller !=" backend/app/services/feedback/  # 应 0 命中
# L4：物理层读方法必须用装饰器
grep -rn "@caller_required_for_read" backend/app/services/feedback/  # 应 >= 1
# L4：白名单与 SPEC-M7 一致性（ADR-0016 §3.4 的 4 个字符串）
grep -oE "\"mood_diary_list\"|\"recall_retrieve\"|\"time_album_list\"|\"feedback_create_own\"" \
  backend/app/services/feedback_service.py | wc -l  # 应 == 4
# L5：403 拦截单测
pytest backend/tests/services/feedback/test_caller_guard.py -v
# L6：M5 组件不应能调 list_for_user
for component in SmartRouter PersonaEngine ModuleDispatcher; do
  grep -rn "$component.*list_for_user\|list_for_user.*$component" backend/app/agents/ && echo "VIOLATION: $component" || true
done
```

---

## 八、Persona 4 态状态机（温柔管家型，M5 P03a）

> 来源：ADR-0015 §3.2-3.3 + `db/init/03-checks.sql:160-165`（CHECK 约束）+ `tech-arch §3.8.3.1` SessionLifecycleManager
> 强约束：**M5 P03a 上线必跑**；状态值**必须**与 `ai_sessions.persona_state_start/end` 列 CHECK 约束一致，违反 = Alembic migration 失败 + DB 写入 500。

### 8.1 4 态定义（与 DB CHECK 约束严格对齐）

| 态 | 含义 | token 输出 | 枚举值 |
|----|------|-----------|--------|
| `warm` | 默认 / 友好管家型 | 全量 | `'warm'` |
| `neutral` | 中性 / 不带情绪倾向 | 全量 | `'neutral'` |
| `slight_hug` | "你最近都没分享，我随时都在"（连续 7 天无 feedback 触发）| 全量 | `'slight_hug'` |
| `medical_guarded` | 触发医疗/医美关键词，**一次触发即回 warm** | 仅拒绝话术 | `'medical_guarded'` |

**DB CHECK 约束**（`db/init/03-checks.sql:160-165`）：

```sql
CHECK (persona_state_start IN ('warm','neutral','slight_hug','medical_guarded'))
CHECK (persona_state_end IS NULL OR persona_state_end IN ('warm','neutral','slight_hug','medical_guarded'))
```

→ 任何代码写入这 2 个列的值必须在上述 4 态之内，**否则写入失败**。

### 8.2 状态机 ASCII 转换图（按 ADR-0015 §3.2 + §10.4 "禁止跨态跳转"）

```
                   user_msg + 7 天无 feedback
                          ▼
   ┌────────► slight_hug ──────────► warm
   │            │                      ▲
   │            │ user_msg             │ user_msg
   │            ▼                      │
   │         warm ◄──────────────────► neutral
   │            │                       │
   │            │ trigger medical       │
   │            ▼                       │
   │     medical_guarded                │
   │            │                       │
   │            └─────── once ──────────┘
   │                  (回到 warm)
   ▼
   (SLEEPING 由 SessionLifecycleManager 管理，不在 4 态状态机内)
```

**关键**：warm ↔ neutral / slight_hug / medical_guarded 是允许的；**禁止跨态跳转**（如 warm → slight_hug 直接跳，需经 neutral）。

### 8.3 五条硬约束（按 ADR-0015 §3.3 + §10.4 工程纪律）

1. **必经 SessionLifecycleManager**：业务节点 `persona_service.request_transition(...)`，由 `SessionLifecycleManager` 真正写 `ai_sessions.persona_state_end`（**会话语义，非消息级**，tech-arch §3.8.3.1）。
2. **`medical_guarded` 一次性**：触发后**必须**回 warm，不允许停留在 medical_guarded（ADR-0015 §3.2）。
3. **转换必日志**：审计日志含 `from` / `to` / `user_id` / `ts` / `trigger`。
4. **状态切换频次告警**：日均切换 > 3 次即告警（ADR-0015 §4.2 风险）。
5. **会话级而非消息级**：`persona_state` 是 session 级属性，跨消息保持不变；30 分钟无活动由 `SessionLifecycleManager.SESSION_TIMEOUT_MIN = 30` 自动关闭 session（**不是状态切换**，是 session 关闭后下次开新 session）。

### 8.4 状态机伪代码（`backend/app/services/persona/state_machine.py`，≤ 35 行）

```python
"""Persona 4 态状态机（M5 P03a 必跑；与 ai_sessions CHECK 约束对齐）"""
from enum import Enum

class PersonaState(str, Enum):
    WARM = "warm"
    NEUTRAL = "neutral"
    SLIGHT_HUG = "slight_hug"
    MEDICAL_GUARDED = "medical_guarded"

# 合法转换矩阵（禁止跨态跳转）
LEGAL_TRANSITIONS: dict[PersonaState, set[PersonaState]] = {
    PersonaState.WARM: {PersonaState.NEUTRAL, PersonaState.SLIGHT_HUG, PersonaState.MEDICAL_GUARDED},
    PersonaState.NEUTRAL: {PersonaState.WARM, PersonaState.SLIGHT_HUG, PersonaState.MEDICAL_GUARDED},
    PersonaState.SLIGHT_HUG: {PersonaState.WARM, PersonaState.NEUTRAL},  # user_msg 触发回 warm
    PersonaState.MEDICAL_GUARDED: {PersonaState.WARM},  # 一次性回 warm
}

class PersonaStateError(Exception): ...

def transition(current: PersonaState, target: PersonaState, trigger: str, user_id: str) -> PersonaState:
    """状态转换；违反硬约束即抛 PersonaStateError；不直接写库（由 SessionLifecycleManager 写 ai_sessions）"""
    if target not in LEGAL_TRANSITIONS[current]:
        raise PersonaStateError(f"illegal transition {current.value} -> {target.value}")
    audit_log.info("persona_state_switch", user_id=user_id,
                   **{"from": current.value, "to": target.value, "trigger": trigger})
    return target
```

**SessionLifecycleManager 单独管理 session 关闭**（不在状态机内）：

```python
# backend/app/agents/session_lifecycle.py（节选，详见 tech-arch §3.8.3.1）
SESSION_TIMEOUT_MIN = 30  # MVP: 30 分钟无活动关闭 session

async def open_or_resume(user: User, entry_card: str | None = None) -> AISession: ...
async def close_if_idle(session: AISession) -> bool: ...  # 30 分钟判定
```

### 8.5 反模式

| 坏味道 | 后果 | 正确做法 |
|--------|------|----------|
| 业务节点直接 `session.persona_state_end = "warm"` | 绕过转换矩阵 + 审计缺失 | 必须走 `persona_service.request_transition` |
| 用 `PersonaState.ACTIVE` / `LISTENING` 等**未在 CHECK 约束内**的枚举值 | Alembic migration 成功但 DB 写入 500 | **必须**用 4 个真实值：`warm` / `neutral` / `slight_hug` / `medical_guarded` |
| 在消息级写 persona 状态 | 与会话语义冲突 | **必须**会话语义，由 `SessionLifecycleManager` 写库 |
| 30 分钟超时写在状态机内 | 状态机职责混淆 | **必须**由 `SessionLifecycleManager.close_if_idle` 单独管理 |
| 状态值用中文 `"温暖"` | 与 DB CHECK 约束 `IN ('warm', ...)` 不匹配 | 严格用英文枚举值 |

### 8.6 自审命令

```bash
# L4：枚举值必须 4 个且与 DB CHECK 一致
grep -rn "PersonaState\." backend/app/services/persona/  # 应只出现 warm/neutral/slight_hug/medical_guarded
# L4：业务代码禁止直接写 ai_sessions.persona_state_end
grep -rn 'persona_state_end\s*=' backend/app/agents/ | grep -v "session_lifecycle"  # 应 0 命中
# L4：CHECK 约束与枚举同步（CI 强制）
diff <(grep -oE "'(warm|neutral|slight_hug|medical_guarded)'" backend/app/services/persona/state_machine.py | sort -u) \
     <(grep -oE "'(warm|neutral|slight_hug|medical_guarded)'" db/init/03-checks.sql | sort -u)  # 应无 diff
# L5：合法转换矩阵单测（5 条硬约束）
pytest backend/tests/services/persona/test_state_machine.py -v
# L6：30 分钟 session 超时（SessionLifecycleManager，不在状态机内）
pytest backend/tests/agents/test_session_lifecycle.py -v
```

---

## 九、SSE 事件契约（M2 诊断流 / 异步任务流）

> 来源：`docs/api/sse-events.md`（v1.0 完整定义）+ `tech-arch §6.2`
> 强约束：**M2 诊断流（`GET /api/v1/diagnosis/{id}/stream`）上线必对齐**；10 种事件类型 = `sse-events.md §2` 真实事件名。
> ⚠️ **本节仅覆盖 M2 单次诊断任务流**；M5 P03a 长连接对话流的事件集需另行设计（P03a 需 `message` / `ping` 等持续事件，与本节不同）。

### 9.1 10 种事件类型（按 `sse-events.md §2.1-2.10` 严格对齐）

| 事件 | 用途 | schema 示例（节选） | 来源 |
|------|------|--------------------|------|
| `connected` | 握手确认 | `{"sid":"abc123","diagnosis_id":"rpt_001","timestamp":"...","expires_at":"..."}` | sse-events §2.1 |
| `processing` | 开始处理（图像预处理启动）| `{"stage":"preprocessing","message":"...","percent":5,"timestamp":"..."}` | sse-events §2.2 |
| `image_validated` | 3 张照片预处理完成 | `{"validated":true,"photos_count":3,"photo_urls":[...],"percent":25}` | sse-events §2.3 |
| `llm_calling` | LLM 调用中 | `{"model":"claude-sonnet-4-20250514","message":"...","percent":40,"estimated_remaining_seconds":12}` | sse-events §2.4 |
| `compliance_check` | 合规审查中 | `{"stage":"compliance_review","message":"...","percent":80}` | sse-events §2.5 |
| `progress` | 通用进度更新（可多次）| `{"percent":60,"message":"...","stage":"llm_analysis"}` | sse-events §2.6 |
| `result` | 诊断成功（含 directions/tags/videos）| `{"id":"rpt_001","directions":[...],"tags":[...],"recommended_video_ids":[...],"llm_cost":0.12,"cached_until":"..."}` | sse-events §2.7 |
| `fallback` | LLM 不可用降级（**30 条兜底话术轮换**）| `{"id":"...","fallback":true,"fallback_reason":"llm_timeout","directions":[...],"message":"..."}` | sse-events §2.8 |
| `error` | 处理失败 | `{"error_code":"E_DIAGNOSIS_*","message_zh":"...","message_en":"...","retryable":true}` | sse-events §2.9 |
| `done` | 流结束 | `{"total_duration_ms":18230,"final_percent":100,"event_count":8}` | sse-events §2.10 |

**关键约束**：
- ⚠️ **本节事件名与 `sse-events.md` 1:1 对应**；任何在 M2 诊断流出现的"虚构事件"（`message` / `tool_call` / `tool_result` / `thinking` / `persona_state` / `ping` / `resume`）都是**本节范围外**
- 心跳按 `sse-events.md §3` **走 SSE 注释行 `: heartbeat`**，**不是** `event: ping` 数据帧
- 错误码引用 `error-codes.md 3xxx`（`E_DIAGNOSIS_*` 系列）

### 9.2 阶段耗时预算（按 `sse-events.md §1.2`，P95 ≤ 20s）

| 阶段 | 预计耗时 | 累计上限 | 对应事件 |
|------|----------|---------|---------|
| 图像预处理 | ≤ 2s | 2s | `processing` → `image_validated` |
| LLM 调用 | ≤ 15s | 17s | `llm_calling`（含多次 `progress`）|
| 合规审查 | ≤ 3s | 20s | `compliance_check` |
| **P95 总耗时** | — | **≤ 20s** | → `result` / `fallback` / `error` → `done` |

### 9.3 心跳 + 响应头（按 `sse-events.md §3` + `§6`）

- **心跳**：每 15 秒发送 **SSE 注释行** `: heartbeat`（**不是**事件帧；前端 `data.startsWith(':')` 忽略）
- **客户端超时判定**：30 秒未收到任何数据 → 断开重连
- **响应头必须包含**：
  ```http
  Content-Type: text/event-stream
  Cache-Control: no-cache
  Connection: keep-alive
  X-Accel-Buffering: no    # 关闭 nginx 缓冲
  Transfer-Encoding: chunked
  ```
- **客户端断连**：必须 `aclose()`，否则 server 继续生成 token 浪费配额（GATES L5 校验）

### 9.4 重试策略（按 `sse-events.md §4.1`）

| 场景 | 策略 |
|------|------|
| 连接断开（未收到 `done`）| 指数退避重试：1s → 2s → 4s → 8s → 16s，最多 3 次 |
| 收到 `done` | 不重试 |
| 收到 `error` 且 `retryable=true` | 提示用户点击重试，不自动重试 |
| 收到 `error` 且 `retryable=false` | 提示具体操作，不重试 |

### 9.5 FastAPI 实现骨架（≤ 40 行，按 `sse-events.md §7` 完整事件序列）

```python
"""SSE 诊断流（GET /api/v1/diagnosis/{id}/stream；M2 上线必跑）"""
import json
from fastapi import Request
from fastapi.responses import StreamingResponse

async def diagnosis_stream(diagnosis_id: str, request: Request):
    async def gen():
        # 1. 握手 connected
        yield f"event: connected\ndata: {json.dumps({'sid': sid, 'diagnosis_id': diagnosis_id})}\n\n"
        # 2. processing / image_validated / llm_calling / compliance_check / progress
        async for stage_event in DiagnosisPipeline(diagnosis_id).stream():
            if await request.is_disconnected():
                break
            # 心跳注释行（15s 一次，sse-events §3）
            yield f": heartbeat\n\n"
            yield f"event: {stage_event.type}\nid: {stage_event.id}\ndata: {stage_event.json()}\n\n"
            if stage_event.type in {"result", "fallback", "error"}:
                break
        # 3. done
        yield f"event: done\ndata: {json.dumps({'total_duration_ms': elapsed, 'event_count': count})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

### 9.6 反模式

| 坏味道 | 后果 | 正确做法 |
|--------|------|----------|
| `Content-Type: text/event-stream` 但漏 `X-Accel-Buffering: no` | nginx 缓冲，体验割裂 | 4 个响应头必须齐全（§9.3）|
| 不用 `aclose()` | server 持续生成 token 浪费配额 | `await request.is_disconnected()` 即停 |
| 心跳用 `event: ping` 数据帧 | 与 `sse-events.md §3` 注释行方案冲突 | 必须用注释行 `: heartbeat` |
| 客户端断连后服务端继续推 | 内存泄漏 | generator 内 `async for` 必须 `break` |
| 心跳 5s 一次 | 增加带宽 / QPS | 固定 15s（sse-events §3.1）|
| 错误事件用 `error_code="E_500"` 占位符 | 与 `error-codes.md` 脱节 | 必须引用 `error-codes.md 3xxx` 真实码（如 `E_DIAGNOSIS_LLM_RATE_LIMIT`）|
| `fallback` 事件用静态话术 | 缺 30 条轮换 | 必须走 `fallback_message_pool` 随机抽取 |

### 9.7 自审命令

```bash
# L4：M2 诊断流 10 种事件必须全部出现（与 sse-events.md §2.1-2.10 一致）
for evt in connected processing image_validated llm_calling compliance_check progress result fallback error done; do
  grep -rn "\"event\": \"$evt\"\|event: $evt" backend/app/api/sse/diagnosis.py || echo "MISSING: $evt"
done
# L4：心跳注释行（不是事件帧）
grep -rn ": heartbeat" backend/app/api/sse/  # 应命中（不是 event: ping）
# L4：响应头 4 个齐全
grep -rn "X-Accel-Buffering" backend/app/api/sse/  # 应命中
# L4：错误事件必须引用 error-codes.md 3xxx
grep -rn "E_DIAGNOSIS_" backend/app/api/sse/diagnosis.py | grep -v "error-codes.md" | wc -l  # 应 >= 1
# L5：阶段耗时 P95 ≤ 20s 性能测试
pytest backend/tests/api/sse/test_diagnosis_latency.py -v
# L6：fallback 30 条话术池抽检
pytest backend/tests/api/sse/test_fallback_pool.py -v
```

---

## 十、统一分页规范（offset-based + 嵌套 pagination 对象）

> 来源：`docs/api/pagination.md`（v1.0）+ `tech-arch §6.4` + `openapi.yaml V1.1.0`
> 强约束：**MVP 阶段全用 `limit + offset`**，**不用 cursor**；响应**必须嵌套** `pagination` 对象（含 `has_next`）。

### 10.1 请求/响应 schema（与 `pagination.md §3.1` 1:1 对齐）

```python
"""统一分页 schema（5 个 list 端点共用，与 pagination.md §3 严格对齐）"""
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class PageRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=50)  # 上限 50；> 50 服务端强制截断为 50（pagination §7）
    offset: int = Field(default=0, ge=0)

class Pagination(BaseModel):
    total: int       # 总记录数
    limit: int       # 当前 limit
    offset: int      # 当前 offset
    has_next: bool   # 是否有下一页；服务端按 (offset + limit) < total 计算

class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    pagination: Pagination
    # 注：has_next 由服务端计算并返回（pagination.md §3.2），**不**让客户端自算
```

**计算规则**（`pagination.md §3.2`）：

```python
has_next = (offset + limit) < total
```

### 10.2 5 个统一端点（与 `pagination.md §4` 1:1 对齐）

| 端点 | 资源 |
|------|------|
| `GET /api/v1/community/posts` | 社区帖子列表（M6） |
| `GET /api/v1/videos/search` | 视频搜索（M3） |
| `GET /api/v1/checkins/history` | 打卡历史（M4） |
| `GET /api/v1/notifications/history` | 推送历史（M9） |
| `GET /api/v1/diagnosis/history` | 诊断历史（M2，**可选**）|

**特殊端点（不适用本规范）**：
- ⚠️ `GET /api/v1/checkins/calendar?year=&month=` —— 用**月份维度**不用 page/page_size（`pagination.md §5.3`）
- ⚠️ feedback 列表（`GET /api/v1/feedback`）—— 走 §7 caller 白名单（PATTERNS.md §七）+ ack-pool.yaml 配套；不在本节通用 list 端点范围
- ⚠️ M8 recall 历史 / M5 assistant 历史 / M3 plan 历史 —— 各自走业务端点（**与 pagination.md §4 端点不同**）

### 10.3 反模式

| 坏味道 | 后果 | 正确做法 |
|--------|------|----------|
| 用 cursor 分页 | MVP 数据 < 10 万行，offset 性能足够；cursor 增加 SDK 复杂度 | 全部 `limit + offset`（pagination §1.1） |
| 响应不带 `pagination` 嵌套 / 直接平铺 `total/limit/offset` | 与 `pagination.md §3.1` 不一致，客户端解析失败 | **必须嵌套** `pagination` 对象 |
| 响应不带 `has_next` / 让客户端用 `offset + len(items) < total` 算 | 与 `pagination.md §3.2` 不一致 | 服务端**必须返回** `has_next` |
| `limit > 50` 返回 400 错误 | 与 `pagination.md §7` 不一致（规定**强制截断为 50**）| 服务端静默截断为 50，不抛错 |
| SQLAlchemy 写 `query.skip().limit()` | 2.0 写法不一致 | 用 `select(...).offset(...).limit(...)` |
| 打卡日历端点用 `limit/offset` | 与 `pagination.md §5.3` 矛盾 | 必须用 `year + month` 维度 |
| 把本节端点列表抄成 8 个（feedbacks/plans/checkins/...）| 与 `pagination.md §4` 不一致 | 严格 5 个 |

### 10.4 自审命令

```bash
# L4：SQLAlchemy 2.0 写法统一
grep -rn "skip=\|take=" backend/app/api/v1/  # 应 0 命中
# L4：limit 上限 50 必命中
grep -rn "le=50\|max=50" backend/app/schemas/page.py  # 应命中
# L4：响应嵌套 pagination（不是平铺）
grep -rn "pagination: Pagination\|class Pagination" backend/app/schemas/page.py  # 应命中
# L4：端点必须与 pagination.md §4 一致（5 个）
grep -rn "@router.get" backend/app/api/v1/community/posts.py backend/app/api/v1/videos/search.py \
  backend/app/api/v1/checkins/history.py backend/app/api/v1/notifications/history.py \
  backend/app/api/v1/diagnosis/history.py | wc -l  # 应 == 5
# L5：5 个端点统一测试
pytest backend/tests/api/v1/test_pagination_unified.py -v
# L6：边界用例（limit=51 静默截断 / offset 负数 / total=0 / 打卡日历特殊端点）
pytest backend/tests/api/v1/test_pagination_edge.py -v
pytest backend/tests/api/v1/checkins/test_calendar.py -v  # 单独覆盖月份维度
```

---

## 十一、DB 公共规范（UUID v4 + 审计 4 字段 + 软删除 + CHECK）

> 来源：`db/init/00-04`（实际落地的 SQL）+ `docs/spec/data-dictionary.md §I`（如存在）
> 强约束：**11 张表统一行为**；新表不按此规范 = L5 阻断。

### 11.1 四项公共规范

| # | 规范 | 落地方式（与 `db/init/01-schema.sql` 实际一致） |
|---|------|--------------------------------------------|
| 1 | UUID 主键 | `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`（**PG 13+ 默认 UUID v4**，**项目无 v7 痕迹**；P2 阶段如需 v7 走时间排序优化再评估） |
| 2 | 审计 4 字段 | `created_at` / `updated_at`（`TIMESTAMPTZ DEFAULT now()`） + `created_by` / `updated_by`（UUID，引用 `users.id`） |
| 3 | 软删除 | 禁用物理 `DELETE`，统一 `deleted_at TIMESTAMPTZ NULL`（所有 SELECT 走 `WHERE deleted_at IS NULL`，SQLAlchemy 2.0 事件钩子统一加） |
| 4 | CHECK 约束 | 状态字段必有 `CHECK (status IN (...))`，禁止字符串自由文本（`db/init/03-checks.sql` 已落地 ≥ 32 条） |

### 11.2 Alembic migration 模板（≤ 30 行）

```python
"""Alembic 模板：每个新表必带 UUID + 审计 4 字段 + 软删除 + CHECK"""
import sqlalchemy as sa

def upgrade():
    op.create_table(
        "example_table",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True),
                  primary_key=True, server_default=sa.text("gen_random_uuid()")),
        # 业务字段
        sa.Column("status", sa.String(20), nullable=False),
        sa.CheckConstraint("status IN ('active', 'inactive', 'archived')", name="ck_example_status"),
        # 审计 4 字段
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by", sa.dialects.postgresql.UUID(as_uuid=True)),
        # 软删除
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_example_deleted_at", "example_table", ["deleted_at"])
```

### 11.3 SQLAlchemy 2.0 软删除 mixin（≤ 25 行）

```python
"""SQLAlchemy 2.0 软删除 mixin（统一事件钩子）"""
from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy import event
from datetime import datetime, timezone

class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    def soft_delete(self, by_user_id: str) -> None:
        self.deleted_at = datetime.now(timezone.utc)
        self.updated_by = by_user_id

@event.listens_for(Session, "do_orm_execute")
def _exclude_deleted(state):
    if state.is_select and not state.is_relationship_load:
        for desc in state.statement.column_descriptions:
            entity = desc["entity"]
            if entity is None:
                continue
            if hasattr(entity, "deleted_at"):
                state.statement = state.statement.where(
                    entity.deleted_at.is_(None)
                )
```

### 11.4 反模式

| 坏味道 | 后果 | 正确做法 |
|--------|------|----------|
| `db.execute(delete(User).where(...))` | 物理删除，不可恢复 | 必须 `soft_delete()` |
| `session.delete(user)` | 物理删除 | 同上 |
| 状态字段不加 CHECK | 任意字符串污染 | 必须 `CHECK (status IN (...))` |
| 不带 `created_by` / `updated_by` | 审计追溯断链 | 4 字段必带 |
| 列名 `createTime` / `update_time` 不一致 | 跨表 join 混乱 | 统一 snake_case：`created_at` / `updated_at` |
| Alembic migration 不带 `downgrade()` | 回滚失败 | 必有 `downgrade()` 对称实现 |

### 11.5 自审命令

```bash
# L4：物理删除必须 0 命中
grep -rn "db.execute.*delete\|session.delete(" backend/app/  # 应 0 命中
# L4：所有迁移文件必带 down()
grep -L "def downgrade" backend/migrations/versions/*.py  # 应 0 输出
# L5：软删除 + 审计单测
pytest backend/tests/db/test_soft_delete_mixin.py -v
pytest backend/tests/db/test_audit_fields.py -v
# L6：11 张表迁移完整性
psql -d selfwell_test -f backend/db/init/05-verify.sql  # 全部 PASS
```
