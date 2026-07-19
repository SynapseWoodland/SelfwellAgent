"""验证 ExceptionHandlerMiddleware 捕获异常时的日志级别策略。

真源：docs/api/openapi.yaml + error-codes.md + RULES.md §5 +
coding-standards.mdc §九-日志（业务异常不打 traceback，未预期异常打 traceback）。

业务异常（``SelfwellError``）一律用结构化字段 ``logger.warning``：每条 4xx
限流 / 状态冲突都打 traceback 会污染 Loki 索引；调试时按 ``code / severity / path``
聚合即可。``unhandled_exception``（500 兜底）才是真正需要 traceback 的场景。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.api.middleware.exception_handler import ExceptionHandlerMiddleware
from app.core.errors import PermanentError, UserInputError


def _raise(exc: Exception):
    """构造一个会抛异常的 call_next。"""

    async def _call_next(_request):
        raise exc

    return _call_next


def _fake_request() -> AsyncMock:
    request = AsyncMock()
    request.url.path = "/api/v1/test"
    request.state.request_id = "test-rid-001"
    request.state.trace_id = "test-tid-001"
    return request


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc_class,code",
    [
        (UserInputError, "E_USER_INVALID_INPUT"),
        (PermanentError, "E_GENERAL_INVALID_REQUEST"),
    ],
)
async def test_selfwell_error_logs_as_warning(exc_class: type, code: str) -> None:
    """SelfwellError 子类走 logger.warning 而非 logger.exception。

    反向断言：``logger.exception`` / ``logger.error`` 都不能被调用 —— 否则说明
    仍然是 traceback 全栈输出（Loki 噪音 + 日志条目膨胀）。
    """
    middleware = ExceptionHandlerMiddleware(app=AsyncMock())
    exc = exc_class("test", code=code)

    with patch("app.api.middleware.exception_handler.logger") as mock_log:
        await middleware.dispatch(_fake_request(), _raise(exc))

        mock_log.warning.assert_called_once()
        call_kwargs = mock_log.warning.call_args.kwargs
        assert call_kwargs["code"] == code
        assert call_kwargs["exc_type"] == exc_class.__name__
        assert call_kwargs["path"] == "/api/v1/test"

        mock_log.exception.assert_not_called()
        mock_log.error.assert_not_called()


@pytest.mark.asyncio
async def test_unhandled_exception_logs_with_traceback() -> None:
    """未预期 Exception 走 logger.exception 并返回 E_GENERAL_INTERNAL_ERROR。"""
    middleware = ExceptionHandlerMiddleware(app=AsyncMock())

    with patch("app.api.middleware.exception_handler.logger") as mock_log:
        response = await middleware.dispatch(
            _fake_request(),
            _raise(ValueError("boom")),
        )

        mock_log.exception.assert_called_once()
        assert response.status_code == 500
        body = response.body.decode()
        assert "E_GENERAL_INTERNAL_ERROR" in body
        # 关键：响应体绝对不能含 traceback 字样
        assert "Traceback" not in body
        assert "ValueError" not in body


@pytest.mark.asyncio
async def test_response_body_never_contains_traceback() -> None:
    """CWE-209 防护：任何 SelfwellError 响应都不应含堆栈字符串。"""
    middleware = ExceptionHandlerMiddleware(app=AsyncMock())
    exc = UserInputError("内部细节：/etc/passwd 拒绝访问", code="E_USER_INVALID_INPUT")

    response = await middleware.dispatch(_fake_request(), _raise(exc))

    body = response.body.decode()
    assert "Traceback" not in body
    assert "/etc/passwd" not in body  # 内部路径不外泄
    assert exc.code in body  # 业务码正常返回
