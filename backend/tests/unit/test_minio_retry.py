"""Unit tests for ``MinioStorage`` retry + S3 error classification.

覆盖：
- transient 5xx → 重试直到成功
- permanent 4xx（NoSuchKey / AccessDenied）→ 立即抛 ``UserInputError``
- 瞬时失败 → 重试成功
- ``_classify_s3_error`` 分类正确
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from minio.error import S3Error

from app.core.errors import UserInputError
from app.errors.codes import E_UPLOAD_PRESIGN_FAILED
from app.storage.minio_impl import (
    MinioStorage,
    _classify_s3_error,
)


def _cfg():
    from app.conf.app_config import MinioConfig

    return MinioConfig(
        endpoint="localhost:9000",
        MINIO_ROOT_USER="user",
        MINIO_ROOT_PASSWORD="pass",
        bucket="selfwell",
        secure=False,
    )


def _s3(code: str) -> S3Error:
    """构造一个 S3Error，code 是 AWS 错误码字符串。"""
    return S3Error(
        response=MagicMock(),
        code=code,
        message="msg",
        resource="r",
        request_id="qid",
        host_id="h",
        bucket_name="b",
        object_name="o",
    )


# ─── 分类 ────────────────────────────────────────────────────────────────────
def test_classify_s3_error_transient() -> None:
    assert _classify_s3_error(_s3("InternalError")) == "transient"
    assert _classify_s3_error(_s3("ServiceUnavailable")) == "transient"
    assert _classify_s3_error(_s3("SlowDown")) == "transient"


def test_classify_s3_error_permanent() -> None:
    assert _classify_s3_error(_s3("NoSuchKey")) == "permanent"
    assert _classify_s3_error(_s3("AccessDenied")) == "permanent"
    assert _classify_s3_error(_s3("InvalidBucketName")) == "permanent"


def test_classify_s3_error_unknown_defaults_transient() -> None:
    assert _classify_s3_error(_s3("SomeWeirdFutureCode")) == "transient"


# ─── 重试 ────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_presigned_url_retries_on_transient_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """两次 transient 后第三次成功。"""
    storage = MinioStorage(_cfg())
    sleep_calls: list[float] = []

    async def fake_sleep(s: float) -> None:
        sleep_calls.append(s)

    monkeypatch.setattr("asyncio.sleep", fake_sleep)

    call_count = {"n": 0}

    def fake_presign(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise _s3("InternalError")
        return "http://signed-url"

    monkeypatch.setattr(storage._client, "presigned_put_object", fake_presign)
    url = await storage.presigned_url("k", expires_sec=60)
    assert url == "http://signed-url"
    assert call_count["n"] == 3
    assert len(sleep_calls) == 2  # 2 次 retry sleep


@pytest.mark.asyncio
async def test_presigned_url_permanent_no_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Permanent (NoSuchKey) → 立即抛 UserInputError(E_UPLOAD_PRESIGN_FAILED)。"""
    storage = MinioStorage(_cfg())
    call_count = {"n": 0}

    def fake_presign(*args, **kwargs):
        call_count["n"] += 1
        raise _s3("NoSuchKey")

    monkeypatch.setattr(storage._client, "presigned_put_object", fake_presign)
    with pytest.raises(UserInputError) as exc_info:
        await storage.presigned_url("k", expires_sec=60)
    assert exc_info.value.code == E_UPLOAD_PRESIGN_FAILED
    assert call_count["n"] == 1  # 没重试


@pytest.mark.asyncio
async def test_get_object_retries_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = MinioStorage(_cfg())
    call_count = {"n": 0}

    class _FakeResp:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload

        def read(self) -> bytes:
            return self._payload

        def close(self) -> None:
            pass

        def release_conn(self) -> None:
            pass

    def fake_get(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise _s3("ServiceUnavailable")
        return _FakeResp(b"data")

    monkeypatch.setattr(storage._client, "get_object", fake_get)
    data = await storage.get_object("k")
    assert data == b"data"
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_get_object_permanent_raises_user_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = MinioStorage(_cfg())

    def fake_get(*args, **kwargs):
        raise _s3("AccessDenied")

    monkeypatch.setattr(storage._client, "get_object", fake_get)
    with pytest.raises(UserInputError):
        await storage.get_object("k")
