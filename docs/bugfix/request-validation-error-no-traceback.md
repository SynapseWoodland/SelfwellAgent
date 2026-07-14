# Bug Fix Report: 异常响应（400/409）无日志

- **日期**: 2026-07-14
- **修复人**: AI Agent
- **影响版本**: 当前开发分支
- **关联接口**: `POST /api/v1/checkins` (及其他所有接口)

---

## 一、问题描述

**现象**：客户端请求返回 400，但终端日志只有一行 uvicorn 访问日志，无堆栈信息，无法定位是哪个字段校验失败。

```
2026-07-14 15:43:37.112 | INFO | request_id - f322e92c25e64acd | uvicorn.protocols.http.httptools_impl:send:485 - 127.0.0.1:0 - "POST /api/v1/checkins HTTP/1.1" 400
```

**期望**：400 错误应打出结构化日志，包含：
- 请求路径 `path`
- 校验失败字段详情 `errors`（`{loc, msg, type}`）
- `request_id` 用于链路追踪

---

## 二、根因分析

**FastAPI + Pydantic v2 异常处理优先级问题**：

FastAPI 的异常处理分为两层：

1. **FastAPI 内置 `RequestValidationError` 处理器**：负责 Pydantic 请求体参数校验，优先级**高于**所有自定义 `exception_handler`。
2. **自定义 `ExceptionHandlerMiddleware`**：只捕获 `SelfwellError` 子类和未处理异常。

由于 `RequestValidationError` 在 FastAPI 内部被直接响应，绕过了中间件，因此：

```
客户端 POST 400
  └─ Pydantic 校验失败 → FastAPI 内置 handler 直接返回 JSON 响应
                         ↑ 此处无日志
```

现有的 `ExceptionHandlerMiddleware` 只处理 `SelfwellError` 子类异常，`RequestValidationError` 永远不会被中间件捕获。

---

## 三、修复方案

在 `app/main.py` 中注册 FastAPI 级别的自定义异常处理器：

**文件**: `backend/app/main.py`

```python
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def _validation_error_handler(request: Request, exc: RequestValidationError) -> Response:
    errors = exc.errors()[:10]
    logger.warning(
        "request_validation_error",
        path=str(request.url.path),
        errors=errors,
        exc_type="RequestValidationError",
    )
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "E_GENERAL_VALIDATION_ERROR",
                "message_zh": "请求参数校验失败",
                "message_en": "Request validation failed",
                "request_id": getattr(request.state, "request_id", "-") or "-",
                "details": {"errors": errors},
            }
        },
    )
```

**关键设计决策**：

| 决策 | 理由 |
|------|------|
| `logger.warning` 而非 `logger.error` | 400 是客户端输入问题，不算服务端故障，WARNING 便于 Loki 按 ERROR 级别聚合真实故障 |
| 最多记录 10 条错误 | 防止异常 payload 过大撑爆日志 |
| 响应体使用统一的 `E_GENERAL_VALIDATION_ERROR` | 与现有 envelope 规范对齐 |
| 在 `app` 实例创建后立即注册 | FastAPI 按注册顺序查找 handler，早注册优先 |

---

## 四、修复后日志效果

```
2026-07-14 15:46:22.649 | WARNING | request_id - aedaebeeb3e642ec |
  backend.app.main:_validation_error_handler:143 - request_validation_error |
  path=/api/v1/checkins |
  errors=[{'loc': ('body', 'day'), 'msg': 'ensure this value is less than or equal to 21', 'type': 'less_than_equal'}]
```

---

## 五、变更文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `backend/app/main.py` | 修改 | 新增 `RequestValidationError` 异常处理器 |
| `backend/app/api/routers/checkin_v1.py` | 修改 | 微调 schema 注释（无功能变更） |

---

## 六、409 / HTTPException 二次修复（2026-07-14 17:00）

### 6.1 问题

路由层 catch `CheckinError` 后 re-raise 为纯 `HTTPException`：

```python
# checkin_v1.py
except CheckinError as exc:
    raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})
```

`HTTPException` 落入 FastAPI 内置处理器，**完全无日志**：

```
2026-07-14 17:23:15.489 | INFO | ... "POST /api/v1/checkins HTTP/1.1" 409
```

### 6.2 修复

在 `main.py` 新增 `HTTPException` 处理器：

```python
@app.exception_handler(HTTPException)
async def _http_exception_handler(request: Request, exc: HTTPException) -> Response:
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "E_GENERAL_HTTP_EXCEPTION")
        message_zh = detail.get("message_zh", "请求处理失败")
        details = {k: v for k, v in detail.items() if k not in ("code", "message_zh")}
    else:
        code = "E_GENERAL_HTTP_EXCEPTION"
        message_zh = str(detail)
        details = None

    status = exc.status_code
    log_fn = logger.error if status >= 500 else logger.warning
    log_fn("http_exception", path=str(request.url.path), status_code=status, code=code, ...)
    return JSONResponse(status_code=status, content={...})
```

**设计原则**：
- `4xx` → `logger.warning`（客户端问题）
- `5xx` → `logger.error`（服务端问题）
- 透出 router 传入的 `{"code", "message_zh"}` 字典结构

### 6.3 修复后日志效果

```
2026-07-14 17:30:00.000 | WARNING | request_id - abc123 | backend.app.main:_http_exception_handler - http_exception | path=/api/v1/checkins | status_code=409 | code=E_CHECKIN_DUPLICATE
```

---

## 七、测试验证

### 7.1 400 验证（RequestValidationError）

1. 发送参数校验失败的请求（如 `day > 21`）到任意接口
2. 检查终端日志是否出现 `request_validation_error` + `errors` 字段
3. 检查响应体是否包含 `E_GENERAL_VALIDATION_ERROR` 错误码

### 7.2 409 验证（HTTPException）

1. 重复打卡触发 409
2. 检查终端日志是否出现 `http_exception` + `status_code=409` + `code` 字段
