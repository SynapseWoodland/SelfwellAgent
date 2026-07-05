"""MinIO 对象存储实现（Sprint 0 骨架）。

真源：``backend/docker-compose.yaml`` §minio + ``app.conf.app_config.MinioConfig``。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.storage.base import ObjectStorage

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class MinioStorage(ObjectStorage):
    """MinIO 客户端适配（占位 Sprint 0）。

    Sprint 1+ 实现真正的 ``put_object`` / ``presigned_url`` 调用，
    使用 ``minio.Minio`` SDK（已在 pyproject.toml 声明 ``minio>=7.2.0``）。
    """

    def __init__(
        self,
        *,
        endpoint: str = "localhost:9000",
        access_key: str = "",
        secret_key: str = "",
        bucket: str = "selfwell",
        secure: bool = False,
    ) -> None:
        self._endpoint = endpoint
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket = bucket
        self._secure = secure

    async def put_object(
        self,
        key: str,
        data: AsyncIterator[bytes] | bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> str:
        raise NotImplementedError("MinioStorage.put_object 待 Sprint 1+ 接入 minio SDK")

    async def get_object(self, key: str) -> bytes:
        raise NotImplementedError("MinioStorage.get_object 待 Sprint 1+ 接入")

    async def delete_object(self, key: str) -> None:
        raise NotImplementedError("MinioStorage.delete_object 待 Sprint 1+ 接入")

    async def presigned_url(self, key: str, *, expires_sec: int = 3600) -> str:
        raise NotImplementedError("MinioStorage.presigned_url 待 Sprint 1+ 接入")


__all__ = ["MinioStorage"]
