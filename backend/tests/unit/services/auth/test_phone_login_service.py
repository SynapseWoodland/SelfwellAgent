"""Unit tests for ``app.services.auth.phone_login_service``."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.auth.phone_login_service import (
    SMS_SEND_RATE_LIMIT,
    PhoneLoginError,
    _dev_sms_code,
    login_via_phone,
    request_sms_code,
)


def test_dev_sms_code_default() -> None:
    os.environ.pop("DEV_SMS_CODE", None)
    assert _dev_sms_code() == "0000"


@pytest.mark.asyncio
async def test_request_sms_code_ok() -> None:
    await request_sms_code("13800000001", recent_send_count=0)


@pytest.mark.asyncio
async def test_request_sms_code_invalid_phone() -> None:
    with pytest.raises(Exception):  # noqa: B017  test 通用兜底
        await request_sms_code("12345", recent_send_count=0)


@pytest.mark.asyncio
async def test_request_sms_code_rate_limited() -> None:
    with pytest.raises(PhoneLoginError) as exc_info:
        await request_sms_code("13800000001", recent_send_count=SMS_SEND_RATE_LIMIT)
    assert exc_info.value.http_status == 429


@pytest.mark.asyncio
async def test_login_via_phone_invalid_phone() -> None:
    with pytest.raises(Exception):  # noqa: B017  test 通用兜底
        await login_via_phone(AsyncMock(), phone="", code="0000")


@pytest.mark.asyncio
async def test_login_via_phone_wrong_code() -> None:
    with pytest.raises(PhoneLoginError):
        await login_via_phone(AsyncMock(), phone="13800000001", code="9999")


@pytest.mark.asyncio
async def test_login_via_phone_expired_code() -> None:
    expired = datetime.now(UTC) - timedelta(minutes=10)
    with pytest.raises(PhoneLoginError) as exc_info:
        await login_via_phone(AsyncMock(), phone="13800000001", code="0000", expires_at=expired)
    assert "expired" in exc_info.value.code.lower() or "EXPIRED" in exc_info.value.code


@pytest.mark.asyncio
async def test_login_via_phone_new_user() -> None:
    fake_session = AsyncMock()
    none_result = MagicMock()
    none_result.scalar_one_or_none.return_value = None
    fake_session.execute.return_value = none_result
    fake_session.flush = AsyncMock()

    _user_id, token, is_new, status_str, expires_in = await login_via_phone(
        fake_session, phone="13800000001", code="0000"
    )
    assert is_new is True
    assert isinstance(token, str)
    assert expires_in > 0
    assert status_str == "draft"
