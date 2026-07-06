"""异常处理中间件（Sprint 0 骨架）。

真源：``docs/api/openapi.yaml#/components/schemas/ErrorResponse`` +
``docs/api/error-codes.md`` + ``app/core/errors.to_error_response()``。

职责：
1. 捕获所有 ``SelfwellError`` 子类 → 返回对应 ``error.code / http_status`` + body
2. 兜底捕获其它异常 → E_GENERAL_INTERNAL_ERROR + 500
3. 5xx 响应必须带 ``X-Request-ID`` / ``traceparent`` 头（TraceContextMiddleware 已注入）
4. 日志用 ``logger.exception`` 自动抓 traceback
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import SelfwellError, to_error_response
from app.core.log import logger

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
            logger.warning(
                "selfwell_error",
                code=exc.code,
                http_status=exc.http_status,
                severity=exc.severity,
                path=request.url.path,
            )
            return JSONResponse(
                status_code=exc.http_status,
                content=to_error_response(exc),
            )
        except Exception:
            logger.exception(
                "unhandled_exception",
                path=request.url.path,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "E_GENERAL_INTERNAL_ERROR",
                        "message_zh": "服务端错误，请稍后重试",
                        "message_en": "Server error, please retry later",
                    }
                },
            )


__all__ = ["ExceptionHandlerMiddleware"]
