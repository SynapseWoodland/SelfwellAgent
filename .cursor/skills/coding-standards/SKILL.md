---
name: coding-standards
description: >
  Python 编码规范 skill。当编写、审查或重构 Python 代码时触发。
  覆盖：类型注解、命名规范、State 定义、节点规范、工具规范、错误处理、日志、配置、测试规范、复杂度约束、L0-L6 质量门禁。
  AI 完成代码编写后、提交前必须执行自审（对标 L0-L6 质量门禁）。
  长文档拆分至子文件：RULES.md（安全与可观测性）、GATES.md（质量门禁）、PATTERNS.md（设计模式与反模式）。
disable-model-invocation: false
---

# Python 编码规范

## 文件长度约束

> 遵循 VoltAgent Skill Quality Standards：SKILL.md 主体 < 500 行。
> 大型参考文档移至子文件，AI 按需加载。

长文档拆分策略：

- `SKILL.md`（< 500 行）— 核心规范 + 快速参考
- `EXAMPLES.md`（保持不变）— 测试代码示例
- `RULES.md`（新增）— SQL 生成安全五层防线、LLM 可观测性、Async 三道防线、Golden Dataset
- `GATES.md`（新增）— L0-L6 详细门禁命令、Pre-commit Hook、四点清单、自我改进循环
- `PATTERNS.md`（新增）— 设计模式速查表、反模式速查表、Result 类型、Interrupt 幂等性

---

## 项目基本信息

- **运行时**：Python >= 3.11（推荐 3.12+）
- **包管理**：uv
- **框架**：FastAPI + LangGraph + LangChain
- **行长度**：`line-length = 100`（pyproject.toml）

---

## 一、代码组织与目录边界

| 职责             | 路径           | 约束                            |
| -------------- | ------------ | ----------------------------- |
| State / Schema | `schemas/`   | 统一用 Pydantic v2，禁止多处重复定义      |
| Agent 编排       | `agents/`    | 仅放图编排，业务逻辑抽离到 nodes/tools     |
| 节点实现           | `nodes/`     | 单一职责，禁止超级节点                   |
| 工具             | `tools/`     | 继承 BaseTool，统一 retry/fallback |
| 硬规则            | `rules/`     | 声明式 YAML + 纯 Python 解释器       |
| Prompt 模板      | `prompts/`   | `.prompt` 文件，禁止在节点内拼接         |
| 配置             | `conf/`      | YAML + dataclass，禁止硬编码        |
| 实体模型           | `entities/`  | `@dataclass` 或 Pydantic       |
| 节点契约           | `contracts/` | 继承 `NodeInput`/`NodeOutput`   |

**禁止**：agents/ 目录内不得写业务规则（必须写在 rules/）。

---

## 二、命名与可读性

### 命名规范

| 类型    | 规范                 | 示例                              |
| ----- | ------------------ | ------------------------------- |
| 文件    | `snake_case.py`    | `process_node.py`               |
| 类     | `PascalCase`       | `AgentContext`                  |
| 函数/变量 | `snake_case`       | `process_node`                  |
| 常量    | `UPPER_SNAKE_CASE` | `CONNECTION_ERROR`              |
| 类型别名  | `PascalCase`       | `RouteName = Literal["a", "b"]` |
| 私有变量  | `_snake_case`      | `_routing_config`               |

### 禁止的命名

- **神秘命名**：变量/函数名无意义或过度缩写（如 `x1`、`tmp2`、`get_it`）
- **单字母变量**：除循环计数器 `i/j/k`、类型泛型 `T/U/V` 外，禁止单字母命名
- **匈牙利命名**：禁止 `str_name`、`int_count` 前缀

### 注释规范

```python
# ✅ 好的注释：解释不显而易见的决策
# 保留 __cause__，方便排查根因
raise TransientError("LLM 调用超时") from e

# ❌ 坏的注释：用注释掩盖逻辑而非提取函数
# x 如果是负数就取反
if x < 0:
    x = -x

# ❌ 废弃代码：禁止保留注释掉的代码交付
```

- 禁止用注释掩盖应提取函数的逻辑
- 禁止保留注释掉的废弃代码（直接删除，用 git 历史找回）
- 注释掉的代码块保留超过 1 个 PR 未清理，触发 L6 反模式告警

---

## 三、类型注解

```python
# ✅ 必须：所有函数/类/公开变量标注类型
async def process_node(state: AgentState, runtime: Runtime[AgentContext]) -> dict:
    ...

# ✅ 复杂结构用 Pydantic（不要用裸 dict）
class ToolInput(NodeInput):
    query: str
    options: list[str] = []
    is_followup: bool = False

# ✅ TypedDict（仅限 Agent State）
class AgentState(TypedDict):
    query: Required[str]
    keywords: Required[list[str]]
    results: Annotated[Required[list], operator.add]  # 累加归约

# ✅ 用 | 而非 Union（Python 3.10+）
result: list[str] | None

# ✅ Python 3.12+ type 语句（推荐）
type RouteName = Literal["general_chat", "data_query"]
type SqlList = list[str]
```

### Python 3.12+ PEP 695 语法（推荐）

```python
def first[T](items: list[T]) -> T | None:
    return items[0] if items else None

def traced[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        with tracer.start_as_current_span(func.__name__):
            return func(*args, **kwargs)
    return wrapper
```

**禁止**：

- 装饰器未使用 `@functools.wraps` 保留元信息
- 混用绝对导入和相对导入（统一使用绝对导入，从项目根路径写 `from app.xxx`）
- 滥用海象运算符 `:=`（仅在推导式/条件表达式中合理使用时允许）

---

## 四、State 定义（Agent）

> **铁律**：Agent State **必须用 `TypedDict`**（不要用 `dict`，不要用 Pydantic BaseModel 作为 State）。

```python
from typing import TypedDict, Required, NotRequired, Annotated
import operator


class AgentState(TypedDict):
    query: Required[str]
    keywords: Required[list[str]]
    retrieved_items: Annotated[Required[list], operator.add]  # 累加归约
    error: Required[Optional[str]]
    previous_result: NotRequired[str]
    retry_count: Annotated[NotRequired[int], lambda old, new: old + new]  # 增量归约
```

### Accumulator vs Overwrite 语义

| 字段类型         | 语义                | Annotated                                        | 示例                         |
| ------------ | ----------------- |:------------------------------------------------:| -------------------------- |
| 累加型 list     | 跨节点追加，不覆盖         | `Annotated[list, operator.add]`                  | `messages`, `results`      |
| 累加型 list(去重) | messages、findings | `Annotated[list, add_messages]`                  | 同上                         |
| 标量           | 单分支写入             | 不加 Annotated                                     | `current_step`, `approved` |
| 标量           | 多分支求和(cost/token) | `Annotated[int, operator.add]`                   | `total_cost`               |
| 不可交换 reducer | 严格顺序              | `Annotated[int, lambda old, new: max(old, new)]` | `retry_count`              |

### 三大硬约束

1. **禁止单 super-step 多分支写同 key 不加 reducer**（会抛 `InvalidUpdateError`）
2. **禁止在节点内 `state["key"] = ...`**（必须返回 dict 增量）
3. **自定义 reducer 必须满足交换律**（除明确标注）

**禁止**：

- 在 State 中存储原始 LLM 响应（含 usage metadata），序列化成本极高
- 用 `dict` 作为 State 类型
- 在节点内直接修改 state 变量

---

## 五、复杂度约束（量化门禁）

> 所有阈值必须有工具支撑或有行业最佳实践来源。无据可查的数字不得作为强制门禁。

| 约束       | 推荐值    | 硬限       | 检查工具                    | 说明                                     |
| -------- | ------ | -------- | ----------------------- | -------------------------------------- |
| 单函数代码行   | ≤ 20 行 | <= 50 行 | `radon -l`              | Clean Code（ClawHub 465k installs）      |
| 函数参数     | ≤ 3 个  | ≤ 5 个    | `ruff --select=PLR0913` | Clean Code + ruff 官方默认值                |
| if 嵌套深度  | ≤ 2 层  | ≤ 4 层    | `ruff --select=PLR1702` | Clean Code + ruff 官方默认值                |
| 圈复杂度     | <=5    | <=5      | `radon -a -i A`         | 超标需要通过提取子函数、卫语句或策略模式重构                 |
| 函数语句数    | —      | ≤ 50     | `ruff --select=PLR0915` | ruff 官方默认值 |
| 函数分支数    | —      | ≤ 12     | `ruff --select=PLR0912` | ruff 官方默认值                             |
| 代码重复率    | —      | ≤ 4%     | `jscpd`                 | 用户要求                                   |
| 单文件函数/类数 | —      | ≤ 20     | `radon -l`              | —                                      |

---

## 六、节点规范（LangGraph）

```python
# ✅ 标准节点签名
async def process_node(state: AgentState, runtime: Runtime[AgentContext]) -> dict:
    writer = runtime.stream_writer
    writer({"type": "thinking", "content": "正在处理..."})
    writer({"type": "progress", "step": "处理中", "status": "running"})

    # --- 入口校验 ---
    try:
        ToolInput.model_validate({"query": state["query"]})
    except ValidationError as e:
        logger.warning(f"process_node input validation failed: {e}")
        return {"error": str(e), "results": []}

    # ... 业务逻辑 ...

    # --- 出口校验 ---
    try:
        output = ToolOutput.model_validate({"results": [...]})
        return output.model_dump()
    except ValidationError as e:
        logger.warning(f"process_node output validation failed: {e}")
        return {"error": str(e), "results": []}
```

节点规则：

- 入口/出口用 Pydantic contract 校验
- 通过 `runtime.stream_writer` 输出 SSE 事件
- 返回**状态增量**（`dict`），禁止返回整个 state
- 单一职责，单节点 <= 150 行
- 禁止在节点内硬编码 Prompt（用 `load_prompt()`）

---

## 七、节点契约（contracts/）

```python
# ✅ app/agent/contracts/example.py
"""example contract (SPEC §4.1)."""
from app.agent.contracts.common import NodeInput, NodeOutput


class ToolInput(NodeInput):
    """Extra fields are forbidden by parent ConfigDict(extra="forbid")."""
    query: str
    options: list[str] = []


class ToolOutput(NodeOutput):
    results: list[dict] = []
    error: str | None = None


__all__ = ["ToolInput", "ToolOutput"]
```

**禁止**：禁止在 `agents/` 内直接定义 Pydantic Model（必须抽到 contracts/）。

---

## 八、工具规范（tools/）

```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class QueryArgs(BaseModel):
    query: str = Field(..., description="待执行的查询语句")


class QueryTool(BaseTool):
    name: str = "run_query"
    description: str = "执行查询并返回结果"
    args_schema: type[BaseModel] = QueryArgs

    def _run(self, query: str) -> str:
        ...

    async def _arun(self, query: str) -> str:
        ...
```

- `name`/`description` 精准清晰
- 入参严格 Schema 校验
- 所有工具调用必须幂等
- 统一 retry/fallback（tenacity）
- 禁止硬编码 LLM 参数（从 config 读取）

---

## 九、错误处理与日志

### 异常处理规范

```python
# ✅ 捕获明确异常，记录日志（用 logger.exception 自动抓 traceback，详见 §九-日志）
try:
    result = await chain.ainvoke({"query": query})
except ValidationError:
    logger.exception("input_validation_failed", error_code="E_GENERAL_INVALID_REQUEST")
    return {"error": str(e)}
except httpx.TimeoutException as e:
    raise TransientError("LLM 调用超时") from e  # 保留 __cause__

# ❌ 禁止裸 except
# except:
# ✅ 禁止 except Exception 吞没 CancelledError
# 必须先捕获 asyncio.CancelledError
```

### 日志规范速查

> **完整规范**：见 [RULES.md §五](RULES.md#五日志系统规范loguru--json-sink--trace_id-关联)（库选型 / Schema / trace_id middleware / PII 黑名单 / 合规审计 3 事件 / 与 error-codes 对齐，约 200 行）。
>
> 模式速查：见 [PATTERNS.md §六-日志模式](PATTERNS.md#六日志模式速查)。

```python
# ✅ 唯一合法 import：禁止 from loguru import logger
from app.core.log import logger

# ✅ 业务事件：kwargs 而非 f-string（让字段可被 Loki 聚合）
logger.info("llm_invoked", model="gpt-4o", prompt_tokens=812, latency_ms=230)

# ✅ except 块统一用 logger.exception（自动抓 traceback）
except ValidationError:
    logger.exception("input_validation_failed", error_code="E_GENERAL_INVALID_REQUEST")

# ✅ trace_id / request_id 由 TraceContextMiddleware 自动注入，**无需手动 bind**
# ✅ 合规审计三事件必须打（SPEC §10.4 第 9 条 / §2.4.4）
logger.warning("audit_safety_violation", user_id=pseudo, category="medical", content_hash=hash)
logger.warning("audit_medical_reject", user_id=pseudo, reason="...", score=0.83)
logger.info("audit_persona_state_switch", user_id=pseudo, from_state="...", to_state="...")

# ❌ 禁止：print / from loguru import logger / f-string 进 message
```

### 九之附、API 错误码规范（对外契约）

> **唯一真源**：错误码字典见 [`docs/api/error-codes.md`](../../../docs/api/error-codes.md)。本节只定义**编码规则与对外契约**，所有具体码值、模块范围、i18n 文案必须以该字典为准。
>
> **行业参考**：[RFC 9457 Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html)（取代 RFC 7807）、[Microsoft API Guidelines · ErrorResponses](https://github.com/microsoft/api-guidelines/blob/vNext/graph/articles/errorResponses.md)、[Google AIP-193 Errors](https://google.aip.dev/193)、[Stripe API Errors](https://docs.stripe.com/api/errors)、[AWS SDK ErrCode 约定](https://aws.amazon.com/blogs/developer/aws-sdk-for-go-adds-error-code-constants/)、[阿里 Java 开发手册·错误码规约](https://developer.aliyun.com/article/1230228)。

#### 1. 适用边界

| 维度 | 适用 | 不适用 |
|------|------|--------|
| **场景** | 对外 HTTP/WebSocket API（移动端 / 小程序 / 第三方）响应体的错误码字段 | LangGraph 节点内部 `state["error"]`、Python 异常类名、日志字段 |
| **对象** | `code` 业务码字符串 + `message_zh/message_en` 文案 | 异常类名（走 [PATTERNS.md §二](./PATTERNS.md) 的 `ErrorSeverity` 4 级） |
| **同步源** | `docs/api/error-codes.md` + `openapi.yaml#/components/responses/*` 双向同步 | 单元测试断言字符串 |

**原则**（综合 RFC 9457 §3.1、Microsoft Guidelines、AIP-193、阿里手册 §13）：

- **HTTP 状态码** 表达"传输层结果"（4xx 客户端、5xx 服务端）；**业务码** 表达"语义层原因"。
- **业务码不可变**：一旦进入 `error-codes.md` 字典，**禁止修改 `code` 字符串**；语义变更只能新增、不能复用。
- **错误码不承担业务数据**：HTTP body 内不通过错误码本身承载过多业务属性（阿里手册 §8），业务变量通过 `message_zh` 插值或额外字段承载。

#### 2. 命名规则

```text
E_<MODULE>_<VERB_OR_NOUN>
```

| 段 | 约束 | 取值依据 |
|----|------|----------|
| `E_` 前缀 | 强制，标识"Error code"，与日志字段、日志 tag、SDK 异常类名做视觉区分 | Microsoft / Stripe / Google 全部使用字符串字面量；阿里用字母（A/B/C） |
| `<MODULE>` | 强制大写，对应 `docs/api/error-codes.md` 中的模块前缀：`GENERAL` / `AUTH` / `USER` / `DIAGNOSIS` / `PLAN` / `VIDEO` / `CHECKIN` / `COMMUNITY` / `NOTIFICATION` / `COMPLIANCE` / `ASSISTANT` / `FEEDBACK` / `RECALL` / `SHARE` | 与 facts-anchor.md §1 模块编号 M1-M11 对齐 |
| `<VERB_OR_NOUN>` | UPPER_SNAKE_CASE，仅字母/数字/下划线；推荐用**动词短语或动名词**表达失败原因，避免无意义后缀（如 `_ERROR` / `_FAIL` 与前缀重复） | Google ErrorInfo.reason 正则 `[A-Z][A-Z0-9_]+[A-Z0-9]` ≤ 63 字符 |

**正例**（沿用现有 `error-codes.md`）：

```text
E_AUTH_TOKEN_EXPIRED          # 模块=AUTH，原因=TOKEN_EXPIRED
E_DIAGNOSIS_IMAGE_TOO_LARGE   # 模块=DIAGNOSIS，原因=IMAGE_TOO_LARGE
E_CHECKIN_DUPLICATE           # 模块=CHECKIN，原因=DUPLICATE
```

**反例**：

```text
E_AUTH_TOKEN_EXPIRED_ERROR    # ❌ 重复 _ERROR 后缀
E401                          # ❌ 与 HTTP 状态码语义混淆（阿里手册 §11 明确禁止）
E_auth_tokenExpired           # ❌ 不符合 UPPER_SNAKE_CASE
AuthTokenExpired              # ❌ 没有 E_ 前缀，无法与日志/异常类区分
```

#### 3. HTTP 状态码映射

> HTTP 状态码只描述"传输层结果"，必须与业务码**配合**使用：同一 HTTP 状态码下可以有多个不同业务码（如 `400` 下同时存在 `E_USER_INVALID_INPUT` / `E_PLAN_INVALID_INPUT`）。

| HTTP 范围 | 语义 | 与 `ErrorSeverity` 映射 | 典型业务码示例 |
|-----------|------|-------------------------|----------------|
| `200` | 业务级 soft-tip（语义成功但需提示） | `USER_ERROR`（前端弹 toast） | `E_RECALL_EMPTY`、`E_RECALL_SAFETY_BLOCKED` |

> **200 soft-tip 豁免**：当 HTTP 状态为 200 时，响应体仍可携带 `error.code` 用于表达业务级警告（如空态、命中安全词），但**不视为业务错误**；§3 的"业务码↔HTTP 一一对应"约束在此豁免（因为语义层是"成功"，只是附带提示）。
| `400` | 请求语法/语义错误 | `USER_ERROR` | `E_*_INVALID_INPUT`、`E_*_INVALID_ENUM`、`E_*_TOO_LONG` |
| `401` | 未认证 / Token 失效 | `USER_ERROR` | `E_AUTH_*`、`E_GENERAL_UNAUTHORIZED` |
| `403` | 已认证但无权限 | `USER_ERROR` / `PERMANENT` | `E_GENERAL_FORBIDDEN`、`E_COMPLIANCE_USER_BLOCKED` |
| `404` | 资源不存在 | `USER_ERROR` | `E_*_NOT_FOUND` |
| `409` | 资源状态冲突 | `USER_ERROR` | `E_*_DUPLICATE`、`E_*_IN_PROGRESS`、`E_*_ALREADY_EXISTS` |
| `413` | 请求体过大 | `USER_ERROR` | `E_FEEDBACK_PHOTO_TOO_LARGE` |
| `429` | 限流 | `TRANSIENT` | `E_*_RATE_LIMIT`、`E_*_FREQUENT`（须配合 `Retry-After` 头） |
| `500` | 未捕获的服务端异常 | `PERMANENT` | `E_GENERAL_INTERNAL_ERROR` |
| `502` | 上游依赖异常 | `TRANSIENT` | `E_DIAGNOSIS_LLM_UNAVAILABLE`、`E_ASSISTANT_LLM_ERROR` |
| `503` | 服务暂时不可用 | `TRANSIENT` / `DEGRADED` | `E_NOTIFICATION_WX_SUBSCRIBE_FAILED`、`E_GENERAL_SERVICE_UNAVAILABLE` |

**强制约束**：

- 同一业务码**必须**只对应一个 HTTP 状态码（避免 `E_USER_INVALID_INPUT` 既返 400 又返 422，破坏客户端契约）。**唯一已知例外**：`docs/api/error-codes.md` 中 `E_VIDEO_NOT_FOUND` 在第 98 行（4xxx 方案/视频模块）与第 141 行（7xxx 视频扩展模块）重复出现，message 略不同，属于 V1.0 历史债务，**待重构统一为 `E_VIDEO_NOT_FOUND` + `E_VIDEO_INACTIVE`（见 §6 重构路径）**。
- **429 Retry-After 头约定**（按码表中 `{seconds}` 占位符是否精确，分三档）：

  | 档位 | 触发条件 | Retry-After 处理 | 示例 |
  |------|----------|------------------|------|
  | **精确秒数** | `message_zh` 含精确秒数占位符（如 `{seconds}`） | **必带** `Retry-After: <秒数>` | `E_USER_SMS_SEND_FREQUENT`、`E_AUTH_LOGIN_FREQUENT` |
  | **粒度提示** | message 含"明日 / 5 分钟 / 1 分钟"等粒度表述 | **推荐带**，值由后端按粒度向上取整为秒（如"5 分钟"→ 300） | `E_DIAGNOSIS_RATE_LIMIT`、`E_COMMUNITY_POST_FREQUENT`、`E_FEEDBACK_DAILY_LIMIT` |
  | **无明确时长** | message 仅为"稍后重试 / 正常节奏"等模糊表述 | **不带**；前端按默认退避策略（如指数退避 5s→30s→120s） | `E_GENERAL_RATE_LIMIT`、`E_CHECKIN_RATE_LIMIT` |

  这一约定与 RFC 9457 §4 + Stripe `Stripe-Should-Retry` 启发保持兼容；后端中间件 `app/api/middleware/rate_limit.py` 必须按上表三档分别实现（详见 §6）。
- 5xx 响应**必须**带 `traceparent` / `X-Request-ID` 头（OpenTelemetry 约定），由 `app/api/middleware/trace.py` 统一注入，便于日志关联；trace id 字段**不进**响应体 body（保持 `ErrorResponse` schema 向后兼容）。

#### 4. ErrorResponse 响应体 Schema

**与现有 `openapi.yaml#/components/schemas/ErrorResponse` 100% 对齐**（任何修改须同步 PR `openapi.yaml` + `error-codes.md`）：

```json
{
  "error": {
    "code": "E_USER_INVALID_INPUT",
    "message_zh": "输入参数错误",
    "message_en": "Invalid user input"
  }
}
```

| 字段 | 必填 | 类型 | 约束 |
|------|:----:|------|------|
| `error.code` | ✅ | string | UPPER_SNAKE_CASE，正则 `^E_[A-Z]+_[A-Z0-9_]+$`，≤ 64 字符，**对外契约字段，禁止重命名** |
| `error.message_zh` | ✅ | string | 简体中文，可含 `{field}` `{value}` `{limit}` 等占位符，运行时由后端插值 |
| `error.message_en` | ⚠️ 推荐 | string | 英文回退文案，与 `message_zh` 一一对应；缺失时前端降级为 `message_zh` |

**为什么用 `{error: {...}}` 包裹而不是顶层平铺**（参考 Microsoft Graph Guidelines §7.10.2）：

- 为未来**扩展字段预留命名空间**（如 `target` / `details` / `innererror`），不破坏现有客户端解析。
- 与 RFC 9457 Problem Details 兼容路径清晰：未来可通过 `Accept: application/problem+json` 协商切换，问题体可以包含同名字段而不冲突。

**为什么不用 RFC 9457 的 `application/problem+json`**（截至 V1.3 不启用）：

- 移动端 SDK 已按 `{ error: { code, message } }` 解析，切换媒体类型属于破坏性变更。
- 当前错误码数量级（M1-M11 共约 80 条）远小于 RFC 9457 推荐的"URI 类型空间"，平铺 `code` 已足够定位。
- **未来迁移路径**（P2 评估）：在 `ErrorResponse.error` 下增加可选扩展字段 `type`（RFC 9457 problem type URI），逐步向 Problem Details 对齐。

#### 5. 错误分级与业务码的对应

对外 HTTP 业务码**不直接**承载 4 级 `ErrorSeverity`（那是内部异常分级，见 [PATTERNS.md §二](./PATTERNS.md)），但**通过 HTTP 状态码段做隐式映射**，前端可基于状态码段决定重试/降级策略：

| HTTP 段 | 前端默认策略 | 后端重试建议 |
|---------|--------------|--------------|
| 2xx（含 200 soft-tip） | 正常处理 / 弹 toast | — |
| 400 / 403 / 404 / 409 / 413 | 不重试，提示用户 | — |
| 401 | 调 refresh 接口，失败跳登录 | — |
| 429 | 按 `Retry-After` 退避重试 | — |
| 5xx | 指数退避，最多 3 次 | 502/503 可立即重试；500 一般不重试 |

后端**内部**异常 → 业务码的转换，由 `app/api/middleware/exception_handler.py` 统一处理（与 `ErrorSeverity` 联动），不在各 handler 内散落。

#### 6. 枚举管理与审批流程

- **唯一源**：`docs/api/error-codes.md`（开发者查阅）+ `openapi.yaml#/components/responses/*`（SDK 生成）**双向同步**。
- **新增**：必须先在该字典中申请编号（含 HTTP 状态码、`message_zh` / `message_en` 文案、前端处理建议），经 PR review 后入库。**先到先得**，编号即被永久固定（阿里手册 §5）。
- **200 soft-tip 新增流程**：在 PR 描述中必须额外标注"业务级提示而非错误"，由 `exception_handler` 单独走 `soft_tip` 通道（区别于真正的 error 响应），不进入监控告警。
- **禁用范围**：禁止在 `agents/`、`nodes/`、`tools/`、`api/v1/*` 内**硬编码**错误码字符串（与 L4 门禁一致）；必须 `from app.errors.codes import E_*` 引用常量，CI 卡 `grep -R "E_[A-Z]" app/` 排除 `app/errors/codes.py`。
- **冻结策略**：已进入 `error-codes.md` 的业务码，**禁止**变更语义；如必须变更，应新增码并标注旧码为 `DEPRECATED`（OpenAPI 中加 `deprecated: true`），保留 ≥ 1 个大版本后再删除。
- **已知债务 → 重构路径**：`E_VIDEO_NOT_FOUND` 在 4xxx 与 7xxx 模块下重复（详见 §3），应在下个迭代统一为：
  - 保留 `E_VIDEO_NOT_FOUND`（语义：video_id 无结果，404）
  - 复用既有 `E_VIDEO_INACTIVE`（语义：视频已下架，409）
  - 删除 7xxx 段的冗余 instance，并同步更新 `openapi.yaml#/components/responses/E_VIDEO_NOT_FOUND`
  - 跟踪 issue：`docs/api/error-codes.md` 行 98 vs 行 141

#### 7. 国际化（i18n）

- `message_zh` 默认值由后端提供；客户端**可**基于 `code` 做二次本地化（推荐）。
- 客户端切换语言时，应**优先使用客户端翻译表**；仅在缺失时回退到响应体的 `message_zh` / `message_en`。
- 占位符（如 `{field}` `{value}` `{limit}` `{seconds}`）由后端在抛出前完成插值，禁止把未替换的模板字符串下发（会泄露内部实现细节）。

#### 8. 与 OpenAPI 契约的关系

- `openapi.yaml#/components/schemas/ErrorResponse` 是 **机器可读的契约**，`error-codes.md` 是**人类可读的字典**，二者必须保持一致。
- 新增 / 修改 / 废弃任何业务码，必须**同时**提交两个文件的 PR（Code Review 必须两个文件一起 diff）。
- `openapi.yaml` 中的 `responses` 示例（`example.error.code`）必须从 `error-codes.md` 复制，不允许手写避免漂移。

#### 9. 禁止项速查

| 禁止 | 正确做法 |
|------|----------|
| 错误码字符串中带 HTTP 状态码（`E401_*`） | HTTP 状态码由状态行承载，业务码独立 |
| 错误码语义随版本变更（同一 code 不同含义） | 新增新码 + 旧码打 `DEPRECATED` |
| 在 `agents/` / `nodes/` / `api/` 内硬编码 `E_*` 字符串 | `from app.errors.codes import E_USER_INVALID_INPUT` |
| `error-codes.md` 与 `openapi.yaml` 单边修改 | 两个文件必须同 PR |
| 错误码下放过多业务数据（`E_USER_NAME_LEN_20`） | 用 `message_zh` 插值 `{field}/{max}` 表达 |
| 5xx 不带 `traceparent` / `X-Request-ID` 头 | 中间件统一注入，便于日志关联 |
| 429 不带 `Retry-After` 头（除非 §3 表中标注为"无明确时长"档） | 按 `message_zh` 中的精确秒数 / 粒度写头 |
| 把内部异常类名（如 `ValidationError`）当业务码 | 异常→业务码映射由 `exception_handler` 集中处理 |

#### 10. 反例参考（业界教训）

| 错误做法 | 后果 | 参考来源 |
|----------|------|----------|
| 用纯数字 `12345` 当错误码 | 不利于跨语言团队协作；不便于感性记忆与分类 | 阿里手册 §13 |
| 业务码与 HTTP 状态码重复编码（`E400_INVALID_INPUT`） | 状态升级时（如 400→422）要全量替换 | 阿里手册 §11 |
| `code` 字段类型为 number（`code: 1001`） | 客户端 if/else 误判，且不利于 i18n | Stripe type+code 双层结构教训 |
| 错误码里塞 JSON / URL（`E_AUTH_LOGIN_FAILED_https://...`） | 解析复杂度爆炸，XSS 风险 | RFC 9457 §3.2 extension 命名约束 |
| `message` 直接拼接堆栈（`"ValueError at line 42"`) | 泄露内部实现，攻击面扩大 | Microsoft Guidelines §7.10.2 |

---

## 十、配置规范

```python
# ✅ 从 app.conf.app_config 读取
from app.conf.app_config import app_config

llm = init_chat_model(
    model=app_config.llm.model_name,
    base_url=app_config.llm.base_url,
    api_key=app_config.llm.api_key,
    temperature=app_config.llm.temperature,
)

# ✅ dataclass 配置类
@dataclass
class LLMConfig:
    model_name: str = "gpt-4o"
    api_key: str = ""
    base_url: str = ""
    timeout: int = 30
```

**禁止**：硬编码密钥、阈值、模型名、base_url。

---

## 十一、Docstring 规范

Google 风格，公开类/函数必须包含 Args / Returns / Raises：

```python
def route_by_classification(state: dict) -> str:
    """
    Route the query based on classification.

    Args:
        state: AgentState dict with classification result

    Returns:
        Route name string for langgraph conditional routing.

    Raises:
        ValueError: If classification is missing from state.
    """
```

### 公开 API 强制要求 Example

LangChain 规范：所有公开函数/类的 docstring 必须包含最小使用示例：

```python
class RouteClassifier:
    """
    Classify user query into route types.

    Args:
        llm: Language model instance for classification.

    Example:
        >>> classifier = RouteClassifier(llm)
        >>> route = classifier.classify("查询数据")
        >>> assert route in SUPPORTED_ROUTES
    """
```

---

## 十二、测试规范

详见 [EXAMPLES.md](EXAMPLES.md)。核心原则：

| 原则       | 说明                                                 |
| -------- | -------------------------------------------------- |
| TDD      | 先写测试（RED）→ 写实现（GREEN）→ 重构                          |
| Mock LLM | 用 `unittest.mock.AsyncMock`，禁止调用真实模型               |
| 外部服务     | 用 `fakeredis`、VCR.py cassette                      |
| 测试命名     | `test_<模块>_<场景>.py`                                |
| 覆盖率门槛    | rules >= 90%，agents/middleware >= 80%，tools >= 70% |

### 测试目录结构

| 目录                   | 用途                    |
| -------------------- | --------------------- |
| `tests/unit/`        | 单元测试（纯 Python，无需外部依赖） |
| `tests/contracts/`   | Pydantic 契约验证测试       |
| `tests/nodes/`       | 单节点逻辑测试               |
| `tests/subgraphs/`   | 子图集成测试                |
| `tests/integration/` | 模块间交互测试               |
| `tests/e2e/`         | 端到端流程测试               |
| `tests/smoke/`       | API 冒烟测试              |
| `tests/state/`       | 状态归约测试                |

---

## 十三、质量门禁（L0-L4）

详见 [GATES.md](GATES.md)。核心命令：

```bash
# L0 语法
cd backend && python -m py_compile app/xxx.py

# L1 风格
cd backend && uv run ruff check . --fix && uv run ruff format --check .

# L2 类型
cd backend && uv run mypy --strict app/

# L3 单元测试
cd backend && uv run pytest tests/unit -x -q

# L4 代码质量
cd backend && uv run ruff check . --select=F401,F811,S608,S307,SEC,B,B003
cd backend && uv run radon -a -i A app/ | grep -v ": A$"
cd backend && uv run jscpd .
```

---

## 十四、禁止项速查表

| 禁止                                    | 正确做法                                      |
| ------------------------------------- | ----------------------------------------- |
| 裸 `except:`                           | `except ValidationError as e:`            |
| `print()`                             | `logger.info()`                           |
| `from loguru import logger` / stdlib `logging.getLogger` | `from app.core.log import logger`（统一工厂）|
| `logger.info(f"...{user_email}...")` f-string 进 message | 用 kwargs `logger.info("event_name", email=pseudo)` |
| `except Exception: logger.warning(str(e))` 吞 traceback | `except Exception: logger.exception("event_failed")` |
| 未经过 `setup_logging()` 直接 `logger.add(...)` | 启动期 `lifespan` 调一次；多 worker 必 `enqueue=True` |
| PII 字段（email/phone/card_number/diagnosis）进日志 | 黑名单 patcher 拦截或字段不进日志 |
| agents/ 写业务规则                         | 写到 rules/                                 |
| 硬编码 LLM 参数                            | 从 `app_config.llm.*` 读取                   |
| 硬编码 Prompt 字符串                        | 用 `load_prompt("name")`                   |
| 节点内直接修改 state                         | 返回状态增量 `dict`                             |
| 多处重复定义 Schema                         | 统一放 `contracts/`                          |
| 并行分支写同 key 不加 reducer                 | 加 `Annotated[T, ...]` 或拆 key              |
| `except Exception` 吞 `CancelledError` | 先 `except asyncio.CancelledError` 再 raise |
| Prompt 改了但没跑 Golden Set               | 改 prompt 必须跑对应版本 golden 回归                |
| 字符串拼接 SQL                             | sqlglot AST 解析 + 参数化绑定                    |
| 应用账户授予 DDL/写权限                        | 强制只读 + statement_timeout                  |
| 装饰器未用 `@wraps`                        | 必须用 `@functools.wraps` 保留元信息              |
| `os.system()`                         | 用标准库替代（subprocess.run 等）                  |
| pickle 反序列化不可信数据                      | 使用 JSON 等安全格式                             |
| 混用绝对/相对导入                             | 统一使用绝对导入                                  |
| 滥用海象运算符 `:=`                          | 仅在推导式/条件表达式中合理使用                          |
| 可变默认参数                                | 用 `None` + 函数内初始化                         |

详见 [RULES.md](RULES.md) 的 SQL 安全五层防线、LLM 可观测性、**日志系统规范（§五，库选型 / Schema / trace_id / PII 黑名单 / 合规审计 3 事件）**。
详见 [PATTERNS.md](PATTERNS.md) 的设计模式速查表、反模式速查表、Result 类型、**日志模式（§六）**规范。

---

## 十五、参考文档

- 详细测试代码示例：[EXAMPLES.md](EXAMPLES.md)
- SQL 安全 / LLM 可观测性 / Async / Golden Dataset / **日志系统规范**：[RULES.md](RULES.md)
- L0-L6 质量门禁命令 / Pre-commit Hook / 四点清单 / **L5 日志扫描**：[GATES.md](GATES.md)
- 设计模式 / 反模式 / Result / 前后端契约 / **日志模式速查**：[PATTERNS.md](PATTERNS.md)
- **对外 API 错误码规范（命名 / HTTP 映射 / 契约 / 兼容性）**：本 SKILL.md §九之附
- 错误码字典（唯一真源）：[`docs/api/error-codes.md`](../../../docs/api/error-codes.md)
- OpenAPI 契约：`docs/api/openapi.yaml`
- 入口规则：`.cursorrules`
- PR 合入检查：`.cursor/skills/pr-gate/SKILL.md`
- Golden Set 维护：`.cursor/skills/golden-set/SKILL.md`
