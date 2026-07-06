"""Integration test for user profile flow (FastAPI dependency override)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import db_session
from app.conf.app_config import app_config
from app.services.auth.jwt_service import issue_token

app_config.jwt.secret_key = "x" * 32


def _make_user(*, status: str = "draft") -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.unionid = "U_001"
    user.openid_mp = "M_001"
    user.openid_app = None
    user.platform = "wx_mp"
    user.device_id = None
    user.nickname = "test"
    user.avatar = ""
    user.age_range = None
    user.focus_parts = None
    user.intensity = None
    user.preferred_time = None
    user.sitting_hours = None
    user.push_token = None
    user.push_channel = None
    user.email = None
    user.phone = None
    user.status = status
    user.version = 0
    user.deleted_at = None
    user.report_cache = None
    user.report_cache_expires_at = None
    user.created_at = datetime.now(UTC)
    user.last_active_at = datetime.now(UTC)
    user.created_by = "test"
    user.created_time = datetime.now(UTC)
    user.last_updated_time = datetime.now(UTC)
    user.last_updated_by = "test"
    return user


def _fake_session_with(user: MagicMock) -> AsyncMock:
    fake_session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    fake_session.execute.return_value = result
    fake_session.flush = AsyncMock()
    return fake_session


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


def _override_with(fake_session: AsyncMock) -> None:
    from app.main import app

    async def _override() -> AsyncMock:
        yield fake_session

    app.dependency_overrides[db_session] = _override


def _clear_override() -> None:
    from app.main import app

    app.dependency_overrides.pop(db_session, None)


def test_get_me_unauthorized_no_token(client: TestClient) -> None:
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401


def test_get_me_unauthorized_bad_token(client: TestClient) -> None:
    resp = client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


def test_get_me_ok(client: TestClient) -> None:
    user = _make_user(status="active")
    fake_session = _fake_session_with(user)
    _override_with(fake_session)
    try:
        token, _ = issue_token(user_id=str(user.id))
        resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["user_id"] == str(user.id)
    finally:
        _clear_override()


def test_update_profile_promotes_to_active(client: TestClient) -> None:
    user = _make_user(status="draft")
    fake_session = _fake_session_with(user)
    _override_with(fake_session)
    try:
        token, _ = issue_token(user_id=str(user.id))
        resp = client.post(
            "/api/v1/users/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "age_range": "23-28",
                "focus_parts": ["face", "head"],
                "intensity": "适中",
                "preferred_time": "晚",
                "sitting_hours": "4-8h",
            },
        )
        assert resp.status_code == 200, resp.text
    finally:
        _clear_override()


def test_update_profile_invalid_enum(client: TestClient) -> None:
    user = _make_user(status="active")
    fake_session = _fake_session_with(user)
    _override_with(fake_session)
    try:
        token, _ = issue_token(user_id=str(user.id))
        resp = client.post(
            "/api/v1/users/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"age_range": "99+"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "E_USER_INVALID_ENUM"
    finally:
        _clear_override()
