# Bugfix · RecallDailyLimitError 返回 500 但前端看到 "服务端错误，请稍后重试"

> **日期**：2026-07-14
> **触发背景**：用户在前端调用"生成主动回忆"接口被限流时，看到的不是"今日已生成过一次主动回忆"，而是"服务端错误，请稍后重试"；uvicorn 日志同时刷出长达 50 行的 traceback
> **故障类型**：业务异常被错误包装，导致 `message_zh` / `http_status` 丢失
> **关联模块**：M8 主动回忆（`/api/v1/butler/recall`）
> **状态**：已修复（见 §5 修法）

---

## 0. 给 Java 转 Python 同事的前置知识

> 如果你是写 Java 多年、刚转 Python 的工程师，先读这一节；后面 §1-§5 都是建立在这些概念上的。

### 0.1 Python 的"异常"机制和 Java 大致一样

| Java | Python | 说明 |
|------|--------|------|
| `throw new RuntimeException("msg")` | `raise RuntimeError("msg")` | 都是主动抛异常 |
| `try { ... } catch (RuntimeException e) { ... }` | `try: ... except RuntimeError as e: ...` | 都是捕获 |
| `class MyExc extends RuntimeException { ... }` | `class MyExc(RuntimeException): ...` | 都是继承 |
| `e.getCause()` | `e.__cause__` | 都能拿到被包装的原始异常 |

### 0.2 Python 的 `**kwargs` 是"兜底收集器"

Java 没有这个概念，所以这是最容易踩坑的地方：

```python
def __init__(self, message=None, *, code=None, http_status=None, **context):
    """初始化异常。"""
```

上面这个签名的意思是：

- `message` / `code` / `http_status` 是**显式命名参数**，调用方传进来才会被绑定
- `**context` 是**兜底**：除了上面三个以外的**所有**命名参数都会被塞进 `context` 字典里

**重点**：如果你在调用时传了一个 `**context` 不认识的命名参数，它**不会报错**，它会**默默被吞掉**放到 `context` 里。这是和 Java 最大的不同——Java 的方法签名如果不匹配就直接编译报错，Python 是运行时默默吞掉。

### 0.3 类属性 vs 实例属性

Python 的类可以有"默认值"（类属性），实例可以"覆盖"它们：

```python
class Dog:
    name = "旺财"   # 类属性：默认值

d = Dog()
print(d.name)    # "旺财" —— 用类属性
d.name = "小黑"  # 实例属性：覆盖了类属性
print(d.name)    # "小黑"
```

**重点**：如果你没有在构造函数里把某个字段写到 `self.xxx`，那它就一直用**类属性的默认值**，改不掉。

### 0.4 middleware / handler 模式

FastAPI 的请求处理流程（类似 Java Servlet Filter + Spring `@ControllerAdvice` 的合体）：

```
请求进来
  → TraceContextMiddleware（生成 request_id）
  → ExceptionHandlerMiddleware（兜底捕获所有异常）
  → RateLimitMiddleware
  → 业务 router（你的 endpoint）
  → service（抛业务异常）
  → 异常冒泡回 ExceptionHandlerMiddleware
  → 渲染成 JSON 返回给前端
```

异常是从内往外冒的，最外层那个 `ExceptionHandlerMiddleware` 就是"全局兜底 handler"。

---

## 1. 故障现象

### 1.1 前端看到什么

```
[用户操作] 点击"今日回忆"按钮
[网络]    POST /api/v1/butler/recall → 429 Too Many Requests
[前端]    toast("服务端错误，请稍后重试")    ← ❌ 错！
```

### 1.2 后端日志刷什么

```
[2026-07-14 09:50:06] app.errors.envelope.AppBusinessError: 服务端错误，请稍后重试
[50 行 traceback，包括 starlette / anyio / sqlalchemy 等框架调用栈]
[2026-07-14 09:50:06] "POST /api/v1/butler/recall HTTP/1.1" 429
```

### 1.3 期望行为

```
[2026-07-14 09:50:06] selfwell_error code=E_RECALL_DAILY_LIMIT http_status=429 severity=USER_ERROR
[2026-07-14 09:50:06] "POST /api/v1/butler/recall HTTP/1.1" 429
```

响应体也应该是：

```json
{
  "error": {
    "code": "E_RECALL_DAILY_LIMIT",
    "message_zh": "今日已生成过一次主动回忆",
    "message_en": "Daily recall limit reached",
    "http_status": 429,
    "request_id": "abc123..."
  }
}
```

---

## 2. 根因（这个 bug 是怎么发生的）

### 2.1 直接原因：router 把 service 异常"重新包装"时弄丢了字段

`backend/app/api/routers/butler_v1.py`（**修复前**）：

```python
@butler_router.post("/recall")
async def generate_recall_endpoint(...):
    try:
        return {"code": 0, "data": await generate_recall(...)}
    except (RecallError, RecallDailyLimitError) as exc:    # ← service 抛的异常
        raise AppBusinessError(                           # ← 重新包装一次
            code=exc.code,
            message_zh=exc.render_zh(),
            http_status=exc.http_status,
            **exc.context,
        ) from exc
```

看起来"忠实转发"了，但 `AppBusinessError` 继承 `SelfwellError`：

```python
# backend/app/core/errors.py
class SelfwellError(Exception):
    code: str = "E_GENERAL_INTERNAL_ERROR"      # ← 类属性默认值
    message_zh: str = "服务端错误，请稍后重试"  # ← 类属性默认值
    http_status: int = 500

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        severity: ... = None,
        http_status: int | None = None,
        **context: object,
    ) -> None:
        ...
        if code is not None: self.code = code          # ✅ code 被覆盖
        if http_status is not None: self.http_status = http_status  # ✅ 被覆盖
        ...
        self.context = dict(context)                  # ❌ message_zh 被塞这里
```

**问题来了**：`SelfwellError.__init__` 的命名参数列表里**没有** `message_zh` 也没有 `message_en`。

所以 router 里 `AppBusinessError(message_zh="今日已生成过一次主动回忆", ...)` 时：

| 参数 | 走哪个分支 | 结果 |
|------|-----------|------|
| `code="E_RECALL_DAILY_LIMIT"` | 命中显式参数 `code=` | ✅ `self.code` 被覆盖为 `E_RECALL_DAILY_LIMIT` |
| `http_status=429` | 命中显式参数 `http_status=` | ✅ `self.http_status` 被覆盖为 429 |
| `message_zh="今日已生成过一次主动回忆"` | **不在显式参数里** → 被 `**context` 吞掉 | ❌ `self.message_zh` 还是类属性默认值 `"服务端错误，请稍后重试"` |
| `message_en="..."` | 同上 | ❌ 同上 |

最终 HTTP 响应：`{"error": {"code": "E_RECALL_DAILY_LIMIT", "message_zh": "服务端错误，请稍后重试", ...}}`

—— code 对、http_status 对（429），但 message_zh 是**假的**，前端看到了"服务端错误，请稍后重试"。

### 2.2 这个 bug 的本质（写给 Java 同事的对比）

**Java 等价物**：假设你写了

```java
public class SelfwellError extends RuntimeException {
    private String code = "E_GENERAL_INTERNAL_ERROR";
    private String messageZh = "服务端错误，请稍后重试";
    private int httpStatus = 500;

    public SelfwellError(String message, String code, ErrorSeverity severity,
                         Integer httpStatus, Map<String, Object> context) {
        super(message);
        if (code != null) this.code = code;
        if (httpStatus != null) this.httpStatus = httpStatus;
        this.context = context;
    }
}
```

然后同事这么调：

```java
throw new AppBusinessError(
    "今天限流",
    exc.getCode(),                  // 显式赋值 this.code ✅
    null,
    exc.getHttpStatus(),            // 显式赋值 this.httpStatus ✅
    Map.of("message_zh", "今日已生成过一次主动回忆",  // ← 进 context 字典
           "message_en", "Daily recall limit reached")
);
```

Java 会因为**没有 setMessageZh() 调用**就让 `this.messageZh` 一直是默认值 `"服务端错误，请稍后重试"`——和你在 Python 看到的现象一模一样。

**唯一的区别**：Java 的同事大概率不会这么写（Java 的构造器签名很明确），但 Python 因为 `**kwargs` 的存在，**默默吞参数**这个反模式很容易写出来且不报错。

### 2.3 为什么 logger.exception 一直在打 traceback

修复前的 `exception_handler.py`：

```python
except SelfwellError as exc:
    logger.exception(   # ← logger.exception 会自动捕获 sys.exc_info() 的 traceback
        "selfwell_error",
        code=exc.code,
        ...
    )
```

每条业务异常（429 / 400 / 409）都会刷一长串 traceback 到日志——这对**调试 500 错误**有用，但对**用户操作错误**是噪音（用户每天触发一两次限流，日志就被刷屏）。

---

## 3. 影响范围

### 3.1 业务影响

| 模块 | 路径 | 触发条件 | 用户感知 |
|------|------|---------|---------|
| M8 主动回忆 | `POST /api/v1/butler/recall` | 同一用户今日已生成回忆 | 看到"服务端错误，请稍后重试"（应见"今日已生成过一次主动回忆"） |
| M5 智能管家 | `POST /api/v1/assistant/sessions` + `.../messages` | service 抛 `AssistantError` / `SessionNotFoundError` / `SessionClosedError` | 同样：消息错乱 |
| M2 诊断 | `POST /api/v1/diagnosis` + `GET /{report_id}` | service 抛 `DiagnosisError` / `DiagnosisNotFoundError` | 同样：消息错乱 |

### 3.2 运维影响

uvicorn 日志被 traceback 污染，按 Loki 的 `code` 聚合查询时噪声比 = 100%（每条业务异常都刷 traceback）。

---

## 4. 排查过程（怎么定位到 bug 的）

### 4.1 第一步：定位 HTTP 真实状态码

uvicorn access log 显示：

```
2026-07-14 09:50:06.149 "POST /api/v1/butler/recall HTTP/1.1" 429
```

→ **HTTP 是 429**（限流），不是 500。所以 `http_status=429` 这一路没坏。

### 4.2 第二步：对比 service 定义 vs 实际响应

`backend/app/services/recall_service.py:142-146`（service 定义，**正确**）：

```python
class RecallDailyLimitError(RecallError):
    code: str = E_RECALL_DAILY_LIMIT                          # "E_RECALL_DAILY_LIMIT"
    message_zh: str = "今日已生成过一次主动回忆"
    message_en: str = "Daily recall limit reached"
    http_status = 429
```

实际响应（用户截图，**错误**）：

```
"message_zh": "服务端错误，请稍后重试"
```

→ `message_zh` 被错误改写。`code` 和 `http_status` 都对，说明 `AppBusinessError.__init__` 收到了正确的 `code=` 和 `http_status=`，唯独 `message_zh=` / `message_en=` 这两个字段没生效。

### 4.3 第三步：看 `SelfwellError.__init__` 的签名

```python
def __init__(self, message=None, *, code=None, severity=None, http_status=None, **context):
```

→ 没有 `message_zh=` / `message_en=` 命名参数。它们**默默进了 `**context` 字典**。

### 4.4 结论

`butler_v1.py:62-67` 的 `raise AppBusinessError(...)` 写法是"看起来在转发，实际只转发了一半"。`code` 和 `http_status` 通过显式参数传过去了，但 `message_zh` 和 `message_en` 因为不是 `__init__` 的命名参数，被 `**context` 吞掉——所以 `self.message_zh` 一直是 `AppBusinessError` 类属性默认值 `"服务端错误，请稍后重试"`。

---

## 5. 修法（推荐：删 router 的 re-wrap + 改 logger 级别）

### 5.1 修法 D（核心）：删 router 内的 re-wrap try/except

**before**：

```python
@butler_router.post("/recall")
async def generate_recall_endpoint(...):
    try:
        return {"code": 0, "data": await generate_recall(...)}
    except (RecallError, RecallDailyLimitError) as exc:
        raise AppBusinessError(
            code=exc.code,
            message_zh=exc.render_zh(),
            http_status=exc.http_status,
            **exc.context,
        ) from exc
```

**after**：

```python
@butler_router.post("/recall")
async def generate_recall_endpoint(...):
    """生成一次主动回忆。

    Raises:
        RecallError / RecallDailyLimitError: 由 ExceptionHandlerMiddleware
            接管为标准 envelope；service 异常已自带 code/http_status/message_zh，
            router 不做 re-wrap 避免上下文丢失。

    """
    payload = body or RecallGenerateRequest()
    return {
        "code": 0,
        "data": await generate_recall(...),
    }
```

**为什么这样修就对了**：

- `RecallError` / `RecallDailyLimitError` 本来就继承 `SelfwellError`
- `SelfwellError` 的 `code` / `message_zh` / `http_status` 是**类属性默认值**，实例不需要重新赋值就能用
- 让异常直接冒泡到 `ExceptionHandlerMiddleware`，middleware 会自动调 `to_error_response(exc)` 拿到正确的 `code / render_zh() / render_en()`

### 5.2 修法 C（辅助）：业务异常不打 traceback

`backend/app/api/middleware/exception_handler.py`：

```python
except SelfwellError as exc:
    # 业务异常（4xx / 429 / 200 soft-tip）：不打 traceback（每条都打会污染日志），
    # 走结构化字段，便于 Loki 按 code / severity 聚合。traceback 仅在
    # ``unhandled_exception``（500 兜底）才需要。
    logger.warning(
        "selfwell_error",
        code=exc.code,
        http_status=exc.http_status,
        severity=exc.severity,
        path=request.url.path,
        exc_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=exc.http_status,
        content=make_envelope(exc, request=request),
    )
```

`logger.warning` 比 `logger.exception` 少做一件事：**不打印 traceback**。业务异常我们只关心 `code / http_status / severity`，不需要 traceback。500 兜底那段（`except Exception`）保留 `logger.exception`——那种才是真正需要 traceback 排查的。

### 5.3 回归测试（防止 bug 复发）

新增 `backend/tests/unit/api/test_recall_daily_limit_envelope.py`：

```python
async def test_recall_daily_limit_envelope_preserves_message_zh() -> None:
    """回归：RecallDailyLimitError → envelope.message_zh 不能被 re-wrap 吞掉。"""
    app = FastAPI(title="recall-daily-limit-regression")
    app.include_router(butler_router, prefix="/api/v1")
    app.add_middleware(ExceptionHandlerMiddleware)
    app.dependency_overrides[current_user_id] = (
        lambda: "00000000-0000-0000-0000-000000000099"
    )

    async def _raise_daily_limit(*_a, **_kw):
        raise RecallDailyLimitError()

    with patch("app.api.routers.butler_v1.generate_recall", side_effect=_raise_daily_limit):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/butler/recall", json={})

    assert resp.status_code == 429
    body = resp.json()
    err = body["error"]
    assert err["code"] == "E_RECALL_DAILY_LIMIT"
    # ★ 核心断言：message_zh 必须是 service 层定义的中文文案，**不能**是默认值
    assert err["message_zh"] == "今日已生成过一次主动回忆"
```

**重点**：这条测试**专门**断言 `message_zh == "今日已生成过一次主动回忆"`。如果以后有人再把 `raise AppBusinessError(message_zh=exc.render_zh(), ...)` 写回来，这条测试会立刻挂掉。

---

## 6. 受影响文件清单

### 6.1 修复

| 文件 | 改动 |
|------|------|
| `backend/app/api/middleware/exception_handler.py` | 修法 C：`logger.exception` → `logger.warning`（业务异常不打 traceback） |
| `backend/app/api/routers/butler_v1.py` | 修法 D：删 `generate_recall_endpoint` / `get_recall_endpoint` 的 re-wrap try/except |
| `backend/app/api/routers/assistant_v1.py` | 修法 D：删 `create_session_endpoint` / `send_message_endpoint` 的 re-wrap；抽 `_assert_ai_session_open` helper |
| `backend/app/api/routers/diagnosis_v1.py` | 修法 D：删 `create_diagnosis` (sync path) / `get_diagnosis_endpoint` 的 re-wrap |

### 6.2 测试

| 文件 | 改动 |
|------|------|
| `backend/tests/unit/api/test_exception_handler_traceback.py` | 同步：`test_selfwell_error_logs_with_traceback` → `test_selfwell_error_logs_as_warning`（反转语义） |
| `backend/tests/unit/api/test_recall_daily_limit_envelope.py` | **新增**：回归测试 |

---

## 7. 给 Java 转 Python 同事的 takeaway

1. **永远不要依赖 `**kwargs` 的"默默兜底"来传业务字段**。如果一个类的构造器有 `**kwargs`，意味着它接受任意额外字段——但那些额外字段不会自动变成实例属性，会被装到一个字典里。要么在构造器签名里显式列出，要么用 `setattr` 手动设属性。

2. **类属性的默认值是被"沉默覆盖"的**。`self.foo = ...` 没执行，`self.foo` 用的就是类属性的值。和 Java 的 `private String foo = "default"` 在子类不重写时的行为一样，但 Python 因为没有"重写"语义、更容易踩坑。

3. **业务异常的 `message_zh` 应该是 service 异常类的类属性**，而不是从 service 拉数据再"转发"。转发层（router / middleware）应该是"通道"，不是"加工厂"。

4. **`logger.exception` 仅用于你真的需要 traceback 的场景**（500 / 未预期异常）。业务异常用 `logger.warning` 加结构化字段就够了——Loki 按 `code / severity` 聚合比读 traceback 高效得多。

5. **写防御性测试**：每修一个 bug 都加一条"如果 bug 复现这条测试就挂"的断言。本次的 `test_recall_daily_limit_envelope_preserves_message_zh` 就是这个原则的实例。

---

## 8. 修复后验证

```bash
# L0 语法
cd backend && python -m py_compile app/api/routers/butler_v1.py \
    app/api/routers/assistant_v1.py app/api/routers/diagnosis_v1.py \
    app/api/middleware/exception_handler.py

# L1 风格
cd backend && uv run ruff check app/ tests/unit/api/

# L3 单元测试（直接相关）
cd backend && uv run pytest tests/unit/api/test_recall_daily_limit_envelope.py \
    tests/unit/api/test_exception_handler_traceback.py \
    tests/unit/services/test_recall_today.py \
    tests/unit/services/test_recall_safety_keywords.py \
    tests/unit/services/test_recall_audit_fields.py -v
```

期望：`6 + 6 + 6 + 25 + 3 = 46 passed`（具体数字按当前代码而定，至少直接相关测试全过）。

---

## 9. 类似 bug 巡检清单

修复一个后发现还有 4 个 router 同样模式，已一并处理：

| Router | 修复 |
|--------|------|
| `butler_v1.py` `generate_recall_endpoint` | ✅ 删 re-wrap |
| `butler_v1.py` `get_recall_endpoint` | ✅ 删 re-wrap |
| `assistant_v1.py` `create_session_endpoint` | ✅ 删 re-wrap |
| `assistant_v1.py` `send_message_endpoint` | ✅ 删 re-wrap（抽出 `_assert_ai_session_open` helper） |
| `diagnosis_v1.py` `create_diagnosis` 同步路径 | ✅ 删 re-wrap |
| `diagnosis_v1.py` `get_diagnosis_endpoint` | ✅ 删 re-wrap |

**剩余 router 内合法的 `raise AppBusinessError(...)`**（业务校验分支，**不是** re-wrap，**保留**）：

- `uploads_v1.py`：contentType / purpose 校验 → 400
- `butler_v1.py` `get_recall_messages_endpoint`：recall_session 不存在 → 404 / 归属不符 → 403
- `diagnosis_v1.py` `get_report_status`：诊断任务不存在 → 404

这些是**真正需要 router 层 raise** 的场景（service 没抛，需要 router 自己做断言），不能删。