"""Vision photos URL helper 单测（V5.2.1-PR2 T14）。

V5.2.1 §4.2.2 E2-4：photos URL helper 单测全 PASS。
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services._photo_urls import build_photo_urls


@pytest.mark.asyncio
async def test_build_photo_urls_passthrough_http_url() -> None:
    """公网 https URL 直接 passthrough，不调 storage."""
    photos: list[dict[str, Any]] = [{"url": "https://example.com/photo.jpg"}]
    storage = MagicMock()
    storage.presigned_get_url = AsyncMock()
    with patch("app.storage.factory.get_storage", return_value=storage):
        result = await build_photo_urls(photos)
    assert result == ["https://example.com/photo.jpg"]
    storage.presigned_get_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_build_photo_urls_passthrough_data_url() -> None:
    """data:image/ URL 直接 passthrough（base64 内嵌图）."""
    photos: list[dict[str, Any]] = [{"url": "data:image/png;base64,xxx"}]
    storage = MagicMock()
    storage.presigned_get_url = AsyncMock()
    with patch("app.storage.factory.get_storage", return_value=storage):
        result = await build_photo_urls(photos)
    assert result == ["data:image/png;base64,xxx"]
    storage.presigned_get_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_build_photo_urls_presigned_for_object_key() -> None:
    """object_key 场景 → 调 storage.presigned_get_url 返回公网预签名 URL."""
    photos: list[dict[str, Any]] = [{"object_key": "uploads/face.jpg", "body_part": "face"}]
    storage = MagicMock()
    storage.presigned_get_url = AsyncMock(return_value="https://minio.example.com/uploads/face.jpg?signed=abc")
    with patch("app.storage.factory.get_storage", return_value=storage):
        result = await build_photo_urls(photos)
    assert result == ["https://minio.example.com/uploads/face.jpg?signed=abc"]
    storage.presigned_get_url.assert_awaited_once()
    args, _ = storage.presigned_get_url.call_args
    assert args[0] == "uploads/face.jpg"


@pytest.mark.asyncio
async def test_build_photo_urls_fallback_on_storage_error() -> None:
    """storage.presigned_get_url 抛异常 → 构造 MinIO 直连 URL 兜底."""
    photos: list[dict[str, Any]] = [{"object_key": "uploads/face.jpg"}]
    storage = MagicMock()
    storage.presigned_get_url = AsyncMock(side_effect=RuntimeError("minio down"))

    fake_cfg = MagicMock()
    fake_cfg.storage.minio.secure = False
    fake_cfg.storage.minio.endpoint = "localhost:9000"
    fake_cfg.storage.minio.bucket = "selfwell"

    with (
        patch("app.storage.factory.get_storage", return_value=storage),
        patch("app.services._photo_urls.app_config", fake_cfg),
    ):
        result = await build_photo_urls(photos)

    assert result == ["http://localhost:9000/selfwell/uploads/face.jpg"]


@pytest.mark.asyncio
async def test_build_photo_urls_skip_empty_url() -> None:
    """photo 字典缺 url/object_key 或值为空字符串 → 跳过."""
    photos: list[dict[str, Any]] = [
        {"object_key": "", "body_part": "face"},
        {"body_part": "shoulder_neck"},  # 无 url/object_key
        {},
        {"url": "https://example.com/kept.jpg"},
    ]
    storage = MagicMock()
    storage.presigned_get_url = AsyncMock()
    with patch("app.storage.factory.get_storage", return_value=storage):
        result = await build_photo_urls(photos)
    assert result == ["https://example.com/kept.jpg"]


@pytest.mark.asyncio
async def test_build_photo_urls_mixed_sources() -> None:
    """混合输入：passthrough + presigned + 空 + 兜底 同时出现."""
    photos: list[dict[str, Any]] = [
        {"url": "https://cdn.example.com/kept.jpg"},
        {"object_key": "uploads/face.jpg"},
        {"object_key": ""},
        {"object_key": "uploads/error.jpg"},
    ]
    storage = MagicMock()
    storage.presigned_get_url = AsyncMock(
        side_effect=[
            "https://minio.example.com/uploads/face.jpg?signed=ok",
            RuntimeError("minio 429"),
        ]
    )

    fake_cfg = MagicMock()
    fake_cfg.storage.minio.secure = True
    fake_cfg.storage.minio.endpoint = "minio.example.com"
    fake_cfg.storage.minio.bucket = "selfwell"

    with (
        patch("app.storage.factory.get_storage", return_value=storage),
        patch("app.services._photo_urls.app_config", fake_cfg),
    ):
        result = await build_photo_urls(photos)

    assert result == [
        "https://cdn.example.com/kept.jpg",
        "https://minio.example.com/uploads/face.jpg?signed=ok",
        "https://minio.example.com/selfwell/uploads/error.jpg",
    ]
