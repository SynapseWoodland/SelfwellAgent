"""Unit tests for ``app.services.users.push_token_service``."""

from __future__ import annotations

import pytest

from app.services.users.push_token_service import (
    PushTokenError,
    default_push_channel_for,
)


def test_default_push_channel_for_known_platforms() -> None:
    assert default_push_channel_for("wx_mp") == "wx_subscribe"
    assert default_push_channel_for("ios") == "apns"
    assert default_push_channel_for("android") == "fcm"
    assert default_push_channel_for("harmony") == "hms"


def test_default_push_channel_for_unknown_falls_back_to_email() -> None:
    assert default_push_channel_for("unknown_platform") == "email"


@pytest.mark.asyncio
async def test_register_push_token_invalid_channel() -> None:
    """非法 push_channel 抛 PushTokenError。"""
    from unittest.mock import AsyncMock

    from app.services.users.push_token_service import register_push_token

    fake_session = AsyncMock()
    with pytest.raises(PushTokenError):
        await register_push_token(
            fake_session,
            user_id="01900000-0000-0000-0000-000000000001",
            push_token="abc",  # noqa: S106  test fixture value
            push_channel="sms",
        )
    fake_session.execute.assert_not_called()
