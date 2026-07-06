"""Unit tests for ``app.services.auth.wx_login_service`` (mocked WeChatClient)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.errors import UserInputError
from app.services.auth.wx_login_service import WxLoginError, login_via_wx


@pytest.mark.asyncio
async def test_validate_platform_invalid() -> None:
    fake_session = AsyncMock()
    with pytest.raises(UserInputError):
        await login_via_wx(fake_session, code="x" * 20, client="web")


@pytest.mark.asyncio
async def test_validate_short_code() -> None:
    fake_session = AsyncMock()
    with pytest.raises(UserInputError):
        await login_via_wx(fake_session, code="short", client="wx_mp")


@pytest.mark.asyncio
async def test_login_via_wx_creates_draft_user() -> None:
    fake_session = AsyncMock()
    none_result = MagicMock()
    none_result.scalar_one_or_none.return_value = None
    fake_session.execute.return_value = none_result
    fake_session.flush = AsyncMock()

    fake_wx_resp = {"openid": "M_001", "session_key": "sk_001", "unionid": "U_001"}

    with patch("app.services.auth.wx_login_service.WeChatClient") as MockClient:  # noqa: N806
        instance = MockClient.return_value
        instance.code2session = AsyncMock(return_value=fake_wx_resp)

        _user_id, token, is_new, status_str, expires_in = await login_via_wx(
            fake_session, code="x" * 20, client="wx_mp"
        )
        assert is_new is True
        assert isinstance(token, str)
        assert expires_in > 0
        assert status_str == "draft"
        instance.code2session.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_via_wx_existing_user() -> None:
    """已存在 user 的分支。"""
    from datetime import UTC, datetime
    from uuid import uuid4

    fake_user = MagicMock()
    fake_user.id = uuid4()
    fake_user.status = "active"
    fake_user.openid_mp = "M_001"
    fake_user.openid_app = None
    fake_user.unionid = "U_001"
    fake_user.platform = "wx_mp"
    fake_user.last_active_at = datetime.now(UTC)

    fake_session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = fake_user
    fake_session.execute.return_value = result
    fake_session.flush = AsyncMock()

    fake_wx_resp = {"openid": "M_001", "session_key": "sk_001", "unionid": "U_001"}

    with patch("app.services.auth.wx_login_service.WeChatClient") as MockClient:  # noqa: N806
        instance = MockClient.return_value
        instance.code2session = AsyncMock(return_value=fake_wx_resp)
        user_id, _token, is_new, status_str, _ = await login_via_wx(
            fake_session, code="x" * 20, client="wx_mp"
        )
        assert is_new is False
        assert status_str == "active"
        assert user_id == str(fake_user.id)


@pytest.mark.asyncio
async def test_login_via_wx_wechat_error() -> None:
    """微信 code 失败场景 → 抛 WxLoginError。"""
    fake_session = AsyncMock()
    with patch("app.services.auth.wx_login_service.WeChatClient") as MockClient:  # noqa: N806
        instance = MockClient.return_value
        instance.code2session = AsyncMock(side_effect=WxLoginError("wechat err"))
        with pytest.raises(WxLoginError):
            await login_via_wx(fake_session, code="x" * 20, client="wx_mp")
