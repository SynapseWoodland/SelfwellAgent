"""Trace 上下文中间件（Sprint 0 骨架）。

真源：``docs/api/openapi.yaml`` + ``docs/api/error-codes.md`` §十 §5
（5xx 响应必须带 ``traceparent`` / ``X-Request-ID`` 头）

职责：
1. 入口：读 ``X-Request-ID`` / ``traceparent`` 头，若缺则生成（uuid4 fallback）
2. 中间件：把 ``trace_id`` / ``request_id`` 注入 ``request.state`` 供业务/日志层读取
3. 出口：把 ``X-Request-ID`` / ``traceparent`` 头写回 response
4. 与 loguru 联动：``logger.bind(trace_id=..., request_id=...)`` 由 ``ContextualFilter`` 实现

不依赖 OpenTelemetry SDK（保持 Sprint 0 体积小）；如未来引入 OTLP，
只需把 ``ContextVar`` 替换为 ``otel_context``。
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request
    from starlette.responses import Response

from starlette.middleware.base import BaseHTTPMiddleware

# ─────────────────────────────────────────────────────────────────────────────
# §一 ContextVar（让 trace_id 在 async 链路中安全地传播）
# ─────────────────────────────────────────────────────────────────────────────
trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def current_trace_id() -> str | None:
    """读取当前 trace context 的 ``trace_id``；优先 ``traceparent`` 链路。"""
    return trace_id_var.get()


def current_request_id() -> str | None:
    return request_id_var.get()


# ─────────────────────────────────────────────────────────────────────────────
# §二 W3C traceparent 解析（W3C Trace Context 标准）
# https://www.w3.org/TR/trace-context/
# 格式：``00-{trace_id_32hex}-{span_id_16hex}-{flags_2hex}``
# ─────────────────────────────────────────────────────────────────────────────
def _parse_traceparent(value: str) -> str | None:
    parts = value.strip().split("-")
    if len(parts) != 4 or parts[0] != "00":
        return None
    trace_id_hex = parts[1]
    if len(trace_id_hex) != 32 or not all(c in "0123456789abcdef" for c in trace_id_hex):
        return None
    return trace_id_hex


def _generate_trace_id() -> str:
    """生成 32 字符小写 hex trace id；与 W3C spec 对齐（无需 16-char span_id）。"""
    return uuid.uuid4().hex


# ─────────────────────────────────────────────────────────────────────────────
# §三 FastAPI / Starlette 中间件
# ─────────────────────────────────────────────────────────────────────────────
class TraceContextMiddleware(BaseHTTPMiddleware):
    """Inject / propagate trace_id across the request lifecycle.

    Usage in FastAPI:

    >>> from fastapi import FastAPI
    >>> app = FastAPI()
    >>> app.add_middleware(TraceContextMiddleware)
    """

    HEADER_TRACE_ID = "X-Trace-Id"
    HEADER_REQUEST_ID = "X-Request-ID"
    HEADER_TRACEPARENT = "traceparent"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # 1. 入口：解析或生成 trace / request id
        # 优先顺序：traceparent(W3C) > X-Trace-Id(自定义) > generate
        traceparent = request.headers.get(self.HEADER_TRACEPARENT, "")
        x_trace_id_inbound = request.headers.get(self.HEADER_TRACE_ID)
        parsed_trace_id = _parse_traceparent(traceparent) if traceparent else None
        trace_id = parsed_trace_id or x_trace_id_inbound or _generate_trace_id()
        request_id = request.headers.get(self.HEADER_REQUEST_ID) or _generate_trace_id()[:16]

        # 2. ContextVar 注入（async 链路安全）
        trace_id_var.set(trace_id)
        request_id_var.set(request_id)
        request.state.trace_id = trace_id
        request.state.request_id = request_id

        # 3. 业务执行
        response = await call_next(request)

        # 4. 出口：写回 trace headers（按 inbound 透传 + 新生成兜底）
        response.headers[self.HEADER_TRACE_ID] = x_trace_id_inbound or trace_id
        response.headers[self.HEADER_REQUEST_ID] = request_id
        if not response.headers.get(self.HEADER_TRACEPARENT):
            response.headers[self.HEADER_TRACEPARENT] = (
                f"00-{trace_id}-{request_id.ljust(16, '0')[:16]}-01"
            )

        return response


__all__ = [
    "TraceContextMiddleware",
    "current_request_id",
    "current_trace_id",
    "request_id_var",
    "trace_id_var",
]
