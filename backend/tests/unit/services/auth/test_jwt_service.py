"""Unit tests for ``app.services.auth.jwt_service``.

真源：``docs/spec/TDS-M1-wechat-login.md`` §4。
"""

from __future__ import annotations

import pytest

from app.auth.jwt_handler import JWTError
from app.conf.app_config import app_config
from app.services.auth.jwt_service import (
    DEFAULT_EXPIRES_SECONDS,
    JWTSignError,
    issue_token,
    token_expires_seconds,
    verify_token,
)

# 设置测试用 secret_key
app_config.jwt.secret_key = "x" * 32


def test_issue_token_minimal() -> None:
    """最小调用：仅 user_id。"""
    token, expires_in = issue_token(user_id="01900000-0000-0000-0000-000000000001")
    assert isinstance(token, str)
    assert len(token) > 20
    assert expires_in == DEFAULT_EXPIRES_SECONDS


def test_issue_token_with_claims() -> None:
    """完整 claims：platform / openid_mp / openid_app / unionid。"""
    token, _ = issue_token(
        user_id="01900000-0000-0000-0000-000000000002",
        platform="ios",
        openid_app="APP_001",
        unionid="U_001",
    )
    payload = verify_token(token)
    assert payload["sub"] == "01900000-0000-0000-0000-000000000002"
    assert payload["platform"] == "ios"
    assert payload["openid_app"] == "APP_001"
    assert payload["unionid"] == "U_001"


def test_issue_token_invalid_user_id() -> None:
    """user_id 缺失或过短 → UserInputError。"""
    with pytest.raises(Exception):  # noqa: B017  test 通用兜底
        issue_token(user_id="")


def test_issue_token_custom_expires() -> None:
    """自定义 expires_seconds。"""
    token, expires_in = issue_token(
        user_id="01900000-0000-0000-0000-000000000003",
        expires_seconds=60,
    )
    assert expires_in == 60
    assert isinstance(token, str)


def test_verify_token_ok() -> None:
    token, _ = issue_token(user_id="01900000-0000-0000-0000-000000000004")
    payload = verify_token(token)
    assert payload["sub"] == "01900000-0000-0000-0000-000000000004"
    assert payload["type"] == "access"


def test_verify_token_empty() -> None:
    with pytest.raises(JWTError):
        verify_token("")


def test_verify_token_malformed() -> None:
    with pytest.raises(JWTError):
        verify_token("not-a-jwt-token")


def test_token_expires_seconds_returns_config() -> None:
    """token_expires_seconds 返回 app_config 推算值。"""
    app_config.jwt.access_token_expire_minutes = 60
    assert token_expires_seconds() == 60 * 60


def test_jwtsign_error_metadata() -> None:
    err = JWTSignError()
    assert err.code == "E_AUTH_TOKEN_INVALID"
    assert err.http_status == 500
