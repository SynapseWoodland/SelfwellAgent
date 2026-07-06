"""Integration test for phone-login flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import db_session
from app.conf.app_config import app_config

app_config.jwt.secret_key = "x" * 32


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    fake_session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    fake_session.execute.return_value = result
    fake_session.flush = AsyncMock()

    async def _override() -> AsyncMock:
        yield fake_session

    app.dependency_overrides[db_session] = _override
    yield TestClient(app)
    app.dependency_overrides.pop(db_session, None)


def test_phone_code_endpoint(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/phone-code", json={"phone": "13800000001"})
    assert resp.status_code == 200
    assert resp.json()["data"]["sent"] is True


def test_phone_code_invalid_phone(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/phone-code", json={"phone": "12345"})
    # Pydantic 校验 422（len!=11）或业务 400
    assert resp.status_code in (400, 422)


def test_phone_login_invalid_phone(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/phone-login", json={"phone": "12345", "code": "0000"})
    assert resp.status_code in (400, 422)


def test_phone_login_wrong_code(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/phone-login", json={"phone": "13800000001", "code": "9999"})
    assert resp.status_code == 401
    body = resp.json()["detail"]
    assert body["code"] == "E_AUTH_PHONE_CODE_INVALID"
