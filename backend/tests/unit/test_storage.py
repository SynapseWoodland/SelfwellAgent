"""Unit tests for MinioStorage + get_storage factory.

真源：M2 修复 #1（落地 MinioStorage 真接入）+ #2（factory）。
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from minio.error import S3Error

from app.conf.app_config import MinioConfig, StorageConfig
from app.core.errors import UserInputError
from app.storage.factory import get_storage, reset_storage_cache
from app.storage.minio_impl import MinioStorage


# ─────────────────────────────────────────────────────────────────────────────
# §一 MinioStorage 真接入（mock minio SDK）
# ─────────────────────────────────────────────────────────────────────────────
def _make_cfg(**overrides) -> MinioConfig:
    """构造一个 MinioConfig（绕开 .env 依赖）。"""
    # pydantic-settings v2.14 中 field name 是 root_password 但 env alias 是 MINIO_ROOT_PASSWORD；
    # 用 alias 才能正确赋值（否则会被 .env 中的 MINIO_ROOT_PASSWORD 覆盖）。
    kwargs = dict(overrides)
    if "root_user" in kwargs:
        kwargs["MINIO_ROOT_USER"] = kwargs.pop("root_user")
    if "root_password" in kwargs:
        kwargs["MINIO_ROOT_PASSWORD"] = kwargs.pop("root_password")
    # presigned_url 测试依赖 _public_host，默认注入避免测试退化
    if "public_host" not in kwargs:
        kwargs["public_host"] = "husenlin.tail61999e.ts.net"
    return MinioConfig(**kwargs)


def test_minio_storage_constructor_uses_config() -> None:
    cfg = _make_cfg()
    storage = MinioStorage(cfg)
    assert storage.bucket == "selfwell"


def test_minio_storage_constructor_kwargs() -> None:
    storage = MinioStorage(
        endpoint="minio.local:9000",
        access_key="a",
        secret_key="b",
        bucket="bkt",
        secure=True,
    )
    assert storage.bucket == "bkt"


@pytest.mark.asyncio
async def test_minio_storage_put_object() -> None:
    cfg = _make_cfg()
    storage = MinioStorage(cfg)

    with patch.object(storage._client, "bucket_exists", return_value=True), patch.object(
        storage._client, "put_object", return_value=None
    ) as mock_put:
        url = await storage.put_object(
            "diagnosis/u/abc.jpg", b"hello", content_type="image/jpeg"
        )

    assert url.startswith("http://")
    assert "abc.jpg" in url
    mock_put.assert_called_once()
    # kwargs check
    kwargs = mock_put.call_args.kwargs
    assert kwargs["bucket_name"] == "selfwell"
    assert kwargs["object_name"] == "diagnosis/u/abc.jpg"
    assert kwargs["content_type"] == "image/jpeg"
    assert kwargs["length"] == 5


@pytest.mark.asyncio
async def test_minio_storage_get_object() -> None:
    cfg = _make_cfg()
    storage = MinioStorage(cfg)

    fake_resp = MagicMock()
    fake_resp.read.return_value = b"file-content"
    fake_resp.close = MagicMock()
    fake_resp.release_conn = MagicMock()

    with patch.object(storage._client, "get_object", return_value=fake_resp):
        content = await storage.get_object("k")

    assert content == b"file-content"
    fake_resp.close.assert_called_once()
    fake_resp.release_conn.assert_called_once()


@pytest.mark.asyncio
async def test_minio_storage_get_object_empty_key() -> None:
    cfg = _make_cfg()
    storage = MinioStorage(cfg)
    with pytest.raises(ValueError):
        await storage.get_object("")


@pytest.mark.asyncio
async def test_minio_storage_delete_object_ok() -> None:
    cfg = _make_cfg()
    storage = MinioStorage(cfg)
    with patch.object(storage._client, "remove_object", return_value=None):
        await storage.delete_object("k")  # 不抛


@pytest.mark.asyncio
async def test_minio_storage_delete_object_idempotent_missing() -> None:
    cfg = _make_cfg()
    storage = MinioStorage(cfg)
    err = S3Error(
        response=MagicMock(),
        code="NoSuchKey",
        message="no such",
        resource="k",
        request_id="rqid",
        host_id="host",
    )
    with patch.object(storage._client, "remove_object", side_effect=err):
        await storage.delete_object("k")  # 缺失视为成功


@pytest.mark.asyncio
async def test_minio_storage_delete_object_other_error() -> None:
    cfg = _make_cfg()
    storage = MinioStorage(cfg)
    # 正确构造 S3Error：response=mock, code="AccessDenied"
    err = S3Error(
        response=MagicMock(),
        code="AccessDenied",
        message="denied",
        resource="k",
        request_id="rqid",
        host_id="host",
    )
    with patch.object(storage._client, "remove_object", side_effect=err), pytest.raises(
        UserInputError
    ) as exc_info:
        await storage.delete_object("k")
    # AccessDenied 是 permanent → 立即抛 UserInputError(E_UPLOAD_PRESIGN_FAILED)
    assert exc_info.value.code == "E_UPLOAD_PRESIGN_FAILED"


@pytest.mark.asyncio
async def test_minio_storage_presigned_url_put() -> None:
    cfg = _make_cfg()
    storage = MinioStorage(cfg)
    fake_url = "http://localhost:9000/selfwell/k?X-Amz-Signature=abc"
    with patch.object(
        storage._client, "presigned_put_object", return_value=fake_url
    ) as mock_sig:
        url = await storage.presigned_url("k", expires_sec=600)

    # MINIO_PUBLIC_HOST 已配置，netloc 替换为公网域名 + prepend /minio
    assert url == "https://husenlin.tail61999e.ts.net/minio/selfwell/k?X-Amz-Signature=abc"
    mock_sig.assert_called_once()
    assert mock_sig.call_args.kwargs["expires"] == timedelta(seconds=600)
    assert mock_sig.call_args.kwargs["bucket_name"] == "selfwell"
    assert mock_sig.call_args.kwargs["object_name"] == "k"


@pytest.mark.asyncio
async def test_minio_storage_presigned_url_empty_key() -> None:
    cfg = _make_cfg()
    storage = MinioStorage(cfg)
    with pytest.raises(ValueError):
        await storage.presigned_url("")


@pytest.mark.asyncio
async def test_minio_storage_ensure_bucket_creates_when_missing() -> None:
    cfg = _make_cfg()
    storage = MinioStorage(cfg)
    with patch.object(storage._client, "bucket_exists", return_value=False), patch.object(
        storage._client, "make_bucket", return_value=None
    ) as mock_make:
        await storage._ensure_bucket()
    mock_make.assert_called_once_with("selfwell")


@pytest.mark.asyncio
async def test_minio_storage_ensure_bucket_skip_when_exists() -> None:
    cfg = _make_cfg()
    storage = MinioStorage(cfg)
    with patch.object(storage._client, "bucket_exists", return_value=True), patch.object(
        storage._client, "make_bucket"
    ) as mock_make:
        await storage._ensure_bucket()
    mock_make.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# §二 Factory：get_storage / reset_storage_cache
# ─────────────────────────────────────────────────────────────────────────────
def test_get_storage_minio_provider() -> None:
    reset_storage_cache()
    cfg = StorageConfig(provider="minio", minio=_make_cfg())
    storage = get_storage(cfg)
    assert isinstance(storage, MinioStorage)
    reset_storage_cache()


def test_get_storage_cos_not_implemented() -> None:
    reset_storage_cache()
    cfg = StorageConfig(provider="cos", minio=_make_cfg())
    storage = get_storage(cfg)
    # MVP CosStorage 仅占位（抛 NotImplementedError on actual calls）
    # 但构造可以
    assert storage.__class__.__name__ == "CosStorage"
    reset_storage_cache()


def test_get_storage_unknown_provider_raises() -> None:
    reset_storage_cache()
    cfg = StorageConfig(provider="unknown-xyz", minio=_make_cfg())
    with pytest.raises(ValueError):
        get_storage(cfg)
    reset_storage_cache()


def test_get_storage_singleton() -> None:
    reset_storage_cache()
    cfg = StorageConfig(provider="minio", minio=_make_cfg())
    s1 = get_storage(cfg)
    s2 = get_storage(cfg)
    assert s1 is s2
    reset_storage_cache()


def test_reset_storage_cache() -> None:
    reset_storage_cache()
    cfg = StorageConfig(provider="minio", minio=_make_cfg())
    s1 = get_storage(cfg)
    reset_storage_cache()
    s2 = get_storage(cfg)
    assert s1 is not s2
    reset_storage_cache()
