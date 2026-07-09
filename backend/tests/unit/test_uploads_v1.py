"""Unit tests for ``/api/v1/uploads/presign`` endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.errors.codes import (
    E_UPLOAD_INVALID_CONTENT_TYPE,
    E_UPLOAD_INVALID_PURPOSE,
)


@pytest.fixture
def mock_jwt_user():
    """注入 current_user_id，让所有路由通过鉴权。

    实现：用 ``app.dependency_overrides`` 替换 dep，避免 AsyncMock 的
    ``(*args, **kwargs)`` 签名被 FastAPI 解析为 query 参数（issue #3331）。
    """
    from app.api.deps import current_user_id
    from app.main import app as fastapi_app

    async def fake_user_id() -> str:
        return "u-test"

    fastapi_app.dependency_overrides[current_user_id] = fake_user_id
    yield "u-test"
    fastapi_app.dependency_overrides.pop(current_user_id, None)


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.presigned_url = AsyncMock(return_value="http://localhost:9000/selfwell/k?X-Amz=x")
    with patch("app.api.routers.uploads_v1.get_storage", return_value=storage):
        yield storage


def _make_client() -> TestClient:
    from app.main import app

    return TestClient(app)


def test_presign_success_jpg(mock_jwt_user, mock_storage) -> None:
    client = _make_client()
    resp = client.post(
        "/api/v1/uploads/presign",
        json={"contentType": "image/jpeg", "purpose": "diagnosis"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["upload_url"].startswith("http://")
    assert data["object_key"].startswith(f"diagnosis/{mock_jwt_user}/")
    assert data["object_key"].endswith(".jpg")
    assert data["expires_in"] == 3600
    assert data["cdn_url"] == data["upload_url"]
    mock_storage.presigned_url.assert_awaited_once()


def test_presign_success_png(mock_jwt_user, mock_storage) -> None:
    client = _make_client()
    resp = client.post(
        "/api/v1/uploads/presign",
        json={"contentType": "image/png", "purpose": "feedback"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["object_key"].endswith(".png")


def test_presign_success_webp(mock_jwt_user, mock_storage) -> None:
    client = _make_client()
    resp = client.post(
        "/api/v1/uploads/presign",
        json={"contentType": "image/webp", "purpose": "diagnosis"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
    assert resp.json()["object_key"].endswith(".webp")


def test_presign_invalid_content_type(mock_jwt_user, mock_storage) -> None:
    client = _make_client()
    resp = client.post(
        "/api/v1/uploads/presign",
        json={"contentType": "application/pdf", "purpose": "diagnosis"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == E_UPLOAD_INVALID_CONTENT_TYPE


def test_presign_invalid_purpose(mock_jwt_user, mock_storage) -> None:
    client = _make_client()
    resp = client.post(
        "/api/v1/uploads/presign",
        json={"contentType": "image/jpeg", "purpose": "unknown"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == E_UPLOAD_INVALID_PURPOSE


def test_presign_missing_field(mock_jwt_user, mock_storage) -> None:
    client = _make_client()
    resp = client.post(
        "/api/v1/uploads/presign",
        json={"purpose": "diagnosis"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 422  # pydantic validation


def test_presign_object_key_unique_per_request(mock_jwt_user, mock_storage) -> None:
    """两次请求 object_key 应不同（uuid4）。"""
    client = _make_client()
    r1 = client.post(
        "/api/v1/uploads/presign",
        json={"contentType": "image/jpeg", "purpose": "diagnosis"},
        headers={"Authorization": "Bearer fake"},
    ).json()
    r2 = client.post(
        "/api/v1/uploads/presign",
        json={"contentType": "image/jpeg", "purpose": "diagnosis"},
        headers={"Authorization": "Bearer fake"},
    ).json()
    assert r1["object_key"] != r2["object_key"]
