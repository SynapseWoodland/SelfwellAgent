"""Unit tests for ``app.api.routers.auth.wx_login`` 路由层。

真源：``backend/app/api/routers/auth.py``（重写后委托给
``app.services.auth.wx_login_service.login_via_wx``）。

本测试覆盖路由层的四个核心契约：
1. Happy path：成功调 service → 返回 JWT + user_id + is_new + status。
2. 异常映射：service 抛 WxLoginError → HTTP status 来自 ``exc.http_status``。
3. 异常映射：service 抛 UserInputError → 透传 ``exc.http_status`` (400/422)。
4. 兜底：service 抛非 SelfwellError → 500 + E_GENERAL_INTERNAL_ERROR。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.errors import UserInputError
from app.errors.codes import E_GENERAL_INTERNAL_ERROR
from app.services.auth.wx_login_service import WxLoginError, login_via_wx


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _mock_service_return(user_id: str = "u-1", token: str = "jwt.tok.en"):  # noqa: S107
    """构造一个 fake service 返回值（对应 login_via_wx 的 5 元 tuple）。"""
    return (user_id, token, True, "draft", 7200)


@pytest.fixture
def mock_login_via_wx() -> AsyncMock:
    """用 patch 替换 service.login_via_wx，避免触发真实 DB / WeChat 调用。"""
    with patch("app.api.routers.auth.login_via_wx") as fn:
        yield fn


# ─────────────────────────────────────────────────────────────────────────────
# 1. Happy path
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_wx_login_happy_path_returns_response_shape(
    mock_login_via_wx: AsyncMock,
) -> None:
    """Service 成功 → 路由返回完整 WxLoginResponse（4 字段）。"""
    mock_login_via_wx.return_value = _mock_service_return()

    from app.api.routers.auth import WxLoginRequest, wx_login

    result = await wx_login(WxLoginRequest(code="x" * 20), session=AsyncMock())
    assert result.access_token == "jwt.tok.en"  # noqa: S105
    assert result.user_id == "u-1"
    assert result.is_new_user is True
    assert result.user_status == "draft"


# ─────────────────────────────────────────────────────────────────────────────
# 2. WxLoginError → HTTP status 来自 exc.http_status
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("http_status", "err_code"),
    [(401, "E_AUTH_CODE_INVALID"), (502, "E_GENERAL_INTERNAL_ERROR"), (504, "E_AUTH_CODE_INVALID")],
)
async def test_wx_login_wxerror_maps_to_exc_http_status(
    mock_login_via_wx: AsyncMock,
    http_status: int,
    err_code: str,
) -> None:
    """微信侧错误（401/502/504）→ HTTP status 透传 + 错误码透传。"""
    from fastapi import HTTPException

    mock_login_via_wx.side_effect = WxLoginError(
        "wx failed", code=err_code, http_status=http_status
    )

    from app.api.routers.auth import WxLoginRequest, wx_login

    with pytest.raises(HTTPException) as exc_info:
        await wx_login(WxLoginRequest(code="x" * 20), session=AsyncMock())
    assert exc_info.value.status_code == http_status
    assert exc_info.value.detail["code"] == err_code


# ─────────────────────────────────────────────────────────────────────────────
# 3. UserInputError → HTTP status 来自 exc.http_status (400/422)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_wx_login_user_input_error_maps_400(mock_login_via_wx: AsyncMock) -> None:
    """Service 抛 UserInputError（400）→ 路由透传 status_code。

    注：UserInputError 类当前没有显式 ``code`` 类属性（继承 SelfwellError 默认
    ``E_GENERAL_INTERNAL_ERROR``），是项目预先存在的小问题，与本次 audit 整改
    无关。本测试只验证路由层的契约：``http_status`` 透传。
    """
    from fastapi import HTTPException

    mock_login_via_wx.side_effect = UserInputError(
        "code too short", field="code", http_status=400
    )

    from app.api.routers.auth import WxLoginRequest, wx_login

    with pytest.raises(HTTPException) as exc_info:
        await wx_login(WxLoginRequest(code="x" * 20), session=AsyncMock())
    # 核心契约：status_code 透传
    assert exc_info.value.status_code == 400
    assert "code" in exc_info.value.detail
    assert "message_zh" in exc_info.value.detail


# ─────────────────────────────────────────────────────────────────────────────
# 4. 兜底：unexpected Exception → 500 + E_GENERAL_INTERNAL_ERROR
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_wx_login_unexpected_error_returns_500(mock_login_via_wx: AsyncMock) -> None:
    """Service 抛非 SelfwellError（如 RuntimeError）→ 路由兜底为 500。"""
    from fastapi import HTTPException

    mock_login_via_wx.side_effect = RuntimeError("boom")

    from app.api.routers.auth import WxLoginRequest, wx_login

    with pytest.raises(HTTPException) as exc_info:
        await wx_login(WxLoginRequest(code="x" * 20), session=AsyncMock())
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail["code"] == E_GENERAL_INTERNAL_ERROR


# ─────────────────────────────────────────────────────────────────────────────
# 5. 路由已不再自己建 User（硬编码 _upsert_user_by_openid_mp 已删）
# ─────────────────────────────────────────────────────────────────────────────
def test_router_does_not_define_upsert_helper() -> None:
    """回归保护：routers/auth.py 不应再有私有 User 创建 helper。"""
    import app.api.routers.auth as router_module

    assert not hasattr(router_module, "_upsert_user_by_openid_mp"), (
        "routers/auth.py 不应再有 _upsert_user_by_openid_mp，"
        "所有 User 创建逻辑必须走 service 层"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. 路由层不再 import WeChatClient（避免两套并行实现漂移）
# ─────────────────────────────────────────────────────────────────────────────
def test_router_does_not_instantiate_wechat_client() -> None:
    """回归保护：routers/auth.py 不应再 import WeChatClient。"""
    import app.api.routers.auth as router_module

    # 路由层源码里不允许出现 WeChatClient 字面量
    src_path = router_module.__file__
    assert src_path is not None
    with open(src_path, encoding="utf-8") as f:
        src = f.read()
    assert "WeChatClient" not in src, (
        "routers/auth.py 不应再 import 或实例化 WeChatClient"
    )


# 防止被 lint 误删未使用的 import（login_via_wx / WxLoginError 用于 mock fixture）
__all__ = ["WxLoginError", "login_via_wx"]
