"""腾讯云 COS 对象存储实现（Sprint 0 占位 · V1.3 prod STAR 标记）。

真源：ADR-0009 + ``backend/Dockerfile`` ENV COS_SECRET_ID/SECRET。
Sprint 0 仅占位（接口骨架）；Sprint 4 M10 抱抱卡海报生成时真接入。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.storage.base import ObjectStorage

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class CosStorage(ObjectStorage):
    """腾讯云 COS 客户端适配（Sprint 0 占位）。"""

    def __init__(
        self,
        *,
        secret_id: str = "",
        secret_key: str = "",
        region: str = "ap-guangzhou",
        bucket: str = "selfwell-prod",
    ) -> None:
        self._secret_id = secret_id
        self._secret_key = secret_key
        self._region = region
        self._bucket = bucket

    async def put_object(
        self,
        key: str,
        data: AsyncIterator[bytes] | bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> str:
        raise NotImplementedError(
            "CosStorage 待 Sprint 4 M10 上线时由 M10 worker 真接入 cos-python-sdk-v5"
        )

    async def get_object(self, key: str) -> bytes:
        raise NotImplementedError("CosStorage 待 Sprint 4+")

    async def delete_object(self, key: str) -> None:
        raise NotImplementedError("CosStorage 待 Sprint 4+")

    async def presigned_url(self, key: str, *, expires_sec: int = 3600) -> str:
        raise NotImplementedError("CosStorage 待 Sprint 4+")


__all__ = ["CosStorage"]
