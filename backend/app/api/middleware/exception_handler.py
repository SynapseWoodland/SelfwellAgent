"""异常处理中间件（Sprint 0 骨架 + v4.1-prep envelope 集成）。

真源：``docs/api/openapi.yaml#/components/schemas/ErrorResponse`` +
``docs/api/error-codes.md`` + ``app/errors/envelope.make_envelope()``。

职责：
1. 捕获所有 ``SelfwellError`` 子类 → envelope 响应 + ``error.code / http_status``
2. 兜底捕获其它异常 → E_GENERAL_INTERNAL_ERROR + 500
3. 5xx 响应必须带 ``X-Request-ID`` / ``traceparent`` 头（TraceContextMiddleware 已注入）
4. 业务异常 (``SelfwellError``) → ``logger.warning``（不打 traceback，避免日志噪音）；
   未预期异常 → ``logger.exception``（自动抓 traceback，便于定位）
5. v4.1-prep：envelope 形态 ``{"error": {code, message_zh, message_en, request_id, details}}``
   取代旧 ``to_error_response()`` 形态；``error.code / message_zh / message_en`` 字段保持不变
   以兼容现有 78 个测试。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import SelfwellError
from app.core.log import logger
from app.errors.envelope import make_envelope

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request
    from starlette.responses import Response


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """统一异常 → 错误响应。

    Usage:
        >>> app.add_middleware(ExceptionHandlerMiddleware)
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        from fastapi.responses import JSONResponse

        try:
            return await call_next(request)  # type: ignore[operator, no-any-return]
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
        except Exception as exc:
            logger.exception(
                "unhandled_exception",
                path=request.url.path,
                exc_type=type(exc).__name__,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "E_GENERAL_INTERNAL_ERROR",
                        "message_zh": "服务端错误，请稍后重试",
                        "message_en": "Server error, please retry later",
                        "request_id": getattr(request.state, "request_id", "-") or "-",
                        "details": None,
                    }
                },
            )


__all__ = ["ExceptionHandlerMiddleware"]
