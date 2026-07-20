"""统一错误响应 envelope（Sprint v4.1-prep · 子任务 4）。

设计动机：
- 现行 4 个 router（assistant_v1 / diagnosis_v1 / uploads_v1 / butler_v1）都用
  ``raise HTTPException(status, {"code": ..., "message_zh": ...})`` 散落抛错。
- 这导致：响应 body 形状不一致、Q-9 业务码契约层缺失、客户端必须靠 HTTP status 区分错误类型。
- 本模块提供 Pydantic envelope + 自定义 ``AppBusinessError`` + FastAPI
  ``exception_handler``，并把 ``request_id`` 从 ``request.state`` 注入。

Envelope 形状（与 ``docs/architecture/api.yaml#/components/schemas/ErrorEnvelope`` 对齐）：
::

    {
      "error": {
        "code": "E_GENERAL_RATE_LIMIT",
        "message_zh": "请求过于频繁，请稍后再试",
        "message_en": "Too many requests, please retry later",
        "request_id": "abc123...",
        "details": {"field": "contentType", "limit": 60}
      }
    }

集成方式：
1. 业务代码 ``raise AppBusinessError(code=E_X, message_zh=..., field="contentType")``
2. ``AppBusinessError`` 继承 :class:`app.core.errors.SelfwellError`，沿用现有 severity /
   http_status / render_zh() 机制
3. ``app.exception_handler:business_error_handler`` 注册到 FastAPI
   ``app.add_exception_handler(AppBusinessError, business_error_handler)`` 后，
   自动包成 envelope，并把 ``request.state.request_id`` 填入

兼容保证：
- ``to_error_response(exc)`` 已在 `app/core/errors.py` 实现，本模块**复用**它产出
  兼容 ``ErrorResponse`` 的 dict，并以 envelope 形式补 ``request_id`` / ``details``
- 不引入任何 fastapi / pydantic 之外的新依赖
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import SelfwellError, to_error_response

if TYPE_CHECKING:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from starlette.responses import Response


# ─────────────────────────────────────────────────────────────────────────────
# §一 Pydantic envelope 模型（L3 错误码契约层）
# ─────────────────────────────────────────────────────────────────────────────
class ErrorDetail(BaseModel):
    """单条业务错误的 envelope 模型（与 openapi ErrorEnvelope 对齐）。

    Attributes:
        code: 业务码（如 ``E_GENERAL_RATE_LIMIT``），与 ``app/errors/codes.py`` 1:1。
        message_zh: 中文用户可读消息；模板字符串已插值。
        message_en: 英文回退消息。
        request_id: 全链路追踪 ID（来自 ``request.state.request_id``，由
            ``TraceContextMiddleware`` 注入；缺省时回 ``"-"`` 占位）。
        details: 附加结构化上下文（如 ``field`` / ``limit`` / ``allowed``）。

    """

    model_config = ConfigDict(extra="ignore")

    code: str = Field(..., description="业务码，E_<MODULE>_<VERB_OR_NOUN>")
    message_zh: str = Field(..., description="中文用户可读消息")
    message_en: str = Field(..., description="英文用户可读消息")
    request_id: str = Field(default="-", description="全链路追踪 ID")
    details: dict[str, Any] | None = Field(default=None, description="额外上下文")


class ErrorEnvelope(BaseModel):
    """外层 envelope：``{"error": {...}}``。"""

    error: ErrorDetail


# ─────────────────────────────────────────────────────────────────────────────
# §二 AppBusinessError：router 层抛错类型（继承 SelfwellError，零迁移成本）
# ─────────────────────────────────────────────────────────────────────────────
class AppBusinessError(SelfwellError):
    """Router 层抛出的业务错误。

    与 :class:`SelfwellError` 行为一致；本类存在的目的：

    1. 区分 router 层主动抛错与服务层未捕获异常（catch-all 走另一定义）
    2. 集中 envelope integration point（FastAPI exception_handler 注册用）
    3. 为后续 v4.2+ 引入 error.code → http_status 决策表预留扩展位

    业务码层错误一律使用 ``raise AppBusinessError(code=E_X, message_zh=...)``；
    ``http_status`` 默认由 ``SelfwellError`` 子类决定（如
    ``UserInputError → 400``、``TransientError → 503``），可在构造时显式覆盖。
    """

    code: str = "E_GENERAL_INTERNAL_ERROR"
    severity: str = "USER_ERROR"
    http_status: int = 400


# ─────────────────────────────────────────────────────────────────────────────
# §三 请求 ID 提取（兜底容错）
# ─────────────────────────────────────────────────────────────────────────────
def _extract_request_id(request: Request | None) -> str:
    """从 ``request.state.request_id`` 取请求 ID；缺省回 ``"-"``。

    中间件顺序（main.py 中 add_middleware 顺序）：
        ``TraceContextMiddleware`` 在 ``ExceptionHandlerMiddleware`` 之外（LIFO 决定），
        所以所有业务异常路径下 ``request.state.request_id`` 已被注入。
    """
    if request is None:
        return "-"
    rid = getattr(request.state, "request_id", None)
    return str(rid) if rid else "-"


# ─────────────────────────────────────────────────────────────────────────────
# §四 构建 envelope dict（业务异常 → envelope）
# ─────────────────────────────────────────────────────────────────────────────
def make_envelope(
    exc: SelfwellError,
    request: Request | None = None,
) -> dict[str, Any]:
    """把 ``SelfwellError`` 子类包成 envelope dict（与 ``ErrorEnvelope.model_dump()`` 一致）。

    与 ``to_error_response()`` 唯一的差异：追加 ``request_id`` 字段。

    入参：
        exc: 业务异常（``AppBusinessError`` 或其他 ``SelfwellError`` 子类）
        request: 当前 FastAPI Request（用于读 request_id）

    出参：
        ``{"error": {code, message_zh, message_en, request_id, details}}``
    """
    base = to_error_response(exc)["error"]
    request_id = _extract_request_id(request)
    details = getattr(exc, "context", None) or None
    return {
        "error": {
            **base,
            "request_id": request_id,
            "details": details,
        },
    }


def make_error(code: str, message_zh: str, request_id: str = "-", **details: Any) -> dict[str, Any]:
    """便捷函数：手工构造一个 envelope（用于跨模块转发的错误 wrap）。

    入参：
        code: 业务码（如 ``E_GENERAL_RATE_LIMIT``）
        message_zh: 中文用户可读消息
        request_id: 全链路 ID（默认 ``"-"`` 占位）
        **details: 任意键值对附加上下文

    出参：
        ``{"error": {code, message_zh, message_en, request_id, details}}``
    """
    return {
        "error": {
            "code": code,
            "message_zh": message_zh,
            "message_en": "Server error, please retry later",
            "request_id": request_id,
            "details": dict(details) if details else None,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# §五 FastAPI exception handler（注册到 app 后自动接管）
# ─────────────────────────────────────────────────────────────────────────────
async def business_error_handler(
    request: Request,
    exc: AppBusinessError,
) -> JSONResponse:
    """FastAPI 全局 handler：``AppBusinessError`` → envelope JSON。

    注册方式（``app/main.py`` 中）：
    ::

        from app.errors.envelope import AppBusinessError, business_error_handler
        app.add_exception_handler(AppBusinessError, business_error_handler)
    """
    from fastapi.responses import JSONResponse  # noqa: PLC0415

    envelope = make_envelope(exc, request=request)
    return JSONResponse(status_code=exc.http_status, content=envelope)


# 兼容旧 import 路径（部分老代码可能引用 ``make_error`` 作为函数名）
__all__ = [
    "AppBusinessError",
    "ErrorDetail",
    "ErrorEnvelope",
    "business_error_handler",
    "make_envelope",
    "make_error",
]
