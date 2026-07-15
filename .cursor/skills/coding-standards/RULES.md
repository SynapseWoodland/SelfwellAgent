# RULES — 运行时安全与可观测性规范

本文档是 `SKILL.md` 的子文件，按需加载。
所有示例已去业务化，使用通用变量名。

---

## 一、SQL 生成安全防线（5 层必选）

> 所有外部查询生成（LLM 生成 SQL / 查询语言）必须通过以下 5 层验证。

### 第 1 层：AST 结构验证

```python
import sqlglot
from sqlglot import exp

ALLOWED_NODE_TYPES = (exp.Select, exp.Union, exp.Intersect, exp.Subquery)
FORBIDDEN_FUNCTIONS = {"LOAD_FILE", "OUTFILE", "SLEEP", "BENCHMARK", "INTO_OUTFILE"}


def validate_query_structure(query: str) -> None:
    parsed = sqlglot.parse_one(query, read="mysql")
    if not isinstance(parsed, ALLOWED_NODE_TYPES):
        raise QuerySecurityError(f"Only SELECT/CTE allowed, got {type(parsed).__name__}")
    for func in parsed.find_all(exp.Anonymous):
        if func.name.upper() in FORBIDDEN_FUNCTIONS:
            raise QuerySecurityError(f"Forbidden function: {func.name}")
```

### 第 2 层：列引用白名单

```python
def validate_columns_referenced(query: str, allowed_columns: set[str]) -> None:
    parsed = sqlglot.parse_one(query)
    referenced = {c.name for c in parsed.find_all(exp.Column) if c.name}
    illegal = referenced - allowed_columns
    if illegal:
        raise QuerySecurityError(f"Unauthorized columns: {illegal}")
```

### 第 3 层：连接账户强制只读（数据库层）

```sql
-- 应用连接账户必须只读
GRANT SELECT ON appdb.* TO 'app_ro'@'%';
REVOKE INSERT, UPDATE, DELETE, DROP, ALTER ON appdb.* FROM 'app_ro'@'%';

-- 强制语句超时
SET SESSION statement_timeout = '10s';
```

### 第 4 层：LIMIT 强制注入

```python
def enforce_limit(query: str, max_rows: int = 10000) -> str:
    parsed = sqlglot.parse_one(query, read="mysql")
    if parsed.args.get("limit") is None:
        parsed = parsed.limit(max_rows)
    return parsed.sql(dialect="mysql")
```

### 第 5 层：审计日志

```python
import hashlib

logger.bind(
    query_hash=hashlib.sha256(query.encode()).hexdigest(),
    user_id=ctx.user_id,
    tables_referenced=sorted(tables),
    row_count=result_size,
).info("external_query_executed")
```

### 禁用清单

| 操作 | 禁止原因 |
|------|----------|
| 字符串拼接 SQL | 注入风险 |
| `f"SELECT ... WHERE x='{user_input}'"` | 同上 |
| `subprocess.run(shell=True)` | 命令注入 |
| `eval()` / `exec()` | 任意代码执行 |
| `os.system()` | 命令注入，应用标准库替代 |
| pickle 反序列化不可信数据 | 代码执行风险（`ruff --select=S301`） |
| 应用账户授予 DDL 权限 | 横向越权 |
| 单次查询无 `statement_timeout` | 慢查询耗尽连接池 |

---

## 二、LLM 可观测性规范（OTel GenAI 语义约定）

> 所有 LLM 调用必须产生 OTel span，必带 `gen_ai.*` 属性与 token 计量。

### 必选 Span 属性

| 属性 | 类型 | 含义 |
|------|------|------|
| `gen_ai.operation.name` | string | `"chat"` / `"embedding"` / `"create_agent"` |
| `gen_ai.system` | string | `"openai"` / `"anthropic"` / `"aws_bedrock"` |
| `gen_ai.request.model` | string | 请求的模型 |
| `gen_ai.response.model` | string | 实际响应的模型 |
| `gen_ai.request.temperature` | float | 温度参数 |
| `gen_ai.usage.input_tokens` | int | 输入 token |
| `gen_ai.usage.output_tokens` | int | 输出 token |
| `gen_ai.response.finish_reasons` | string[] | `["stop"]` / `["tool_calls"]` |

### 代码模板

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


async def call_llm_node(input_data: dict, config: LLMConfig) -> dict:
    with tracer.start_as_current_span("llm.call") as span:
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.system", config.provider)
        span.set_attribute("gen_ai.request.model", config.model_name)
        span.set_attribute("gen_ai.request.temperature", config.temperature)

        result = await llm.ainvoke(input_data)

        usage = result.usage_metadata or {}
        span.set_attribute("gen_ai.response.model", result.response_metadata.get("model", ""))
        span.set_attribute("gen_ai.usage.input_tokens", usage.get("input_tokens", 0))
        span.set_attribute("gen_ai.usage.output_tokens", usage.get("output_tokens", 0))
        span.set_attribute(
            "gen_ai.response.finish_reasons",
            [result.response_metadata.get("finish_reason", "stop")],
        )
        return result
```

---

## 三、Async 调用三道防线（LLM / HTTP / Stream）

> 关键陷阱：`asyncio.timeout()` 只能停止本地等待，远程 LLM 仍会消耗 token。

### 防线 1：HTTP 客户端层 timeout（server-side 切断）

```python
llm = ChatOpenAI(
    model=app_config.llm.model_name,
    timeout=app_config.llm.request_timeout,
    max_retries=app_config.llm.max_retries,
)
```

### 防线 2：Chain 层 asyncio.timeout（end-to-end）

```python
import asyncio

async def call_chain_with_budget(chain, inputs, budget_s: float = 30.0):
    try:
        async with asyncio.timeout(budget_s):
            return await chain.ainvoke(inputs)
    except asyncio.TimeoutError:
        logger.warning(f"chain timeout after {budget_s}s")
        raise
```

### 防线 3：Stream 层 aclose + CancelledError 专捕

```python
async def stream_with_cleanup(stream):
    try:
        async for chunk in stream:
            yield chunk
    except asyncio.CancelledError:
        await stream.aclose()
        raise
    except Exception as e:
        logger.exception("stream error")
        raise
```

### 关键陷阱清单

| 陷阱 | 后果 | 正确做法 |
|------|------|----------|
| `asyncio.timeout()` 但没设 client timeout | 远程 LLM 继续消耗 token | 必须两道防线都设 |
| `except Exception` 在外层捕获 | CancelledError 被吞 | `except asyncio.CancelledError` 优先 |
| stream 客户端断开后不 `aclose()` | server 继续生成 token | 用 `async with` 或 `try/finally` |
| retry 不消耗 timeout 预算 | 5 次重试 × 30s = 150s | 共享 timeout 预算 |
| `asyncio.gather` 不接 timeout | 一个慢任务拖死所有 | `gather(*, timeout=...)` |

---

## 四、Golden Dataset 强制规范（Prompt 回归）

> Prompt 是不可变资产，必须配套版本化的 Golden Dataset 与 CI gate。

### Prompt 不可变原则

- 一旦版本发布，**禁止直接修改文件内容**
- 必须改版本号 → 新建目录
- 好处：trace 里看到的 `prompt_hash` 在历史日志里可回溯

### Prompt 版本号规则（SemVer for Prompts）

| 版本号 | 含义 | 是否需要回归测试 |
|--------|------|----------------|
| MAJOR（v2） | 重写逻辑 | 必须跑 golden set 全量 |
| MINOR（v1.5） | 新增 few-shot 例子 | 必须跑 golden set 全量 |
| PATCH（v1.4.2） | 修标点/修字 | 必须跑 golden set 全量 |

### CI 门禁

```yaml
pytest tests/golden/v1.4.2 \
  --gate="execution_rate>=0.95,exact_match>=0.80,cost_avg<=0.05"
```

---

## 五、日志系统规范（Loguru + JSON sink + trace_id 关联）

> **决议**：保留 `loguru`（已锁 `>=0.7.0`），**不切换 structlog**。理由见 `docs/adr/`（后续 ADR 编号待定）。
> 规范来源：[12-Factor App §XI Logs](https://12factor.net/logs) · [structlog 2026 best practices] · [OWASP Logging Cheat Sheet] · GDPR Article 5/17/25。
> 适用范围：`backend/app/**/*.py`；`backend/eval/**/*.py`；后续 `backend/services/`。

### 5.1 库选型与 import

```python
# ✅ 唯一合法写法
from app.core.log import logger

# ✅ 工厂函数（用于需要在 spawn 子进程/fork 时拿同一 logger 的场景）
from app.core.log import get_logger
log = get_logger(__name__)

# ❌ 禁止：直接 import loguru
# from loguru import logger

# ❌ 禁止：stdlib logging（会导致 SDK 日志绕开统一管道）
# import logging
# logger = logging.getLogger(__name__)
```

L5 gate：`grep -rn "from loguru import logger" backend/app/` 必须 0 命中。

### 5.2 `app/core/log.py` 模块规范（必落地的工厂）

| 元素 | 规范 | 说明 |
|------|------|------|
| `setup_logging(level: str, fmt: str)` | 启动期调一次 | FastAPI `lifespan` / Celery `worker_init` 各调一次 |
| stdout sink | `serialize=True` (生产) / `serialize=False, colorize=True` (开发) | 由 `LOG_FORMAT=json\|text` env 切换 |
| enqueue | `True` | 多 worker 进程安全（uvicorn `--workers 4` 必备） |
| backtrace / diagnose | `True` / `False` | diagnose 关闭避免泄漏本地变量 |
| format | `{message}` 即可 | JSON sink 下 format 字段会被 processor 加，不需要自己拼 |
| uvicorn 接管 | `InterceptHandler` 注册到 stdlib `logging.root` | 让 `uvicorn.access` / `sqlalchemy.engine` / `httpx` / anthropic/openai SDK 全走同管道 |
| contextvars | loguru `ContextVar` 存 `trace_id` / `request_id` | 需配合 §5.4 中间件 |
| sink 过滤 | `extra={"audit": True}` | §5.7 审计 sink 用此标记分流 |

骨架（**禁止直接复制粘贴到生产**，按规范补全）：

```python
# backend/app/core/log.py
"""Unified logging factory (SPEC §五)."""
from __future__ import annotations

import logging
import sys
from typing import Literal

from loguru import logger as _loguru

_LOG_FORMAT: Literal["json", "text"] = "json"
_LOG_LEVEL = "INFO"


class InterceptHandler(logging.Handler):
    """把 stdlib logging 重定向到 loguru（uvicorn/SQLAlchemy/httpx SDK 必备）。"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _loguru.level(record.levelname).name
        except ValueError:
            level = record.levelno
        _loguru.opt(depth=6, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(level: str = _LOG_LEVEL, fmt: str = _LOG_FORMAT) -> None:
    """启动期调用一次。"""
    _loguru.remove()
    if fmt == "json":
        _loguru.add(
            sys.stdout,
            serialize=True,
            enqueue=True,
            backtrace=True,
            diagnose=False,
            level=level,
        )
    else:
        _loguru.add(
            sys.stderr,
            colorize=True,
            enqueue=True,
            backtrace=True,
            diagnose=False,
            level=level,
            format=("<green>{time:HH:mm:ss.SSS}</green> | "
                    "<level>{level: <8}</level> | "
                    "{extra[trace_id]} | {message}"),
        )
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


def get_logger(name: str):
    return _loguru.bind(logger_name=name)


__all__ = ["logger", "get_logger", "setup_logging"]
```

### 5.3 日志 Schema（每条必含字段）

| 字段 | 来源 | 示例 |
|------|------|------|
| `timestamp` | loguru TimeStamper | `2026-07-05T22:00:00.000Z` |
| `level` | loguru | `INFO`/`WARNING`/`ERROR` |
| `message` | 用户 | `"chain_invoked"`（**事件名，永远不用整句话**） |
| `trace_id` | §5.4 中间件 | `"a3f9b2..."` |
| `request_id` | §5.4 中间件 | `"req_8c3..."` |
| `logger_name` | `get_logger(name)` | `"app.nodes.sql_gen"` |
| `error_code` | 业务 `docs/api/error-codes.md` | `"E_RECALL_SAFETY_BLOCKED"`（可选，错误时必带） |

**禁止**：

- `message` 字段写整句自然语言（无法被 Loki 聚合）
- 自定义嵌套字段重复 `timestamp` / `level`（sink 已经处理）

### 5.4 trace_id / request_id 注入（FastAPI 中间件）

```python
# backend/app/core/middleware.py
"""Trace ID middleware (SPEC §五.4)."""
from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

HEADER_TRACE = "X-Trace-Id"
HEADER_REQ = "X-Request-Id"


class TraceContextMiddleware(BaseHTTPMiddleware):
    """每个请求开始注入 trace_id / request_id，结束时清理 contextvars。"""

    async def dispatch(
        self, request: Request, call_next: Callable[..., Awaitable[Response]]
    ) -> Response:
        trace_id = request.headers.get(HEADER_TRACE) or uuid.uuid4().hex[:16]
        request_id = uuid.uuid4().hex[:12]
        with logger.contextualize(trace_id=trace_id, request_id=request_id):
            request.state.trace_id = trace_id
            request.state.request_id = request_id
            response = await call_next(request)
            response.headers[HEADER_TRACE] = trace_id
            response.headers[HEADER_REQ] = request_id
            return response
```

注册到 `backend/app/main.py` 的 `app.add_middleware(...)`（**中间件顺序**：trace → CORS → GZip → 业务）。

下游 `logger.info("event", k=v)` **自动**带 `trace_id`，无需手动 bind。

### 5.5 调用模式

```python
# ✅ 业务事件：永远用 kwargs，不用 f-string
logger.info("llm_invoked", model="gpt-4o", prompt_tokens=812, latency_ms=230)

# ✅ Request-scoped 上下文传播（用 contextualize 或 partial，不重新 .bind()）
with logger.contextualize(user_id=pseudo_id):
    await process(state, runtime)

# ✅ except 块一律 logger.exception（自动抓 traceback）
try:
    await chain.ainvoke(inputs)
except asyncio.TimeoutError:
    logger.exception("chain_timeout")  # 等同 log.error + exc_info=True
    raise

# ✅ 重试类用 before_sleep
@retry(stop=stop_after_attempt(3), before_sleep=before_sleep_log(logger, "WARNING"))
async def call(): ...

# ❌ 禁止：f-string（破坏聚合查询）
logger.info(f"llm_invoked model={m} tokens={n}")  # message 不可被 Loki 索引

# ❌ 禁止：print
# print("debug")

# ❌ 禁止：吞 traceback
except Exception as e:
    logger.warning(str(e))  # 应改 logger.exception
```

### 5.6 等级使用规约

| Level | 用途 | 触发后续动作 |
|-------|------|-------------|
| `DEBUG` | 详细诊断信息（payload / SQL bind values） | 仅 dev 开启 |
| `INFO` | 业务事件（节点进入/退出、路由选定、LLM 调用） | Loki 索引 |
| `WARNING` | 预期失败（validation fail、safety rejected、rate limit） | 监控告警 |
| `ERROR` | 系统级故障（DB 不可用、配置缺失、未捕获异常） | PagerDuty / 邮件 |
| `CRITICAL` | 全局不可用（启动失败、secret 泄漏） | 即时处置 |

依据：[structlog best practices — Levels] 与 [OWASP Logging Vocabulary Cheat Sheet]。

### 5.7 合规审计日志（SPEC §10.4 第 9 条 + §2.4.4）

> 拍板方案：**仅应用层 log（warning 级, `event=audit_*`）**，**不** 单独写 audit_logs 表 / 外部 sink。

| 事件名 | 必带字段 | level | 触发现场 |
|--------|---------|-------|---------|
| `audit_safety_violation` | `user_id`(pseudo), `category`, `content_hash`, `safety_passed=false` | WARNING | `RecallSafetyGuard.check()` 拒收 |
| `audit_medical_reject` | `user_id`(pseudo), `reason`, `score` | WARNING | `compliance/checker.py` 拒收 |
| `audit_persona_state_switch` | `user_id`(pseudo), `from_state`, `to_state` | INFO | persona 状态机 |

约束：

- 仅应用层 log（不异步落 ES / 不写 audit_logs 表）
- 用户 ID **必须**用 `pseudo_user_id()`（SHA256 + 固定 salt），**不允许**明文 email / phone
- PR-gate 必查：`grep -rn "audit_safety_violation\|audit_medical_reject\|audit_persona_state_switch" backend/` 至少 3 处命中
- ADR 待办：是否后续引入 Loki / ES（受 TBC-009 治理）

### 5.8 PII 脱敏（OWASP / GDPR 黑名单）

> 拍板方案：**黑名单**，不 hash。明确字段禁入日志。

| 类别 | 字段 |
|------|------|
| 凭据类 | `password` / `passwd` / `secret` / `api_key` / `token` / `bearer` / `authorization` |
| PII 明文 | `email` / `phone` / `id_card` / `ssn` |
| 支付类 | `card_number` / `cvv` |
| 健康数据 | `diagnosis` / `symptom` / `medical_record`（受 §10.4 合规管辖） |
| 网络 | `client_ip`（如需保留，预先 hash 末段） |

实现：loguru `patcher` 在写入前对 `record["extra"]` 做 key 黑名单过滤；建议放在 `app/core/log.py` 同文件 `# PATCHER BEGIN / END` 段。

```python
# ✅ 自动拦截（loguru patcher，跑在所有 sink 之前）
_PII_DENY_KEYS = {"password", "email", "phone", "card_number", "diagnosis", ...}

def _scrub_pii(record):
    extra = record.get("extra", {})
    for k in _PII_DENY_KEYS:
        if k in extra:
            extra[k] = "[REDACTED]"
    return record

_loguru = _loguru.patch(_scrub_pii)
```

L5 gate（[§5.7](#57-合规审计日志) 同处执行）：

```bash
grep -rnE "\.(password|email|phone|card_number|diagnosis)\s*=" backend/app/ \
  | grep -v "REDACTED" | grep -v "tests/"
```

> ⚠️ 已知边界：黑名单不防止"构造 log message 字符串里塞 PII"（`logger.info(f"user {email}")`）——PR-gate 配合人工 review。

### 5.9 与 `docs/api/error-codes.md` 的对齐

日志 `error_code` 字段必须与 `docs/api/error-codes.md` 中定义的 1xxx-13xxx 错误码一致：

```python
from app.core.errors import ErrorCode  # 复用 error-codes 字典

try:
    ...
except ValidationError as e:
    logger.exception(
        "input_validation_failed",
        error_code=ErrorCode.E_GENERAL_INVALID_REQUEST.value,
    )
```

### 5.10 容器 stdout 与 12-Factor 对齐

✅ docker-compose.yaml 现状：`driver: json-file, max-size=20m, max-file=5`（合规）。
✅ 应用层：`logger.add(sys.stdout, serialize=True, enqueue=True)`（合规）。
❌ 禁止：应用层直接写 `/var/log/app/*.log` 文件（破坏 12-Factor）。
❌ 禁止：应用层直连 Loki/ES/Sentry（破坏关注点分离；后续如需要，开 `app/infra/sinks/` 子模块并走 ADR）。

### 5.11 与 SDD-TDD 流程的对接

实现 logging 时的工作流（与 `.cursor/skills/sdd-tdd/SKILL.md` 一致）：

1. RED：先写 `tests/test_log.py`，断言 PII 黑名单、trace_id 注入、错误码必带
2. GREEN：在 `app/core/log.py` 实现最小够用的 setup + patcher + middleware
3. REFACTOR：抽公共 sink 配置 dataclass 到 `app/conf/app_config.py:LoggingConfig`
4. FULL GATES：L0-L5 + mypy --strict + pytest，**全套绿**才能 commit

### 5.12 关键陷阱清单

| 陷阱 | 后果 | 正确做法 |
|------|------|----------|
| `logger.add(...)` 多处重复 | 双倍日志 / 顺序错乱 | `setup_logging()` 必先 `_loguru.remove()` |
| `serialize=True` + `format="{message}"` | format 字段失效 | JSON sink 不要写 format |
| `enqueue=False` 多 worker 跑 4 进程 | 日志交错 / 丢失 | 始终 `enqueue=True` |
| `logger.exception` 在 except 块外 | 静默无 traceback | 永远在 except 内 |
| 用 `from loguru import logger` | 测试替身失效 / 无法集中配置 | 始终 `from app.core.log import logger` |
| PII 字段走 f-string 进 message | 黑名单 patcher 失效 | 仅走 kwargs |
| 多处 `logger.configure(...)` | race condition + 缓存失效 | 启动期调用一次 |
| uvicorn 不接管 | SDK 日志绕开统一格式 | `InterceptHandler` 注册到 stdlib |
| `diagnose=True` 生产开 | 泄漏本地变量 | `diagnose=False` |

---

## 六、参考文档

- Python 安全 / LLM 可观测性 / Async / Golden Dataset：第 一-四 节
- 日志系统规范（库选型 / Schema / trace_id / 审计 / PII）：第 五 节
- L0-L6 质量门禁命令 / Pre-commit Hook：见 [GATES.md](GATES.md)
- 设计模式 / 反模式 / Result：见 [PATTERNS.md](PATTERNS.md)
- 入口规则：`.cursorrules`
- PR 合入检查：`.cursor/skills/pr-gate/SKILL.md`
- Golden Set 维护：`.cursor/skills/golden-set/SKILL.md`

---

## 六、合规红线规范（8 条 + Prompt hardcode 模板）

> 来源：`docs/api/error-codes.md`（9xxx 合规错误码）+ ADR-0004 §3 + ADR-0017 §3.3 + `facts-anchor §7`
> 强约束：**MVP W1 起所有 LLM 调用必须命中本节模板**，否则 CI 阻断。

### 6.1 八条合规红线（按 ADR-0004 §3.2 关键词域 + PRD §3.2.2 拓展）

| # | 领域 | 禁用关键词（含但不限） | 标准回复话术 | 串联错误码 |
|---|------|---------------------|------------|-----------|
| 1 | 医疗 | 诊断 / 治疗 / 处方 / 根治 / 治愈 / 病情 / 确诊 / 药方 / 医生 / 医院 / 病理 / 病因 | "建议咨询专业医生" | `E_COMPLIANCE_MEDICAL_CLAIM` |
| 2 | 医美 | 微整 / 整形 / 打针 / 玻尿酸 / 瘦脸针 / 超声刀 / 热玛吉 / 抽脂 / 隆胸 / 双眼皮手术 | "暂不支持医美相关咨询" | `E_COMPLIANCE_MEDICAL_CLAIM` |
| 3 | 功效承诺 | 几天见效 / 一定能瘦 / 一定能白 / 一定会好 / 保证有效 / 一定改善 | "效果因人而异，请坚持养护" | `E_COMPLIANCE_EFFICACY_CLAIM` |
| 4 | 容貌焦虑 | 我几分 / 颜值多少 / 颜值打分 / 你觉得我好看吗 | "我们关注养护方向，不做评分" | `E_COMPLIANCE_APPEARANCE_ANXIETY` |
| 5 | 心理 | 自杀 / 自残 / 具体解脱方法 / 你应该跳楼 | "建议联系专业心理咨询师或拨打当地 24 小时心理援助热线" | （不抛错，转人工路由）|
| 6 | 法律 | 你会赢 / 你会输 / 这个案子必败 / 对方肯定 | "建议咨询专业律师" | （不抛错，转人工路由）|
| 7 | 金融 | 这只股票会涨 / 赶紧买 / 这个币要跌 | "投资有风险，请独立判断" | （不抛错，转人工路由）|
| 8 | 政治 / 隐私 / 未成年 | 人物评价 / 身份证号 / 银行卡号 / 密码 / CVV（用户主动输入） / 任意 18 岁以下话题 | "涉及政治话题不便评价" / "为保护您的隐私，请勿提供" / "请咨询监护人或专业人士" | （不抛错，转人工路由）|

**绝对禁止**（任何位置 hardcode）：
- ❌ **禁止在 prompt / 文案 / 测试 fixture 中编造未在 SPEC 注册的电话号码、URL、专有名词**（如"24 小时热线 400-161-9995"在 `docs/SPEC/forbidden-words.md` / `docs/architecture/mvp-tech-architecture.md` / `docs/adr/*.md` 中均无登记 → 引用即事故）
- ✅ 心理 / 法律 / 金融红线的话术必须**只写"建议联系专业人士"**，不下具体电话 / 机构名（等运营在 SPEC 注册后再用 `{{support_hotline}}` 模板变量）

**复合违规**：同一轮同时命中多条（如"我孩子抑郁怎么办"命中 1+5+8），按**最严级别**输出兜底话术并触发 `notification_service.dispatch_handoff(user_id, intent="human_handoff")`。

### 6.2 Prompt hardcode 强制模板

```jinja2
{# backend/app/prompts/compliance/system.j2 #}
{# 合规红线（V1.3 必读，禁止删改、禁止插入未注册的电话/URL） #}
你必须严格遵守以下合规红线，违反任意一条即输出对应话术并停止：

1. 禁止医疗诊断 / 处方 / 治愈承诺 → 输出"建议咨询专业医生"
2. 禁止医美相关建议 → 输出"暂不支持医美相关咨询"
3. 禁止功效承诺（"几天见效 / 一定能..."）→ 输出"效果因人而异，请坚持养护"
4. 禁止容貌焦虑 / 颜值打分 → 输出"我们关注养护方向，不做评分"
5. 禁止心理具体方法 → 输出"建议联系专业心理咨询师或拨打当地心理援助热线"
6. 禁止法律胜诉预测 → 输出"建议咨询专业律师"
7. 禁止投资建议 → 输出"投资有风险，请独立判断"
8. 禁止政治人物评价 / 处理隐私 PII / 对未成年人专业建议 → 输出对应兜底话术

如发现自身输出违反以上红线，必须**立即**追加"以上内容有误，建议..."自我修正段。
```

### 6.3 模板命名规范

| 路径 | 用途 | 加载方 |
|------|------|--------|
| `backend/app/prompts/compliance/system.j2` | 全局 system prompt 注入 | 所有 LLM 调用 |
| `backend/app/prompts/compliance/{domain}_redirect.j2` | 单领域兜底话术 | `ComplianceChecker.check_output` 命中时 |

**禁**：业务代码内 f-string 拼合规 prompt（GATES §13 第 6 条拦截）。

### 6.4 反模式

| 坏味道 | 后果 | 正确做法 |
|--------|------|----------|
| 在业务代码 `if "诊断" in user_input` 关键词过滤 | 误伤 + 漏过 | 交给 LLM Prompt + `ComplianceChecker` 双层 |
| 只在 system prompt 写 8 条红线、不在 §6.5 自审 | prompt 漂移没人发现 | CI 必跑 §6.5 命令 |
| 输出"已转人工"但服务层无路由 | 兜底空话 | `notification_service.dispatch_handoff(...)` 必接 |
| Prompt 中 hardcode 未注册的电话 / URL | 引导用户联系不存在的服务 → 法律风险 | 必须用 `{{ support_hotline }}` 模板变量 + SPEC 注册 |
| Prompt 中用英文写红线但 LLM 用中文 | 部分漏过 | MVP 全部用中文 hardcode |

### 6.5 自审命令

```bash
# L4：红线硬编码必须 0 漏（业务代码）
grep -rn "诊断\|处方\|根治\|微整\|玻尿酸\|几天见效" backend/app/agents/ 2>/dev/null | grep -v "\.j2:"  # 应 0 命中
# L4：禁止硬编码电话号码
grep -rn "1[3-9][0-9]{9}\|0[0-9]{2,3}-[0-9]{7,8}" backend/app/prompts/compliance/  # 应 0 命中（必须走模板变量）
# L5：Golden Set 至少 30 条 FF-COMP-* 用例（参考 ADR-0004 §7 的 G-01..G-30）
pytest backend/eval/test_golden.py -k compliance --collect-only | grep "FF-COMP" | wc -l  # >= 30
# L6：每周回归，禁止 baseline 下滑
python backend/eval/run_eval.py --mode daily --suite compliance
```

---

## 七、Recall Safety 三层架构

> 来源：ADR-0017 §3 + `facts-anchor §12.4`
> 强约束：**M8 上线前必须 0 漏过**（任何"编造" / "推断" 类输出都不允许）。

### 7.1 三层防护总览

```
[用户问题]
    │
    ▼
[第一层 · Prompt 约束] ─── system prompt 显式声明"只能复述已记录历史"
    │
    ▼
[第二层 · 关键词 100+ 词库] ─── pre-check 拦截高风险输出
    │
    ▼
[第三层 · 后处理兜底] ─── post-check 正则匹配 + 道歉 + 转人工
    │
    ▼
[用户可见回复]
```

### 7.2 关键词库（按 ADR-0017 §3.3 严格分 4 组，全量词表位置 = `docs/data/recall-forbidden-words.yaml`，待 W2 创建）

| 分组 | 数量 | 示例（节选） |
|------|------|------------|
| **前后评判** `before_after_judge` | 40+ | 比之前 / 比一开始 / 比上个月 / 比 7 天前 / 进步了 / 改善了 / 变好了 / 变差了 / 效果好 / 成效 / 见效 / 有效果 |
| **效果承诺** `effect_commit` | 30+ | 会变白 / 会瘦 / 会挺拔 / 会提升 / 肯定有效 / 保证 / 一定能 |
| **数字评判** `numeric_judge` | 20+ | 打败 / 超过 / 排名 / 第 X / 坚持 X 天真棒 / 满分 / 100 分 |
| **评判气质** `appearance_judge` | 10+ | 颜值 / 好看 / 美 / 丑 / 身材好 / 变美 / 气质好 |

**触发策略**（按 ADR-0017 §3.7）：命中 → `ai_messages.safety_passed = FALSE` + 立即告警（邮件 + IM）+ 安全兜底文案替换（不暴露给用户违规事实）+ 违规率 > 0.1% 触发模型降级。

### 7.3 模块骨架（`backend/app/services/recall/safety.py`，≤ 50 行）

> 严格按 ADR-0017 §3.1 三层架构 + §3.3 4 分组词库 + §3.7 审计告警

```python
"""Recall Safety 三层防护（M8 上线必跑）"""
from typing import Final

# Layer 2: 4 分组关键词库（与 docs/data/recall-forbidden-words.yaml 同步）
RECALL_FORBIDDEN: Final[dict[str, list[str]]] = {
    "before_after_judge": [
        "比之前", "比一开始", "比上个月", "比 7 天前",
        "进步了", "改善了", "变好了", "变差了",
        "效果好", "成效", "见效", "有效果",
        # ... 共 40+（全量见 docs/data/recall-forbidden-words.yaml）
    ],
    "effect_commit": [
        "会变白", "会瘦", "会挺拔", "会提升",
        "肯定有效", "保证", "一定能",
        # ... 共 30+
    ],
    "numeric_judge": [
        "打败", "超过", "排名", "第 X",
        "坚持 X 天真棒", "满分", "100 分",
        # ... 共 20+
    ],
    "appearance_judge": [
        "颜值", "好看", "美", "丑", "身材好",
        "变美", "气质好",
        # ... 共 10+
    ],
}

# Layer 3: 兜底文案池（人格保稳，不暴露违规事实给用户）
_SAFE_FALLBACK_SUMMARY = [
    "你过去记录过这些话，我读了一遍，都是真诚的。",
    "我看到你过去的样子——那时的你也在慢慢来。",
]
_SAFE_FALLBACK_ENCOURAGE = [
    "走到的今天，你已经在这里了。",
    "每一步都是你自己的。",
]

def check_prompt(system_prompt: str) -> str:
    """Layer 1: 在 system prompt 强制追加 Recall Safety 4 条硬约束 + 4 条可做项"""
    hardcode = (
        "\n\n【Recall Safety · 绝对不可违反】"
        "\n1. 永远不评判用户照片前后变化"
        "\n2. 永远不评判用户反馈质量"
        "\n3. 永远不评判用户坚持时长"
        "\n4. 永远不做横向自比"
        "\n【你可以做的】引用用户原文 / 引用事实确认 / 引用方案动作 / 给鼓励语"
    )
    return system_prompt + hardcode

def scan_keywords(llm_output: str) -> tuple[bool, list[str]]:
    """Layer 2: 4 分组扫描；返回 (是否命中, 命中的 (group, word) 列表)"""
    hits: list[str] = []
    for group, words in RECALL_FORBIDDEN.items():
        for w in words:
            if w in llm_output:
                hits.append(f"{group}:{w}")
    return bool(hits), hits

def post_process_output(llm_output: str) -> str:
    """Layer 3: 命中即用兜底文案替换 + 审计日志（不暴露违规事实）"""
    is_hit, hits = scan_keywords(llm_output)
    if is_hit:
        # 审计（参考 ADR-0017 §3.7 ai_messages.safety_passed + 告警）
        audit_log.warning("recall_safety_violation", hits=hits)
        return random.choice(_SAFE_FALLBACK_SUMMARY), random.choice(_SAFE_FALLBACK_ENCOURAGE)
    return llm_output
```

### 7.4 反模式

| 坏味道 | 后果 | 正确做法 |
|--------|------|----------|
| 只做第一层（Prompt）不做第二层关键词 | 模型漂移会漏过 | 必须三层全开 |
| 关键词库只放 5-10 个词 | 漏过率 > 30% | 至少 20+ 词，分 4 组 pattern |
| 第三层用 `<think>` 替换原文 | 输出不一致 / 用户感知割裂 | 整句替换为兜底话术 |
| 不写测试用例 | 关键词库新增无人把关 | 每次新增词必须加 FF-RECALL-* 用例 |

### 7.5 自审命令

```bash
# L4：模块存在性
test -f backend/app/services/recall/safety.py && echo OK
# L5：三层独立单元测试
pytest backend/tests/services/recall/test_safety.py -k "test_three_layer" -v
# L6：Golden Set 至少 10 条 FF-RECALL-* 用例
pytest backend/eval/test_golden.py -k recall --collect-only | grep "FF-RECALL" | wc -l  # >= 10
# 关键词覆盖率检查
grep -c "可能是\|好像是\|大概" backend/app/services/recall/safety.py  # 应 >= 3（pattern 中出现）
```

---

## 八、ACK 模板池与禁用词

> 来源：ADR-0016 §3.6 + `backend/app/prompts/ack/ack-pool.yaml`
> 强约束：**M7 上线前 30 条 ACK 全过禁用词扫描**（自动化 `scripts/lint_ack.py`）。

### 8.1 五类 30 条模板池（节选）

| 类别 | 条数 | 示例（节选 1-2 条） |
|------|------|------------------|
| 打招呼 | 6 | `ack_greet_01: "你好呀～今天感觉怎么样？"` / `ack_greet_06: "又见面啦，最近好吗？"` |
| 追问 | 8 | `ack_follow_01: "能再多说说吗？"` / `ack_follow_08: "听起来你很在意这点"` |
| 共情 | 6 | `ack_empathy_03: "我能理解你的感受"` / `ack_empathy_06: "这确实不容易"` |
| 收尾 | 6 | `ack_close_02: "希望这些能帮到你"` / `ack_close_05: "有需要随时来找我"` |
| 兜底 | 4 | `ack_fallback_01: "我还在学习中"` / `ack_fallback_04: "换个话题聊聊？"` |

### 8.2 ACK_FORBIDDEN_TOKENS（绝对禁词，命中即拒）

```python
ACK_FORBIDDEN_TOKENS: Final[frozenset[str]] = frozenset({
    "诊断", "处方", "可能得", "应该是", "好像是", "大概", "也许",
    "估计", "推断", "推测", "记忆模糊", "没记错", "据我", "似乎是", "依稀",
})
```

### 8.3 YAML 结构示例（节选 5 条）

```yaml
# backend/app/prompts/ack/ack-pool.yaml
ack_greet_01:
  text: "你好呀～今天感觉怎么样？"
  class: greet
  persona_state: [ACTIVE, LISTENING]
ack_follow_01:
  text: "能再多说说吗？"
  class: follow
  persona_state: [ACTIVE]
ack_empathy_03:
  text: "我能理解你的感受"
  class: empathy
  persona_state: [ACTIVE, LISTENING, WAITING]
ack_close_02:
  text: "希望这些能帮到你"
  class: close
  persona_state: [ACTIVE]
ack_fallback_01:
  text: "我还在学习中"
  class: fallback
  persona_state: [ACTIVE, LISTENING, WAITING, SLEEPING]
```

### 8.4 选 ACK 模板伪代码

```python
def pick_ack(persona_state: PersonaState, prev_class: str | None) -> str:
    """按 persona_state + 上一轮 class 选模板；连续 3 轮同类强制切换"""
    candidates = [
        t for t in ACK_POOL.values()
        if persona_state.name in t["persona_state"]
        and t["class"] != prev_class
    ]
    return random.choice(candidates)["text"]
```

### 8.5 反模式

| 坏味道 | 后果 | 正确做法 |
|--------|------|----------|
| ACK 用 LLM 实时生成 | 不一致 / 可能命中禁用词 | **必须**从 30 条池选 |
| 30 条池没用 lint 扫描 | 增量修改引入违禁词 | CI 必跑 `scripts/lint_ack.py` |
| 选 ACK 不看 persona_state | LISTENING 态用问候语违和 | 严格按 §8.4 过滤 |
| 兜底话术用"我不确定" | 触发 Recall Safety 误报 | 用"我还在学习中"代替 |

### 8.6 自审命令

```bash
# L4：禁用词扫描（CI 必跑）
python backend/scripts/lint_ack.py backend/app/prompts/ack/ack-pool.yaml
# L4：模板总数检查
grep -c "^ack_" backend/app/prompts/ack/ack-pool.yaml  # >= 30
# L5：选 ACK 函数单测
pytest backend/tests/agents/test_ack_picker.py -v
```

---

## 九、JWT 鉴权规范

> 来源：`tech-arch §7.3` + ADR-0007 + `docs/spec/SPEC-AUTH-001.md`
> 强约束：**M1 上线必跑**；token 一旦泄漏必须立即吊销（redis 黑名单）。

### 9.1 算法与有效期

| 项 | 规范 | 理由 |
|----|------|------|
| 算法 | **HS256**（对称）| MVP 单服务，省公钥管理；多服务时迁移 RS256 |
| 双 token 机制 | **access_token + refresh_token**（**项目已存在**，`error-codes.md` 行 59 已定义 `E_AUTH_REFRESH_FAILED`）| MVP 必跑 |
| access_token 有效期 | ⚠️ **待 `docs/spec/SPEC-AUTH-001.md` 确认**（常见 2h / 24h） | 写入前 grep `SPEC-AUTH-001.md` 取实际值 |
| refresh_token 有效期 | ⚠️ **待 `SPEC-AUTH-001.md` 确认**（常见 7d / 30d） | 写入前 grep `SPEC-AUTH-001.md` 取实际值 |
| 传输 | `Authorization: Bearer <access_token>` | RFC 6750 |
| 必须 claim（access）| `sub` / `iat` / `exp` / `jti` | 4 项缺一不可 |
| 错误码 | 过期 = `E_AUTH_TOKEN_EXPIRED` / 刷新失败 = `E_AUTH_REFRESH_FAILED` / 无效签名 = `E_AUTH_TOKEN_INVALID` | 引用 `error-codes.md 2xxx` |

### 9.2 中间件骨架（`backend/app/api/middleware/auth.py`，≤ 30 行）

```python
"""JWT 鉴权中间件（M1 上线必跑）"""
from datetime import datetime, timezone
from fastapi import Request
from jose import JWTError, jwt
from app.core.config import settings
from app.errors.codes import E_AUTH_TOKEN_INVALID, E_AUTH_TOKEN_EXPIRED

async def auth_middleware(request: Request, call_next):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        request.state.user_id = None  # 匿名端点放行
        return await call_next(request)
    token = auth.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except JWTError as e:
        raise E_AUTH_TOKEN_INVALID from e
    if await redis.exists(f"jwt:blocked:{payload['jti']}"):
        raise E_AUTH_TOKEN_EXPIRED
    request.state.user_id = payload["sub"]
    return await call_next(request)
```

### 9.3 吊销机制（用户封禁/删除即时失效）

```python
async def revoke_token(jti: str, exp: int) -> None:
    """吊销 token；TTL = 剩余有效期，到期自动清理"""
    ttl = exp - int(datetime.now(timezone.utc).timestamp())
    if ttl > 0:
        await redis.setex(f"jwt:blocked:{jti}", ttl, "1")
```

### 9.4 反模式

| 坏味道 | 后果 | 正确做法 |
|--------|------|----------|
| RS256 / 复杂公钥管理 | MVP 单服务冗余 | HS256 |
| 不引入 refresh_token（与 `E_AUTH_REFRESH_FAILED` 错误码矛盾）| 客户端无法续期 / 实现 = 错误码永远不抛 | **必须 access + refresh 双 token** |
| 把 token 写日志 | 一旦日志泄漏 = 永久身份冒用 | 列入 PII 黑名单（RULES §5.x） |
| `jwt.decode(..., options={"verify_exp": False})` | 永不过期 | 始终 verify_exp |
| 吊销不用 redis 用内存 | 多 worker 不生效 | 必须 redis 黑名单 |
| access_token 有效期凭印象填（如"7 天"）| 与 SPEC 不一致 | 必读 `SPEC-AUTH-001.md` 取实际值 |

### 9.5 自审命令

```bash
# L4：jwt 编码/解码必须只在 auth_service
grep -rn "jwt.encode\|jwt.decode" backend/app/ | grep -v "app/services/auth/"  # 应 0 命中
# L4：算法强制 HS256
grep -rn "algorithms=\[\"RS256\"\]" backend/app/  # 应 0 命中
# L5：中间件单测
pytest backend/tests/api/middleware/test_auth.py -v
# L6：端到端 401/403 路径
pytest backend/tests/api/test_auth_e2e.py -v
```
