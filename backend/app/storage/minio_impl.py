"""MinIO 对象存储实现。

重试策略（Sprint D M2 修复 #4）：
- transient（5xx / 网络抖动）：走 ``async_retry`` 指数退避（默认 4 次）
- permanent（NoSuchKey / AccessDenied 等 4xx）：立即抛业务错 ``UserInputError``
"""

from __future__ import annotations

from datetime import timedelta
from io import BytesIO
from typing import TYPE_CHECKING

from minio import Minio
from minio.error import S3Error

from app.conf.app_config import MinioConfig
from app.core.errors import UserInputError
from app.core.log import logger
from app.errors.codes import E_UPLOAD_PRESIGN_FAILED
from app.storage.base import ObjectStorage

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# transient 错误码（来自 AWS S3 / MinIO，5xx 或网络问题，可重试）
_TRANSIENT_S3_CODES: frozenset[str] = frozenset(
    {
        "InternalError",
        "ServiceUnavailable",
        "SlowDown",
        "RequestTimeout",
        "Throttling",
        "RequestTimeoutException",
    }
)
# permanent 错误码（4xx 客户端错误，立即失败不重试）
_PERMANENT_S3_CODES: frozenset[str] = frozenset(
    {
        "NoSuchKey",
        "NoSuchBucket",
        "AccessDenied",
        "InvalidBucketName",
        "InvalidArgument",
        "InvalidObjectName",
        "NoSuchObject",
        "MethodNotAllowed",
        "SignatureDoesNotMatch",
    }
)


def _classify_s3_error(exc: S3Error) -> str:
    """把 S3Error 分类成 ``transient`` / ``permanent``。"""
    code = (exc.code or "").strip()
    if code in _TRANSIENT_S3_CODES:
        return "transient"
    if code in _PERMANENT_S3_CODES:
        return "permanent"
    # 未知：按 transient 处理（保守策略，宁可重试也不要漏）
    return "transient"


def _raise_user_input_for_s3(exc: S3Error) -> None:
    """把 S3Error 转换成业务错误 ``UserInputError(E_UPLOAD_PRESIGN_FAILED)``。"""
    raise UserInputError(
        f"对象存储操作失败：{exc.code}",
        code=E_UPLOAD_PRESIGN_FAILED,
        field="object_key",
        s3_code=exc.code or "Unknown",
    ) from exc


async def _with_retry(sync_fn, *, attempts: int = 4):
    """对同步函数做指数退避重试；只重试 transient 错误。

    Args:
        sync_fn: 可调用对象（同步），返回结果或抛 ``S3Error``
        attempts: 最大尝试次数

    Returns:
        sync_fn() 的结果

    Raises:
        UserInputError: permanent S3Error 转换
        S3Error: transient S3Error 重试耗尽

    """
    last_exc: S3Error | None = None
    for attempt in range(1, attempts + 1):
        try:
            return sync_fn()
        except S3Error as exc:
            kind = _classify_s3_error(exc)
            if kind == "permanent":
                _raise_user_input_for_s3(exc)
            last_exc = exc
            if attempt < attempts:
                logger.warning(
                    "minio_retry_transient",
                    s3_code=exc.code,
                    attempt=attempt,
                    max_attempts=attempts,
                )
                import asyncio

                await asyncio.sleep(min(0.5 * (2 ** (attempt - 1)), 8.0))
    assert last_exc is not None
    raise last_exc


class MinioStorage(ObjectStorage):
    """MinIO 客户端适配。"""

    def __init__(
        self,
        config: MinioConfig | None = None,
        *,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        secure: bool | None = None,
    ) -> None:
        """支持两种构造方式：
        - ``MinioStorage(config: MinioConfig)``（生产）
        - ``MinioStorage(endpoint=..., access_key=..., secret_key=..., bucket=..., secure=...)``（测试）
        """
        if config is not None:
            self._endpoint = config.endpoint
            self._access_key = config.root_user
            self._secret_key = config.root_password
            self._bucket = config.bucket
            self._secure = config.secure
        else:
            if not all(
                v is not None for v in (endpoint, access_key, secret_key, bucket)
            ):
                raise ValueError(
                    "MinioStorage 需 config 或全部 kwargs (endpoint, access_key, secret_key, bucket)"
                )
            assert endpoint is not None
            assert access_key is not None
            assert secret_key is not None
            assert bucket is not None
            self._endpoint = endpoint
            self._access_key = access_key
            self._secret_key = secret_key
            self._bucket = bucket
            self._secure = bool(secure) if secure is not None else False
        # minio SDK 自身要求 access_key / secret_key 非空；空字符串会抛 ValueError
        if not self._access_key or not self._secret_key:
            raise ValueError(
                "MinioStorage 需有效的 access_key / secret_key（minio SDK 强制）"
            )
        self._client = Minio(
            self._endpoint,
            access_key=self._access_key,
            secret_key=self._secret_key,
            secure=self._secure,
        )

    @property
    def bucket(self) -> str:
        return self._bucket

    async def put_object(
        self,
        key: str,
        data: AsyncIterator[bytes] | bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> str:
        key = _normalize_key(key)
        content = await _collect_bytes(data)

        def _put() -> None:
            self._client.put_object(
                bucket_name=self._bucket,
                object_name=key,
                data=BytesIO(content),
                length=len(content),
                content_type=content_type,
            )

        await _with_retry(_put)
        scheme = "https" if self._secure else "http"
        return f"{scheme}://{self._endpoint}/{self._bucket}/{key}"

    async def get_object(self, key: str) -> bytes:
        key = _normalize_key(key)

        def _get() -> bytes:
            response = self._client.get_object(self._bucket, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        return await _with_retry(_get)

    async def delete_object(self, key: str) -> None:
        key = _normalize_key(key)

        def _rm() -> None:
            self._client.remove_object(self._bucket, key)

        try:
            await _with_retry(_rm)
        except (S3Error, UserInputError) as exc:
            # delete_object 幂等：NoSuchKey 视为成功（不要抛错给上层）
            s3_code: str = ""
            if isinstance(exc, S3Error):
                s3_code = exc.code or ""
            elif isinstance(exc, UserInputError):
                s3_code = str(exc.context.get("s3_code", ""))
            if s3_code in {"NoSuchKey", "NoSuchObject"}:
                return
            raise

    async def presigned_url(self, key: str, *, expires_sec: int = 3600) -> str:
        key = _normalize_key(key)

        def _sign() -> str:
            return self._client.presigned_put_object(
                bucket_name=self._bucket,
                object_name=key,
                expires=timedelta(seconds=expires_sec),
            )

        return await _with_retry(_sign)

    async def presigned_get_url(self, key: str, *, expires_sec: int = 3600) -> str:
        key = _normalize_key(key)

        def _sign_get() -> str:
            return self._client.presigned_get_object(
                bucket_name=self._bucket,
                object_name=key,
                expires=timedelta(seconds=expires_sec),
            )

        return await _with_retry(_sign_get)

    async def _ensure_bucket(self) -> None:
        def _ensure() -> None:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)

        await _with_retry(_ensure)


def _normalize_key(key: str) -> str:
    normalized = key.strip()
    if not normalized:
        raise ValueError("object key must not be empty")
    return normalized


async def _collect_bytes(data: AsyncIterator[bytes] | bytes) -> bytes:
    if isinstance(data, bytes):
        return data
    chunks: list[bytes] = []
    async for chunk in data:
        chunks.append(chunk)
    return b"".join(chunks)


__all__ = ["MinioStorage"]
