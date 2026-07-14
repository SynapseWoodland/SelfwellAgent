"""回归测试：RecallDailyLimitError → envelope 必须保留 ``message_zh``。

背景：v0.x router 曾经对 ``RecallError`` / ``RecallDailyLimitError`` 做 re-wrap
为 ``AppBusinessError``，但 ``SelfwellError.__init__`` 不接受 ``message_zh=`` /
``message_en=`` 这两个命名参数（会被 ``**context`` 吞掉），结果 envelope 返回了
``AppBusinessError`` 类属性默认值 ``"服务端错误，请稍后重试"`` 而不是 service
层定义的 ``"今日已生成过一次主动回忆"``，HTTP 状态码也跑偏到默认 400 / 400。

修法（PR "fix: drop XxxError -> AppBusinessError re-wrap in routers"）：
router 不再做 re-wrap，让 ``SelfwellError`` 子类直接冒泡到
``ExceptionHandlerMiddleware``，由 ``make_envelope()`` 渲染。本测试断言
修法 D（删 re-wrap）+ 修法 C（SelfwellError 分支 logger.warning 而非 exception）
后 envelope 行为正确。

真源：``docs/spec/SPEC-M8-recall.md`` §3.6 每日 ≤ 1 次；
``backend/app/services/recall_service.py`` RecallDailyLimitError 定义。
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.middleware.exception_handler import ExceptionHandlerMiddleware
from app.services.recall_service import RecallDailyLimitError


@pytest.mark.asyncio
async def test_recall_daily_limit_envelope_preserves_message_zh() -> None:
    """回归：E_RECALL_DAILY_LIMIT envelope.message_zh 不能被 router re-wrap 吞掉。

    触发场景：service 抛 ``RecallDailyLimitError()`` → router 不能再 ``raise
    AppBusinessError(...)`` 包装（之前会把 ``message_zh=`` 当成 ``**context``
    吞掉，结果 envelope 返回 "服务端错误，请稍后重试" 而非 service 定义的
    "今日已生成过一次主动回忆"）。
    """
    app = FastAPI(title="recall-daily-limit-regression")
    from app.api.routers.butler_v1 import butler_router

    app.include_router(butler_router, prefix="/api/v1")
    app.add_middleware(ExceptionHandlerMiddleware)

    # 跳过 auth：直接 override current_user_id
    from app.api.deps import current_user_id

    app.dependency_overrides[current_user_id] = lambda: "00000000-0000-0000-0000-000000000099"

    async def _raise_daily_limit(*_a: Any, **_kw: Any) -> dict[str, Any]:
        raise RecallDailyLimitError()

    with patch("app.api.routers.butler_v1.generate_recall", side_effect=_raise_daily_limit):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/butler/recall", json={})

    # HTTP 状态码：service 定义 http_status=429
    assert resp.status_code == 429, f"expected 429, got {resp.status_code}: {resp.text!r}"
    body = resp.json()

    # envelope 形状必须是 {"error": {...}}
    assert "error" in body, f"missing 'error' key, got {body!r}"
    assert "detail" not in body, f"legacy FastAPI envelope detected: {body!r}"

    err = body["error"]
    # code / http_status 来自 RecallDailyLimitError 类属性
    assert err["code"] == "E_RECALL_DAILY_LIMIT", (
        f"expected E_RECALL_DAILY_LIMIT, got {err['code']!r}"
    )

    # ★ 核心断言：message_zh 必须是 service 层定义的中文文案，**不能**是默认值
    assert err["message_zh"] == "今日已生成过一次主动回忆", (
        f"message_zh 错误（被 re-wrap 吞了 service 文案）：{err['message_zh']!r}. "
        "不要在 router 内把 RecallError 再包成 AppBusinessError。"
    )
    assert err["message_en"] == "Daily recall limit reached", (
        f"message_en 错误：{err['message_en']!r}"
    )


@pytest.mark.asyncio
async def test_recall_daily_limit_logs_warning_not_exception() -> None:
    """修法 C：业务异常 ``SelfwellError`` 走 ``logger.warning``，**不**打 traceback。"""
    from app.api.middleware.exception_handler import ExceptionHandlerMiddleware

    middleware = ExceptionHandlerMiddleware(app=AsyncMock())
    exc = RecallDailyLimitError()

    request = AsyncMock()
    request.url.path = "/api/v1/butler/recall"
    request.state.request_id = "test-rid"
    request.state.trace_id = "test-tid"

    async def _call_next(_request):
        raise exc

    with patch("app.api.middleware.exception_handler.logger") as mock_log:
        await middleware.dispatch(request, _call_next)

        # 业务异常：warning 被调用，且 code 字段正确
        mock_log.warning.assert_called_once()
        call_kwargs = mock_log.warning.call_args.kwargs
        assert call_kwargs["code"] == "E_RECALL_DAILY_LIMIT"
        assert call_kwargs["http_status"] == 429
        assert call_kwargs["severity"] == "USER_ERROR"

        # 反向断言：traceback 路径绝不能被触发
        mock_log.exception.assert_not_called()
        mock_log.error.assert_not_called()
