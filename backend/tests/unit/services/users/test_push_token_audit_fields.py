"""Unit tests for ``app.services.users.push_token_service.register_push_token`` audit fields。

真源：本次 audit 整改
- user.last_updated_by = user_id  （注册推送的人）
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.users.push_token_service import register_push_token


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _make_user(user_id: str = "u-push-1") -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.push_token = None
    u.push_channel = None
    return u


@pytest.mark.asyncio
async def test_register_push_token_last_updated_by_is_current_user() -> None:
    """user.last_updated_by 必须 = 当前 user_id，不能是 "push-token-register"。"""
    user_id = "u-1"
    user = _make_user(user_id=user_id)
    session = AsyncMock()
    session.execute.return_value = _scalar_result(user)
    session.flush = AsyncMock()

    await register_push_token(
        session,
        user_id=user_id,
        push_token="abc-123",  # noqa: S106  test fixture
        push_channel="wx_subscribe",
    )

    forbidden = {"push-token-register", "M1", "m1", "system", ""}
    assert user.last_updated_by not in forbidden
    assert user.last_updated_by == user_id


@pytest.mark.asyncio
async def test_register_push_token_audit_time_is_utc() -> None:
    user_id = "u-1"
    user = _make_user(user_id=user_id)
    session = AsyncMock()
    session.execute.return_value = _scalar_result(user)
    session.flush = AsyncMock()

    before = datetime.now(UTC)
    await register_push_token(
        session,
        user_id=user_id,
        push_token="abc-123",  # noqa: S106  test fixture, not a real credential
        push_channel="apns",
    )
    after = datetime.now(UTC)

    assert before <= user.last_updated_time <= after
    assert user.last_updated_time.tzinfo is not None
