"""Integration test for wx-login flow (FastAPI dependency override)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import db_session
from app.conf.app_config import app_config

app_config.jwt.secret_key = "x" * 32


def _make_session_for_new_user() -> AsyncMock:
    fake_session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    fake_session.execute.return_value = result
    fake_session.flush = AsyncMock()
    return fake_session


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    fake_session = _make_session_for_new_user()

    async def _override() -> AsyncMock:
        yield fake_session

    app.dependency_overrides[db_session] = _override
    yield TestClient(app)
    app.dependency_overrides.pop(db_session, None)


def test_wx_login_creates_draft(client: TestClient) -> None:
    with patch("app.services.auth.wx_login_service.WeChatClient") as MockClient:  # noqa: N806  test convention
        instance = MockClient.return_value
        instance.code2session = AsyncMock(
            return_value={"openid": "M_TEST_001", "session_key": "sk"}
        )
        resp = client.post(
            "/api/v1/auth/wx-login",
            json={"code": "x" * 20, "client": "wx_mp"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["is_new_user"] is True
        assert data["user_status"] == "draft"
        assert len(data["access_token"]) > 20
        instance.code2session.assert_awaited_once()


def test_wx_login_invalid_client(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/wx-login",
        json={"code": "x" * 20, "client": "web"},
    )
    # Pydantic 校验 422（client 字段类型不匹配）或业务 400
    # 我们的 service 会校验 client 是否在合法枚举内 → 抛 UserInputError → 400
    assert resp.status_code in (400, 422)
    body = resp.json()
    # 422 时 detail 是 list；400 时 detail.code
    if resp.status_code == 400:
        assert body["detail"]["code"] == "E_USER_INVALID_INPUT"


def test_wx_login_short_code(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/wx-login",
        json={"code": "short", "client": "wx_mp"},
    )
    assert resp.status_code in (400, 422)
