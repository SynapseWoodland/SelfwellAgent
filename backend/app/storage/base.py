"""ObjectStorage 抽象（Sprint 0 骨架）。

真源：ADR-0009 + ``docs/api/openapi.yaml#/components/responses/StorageCallback``。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class ObjectStorage(ABC):
    """对象存储抽象基类（MinIO / COS）。

    实现：
    - ``MinioStorage``（开发态）
    - ``CosStorage``（生产态，仅占位 Sprint 0）
    """

    @abstractmethod
    async def put_object(
        self,
        key: str,
        data: AsyncIterator[bytes] | bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> str:
        """上传对象；返回最终可访问 URL。"""

    @abstractmethod
    async def get_object(self, key: str) -> bytes:
        """下载对象字节。"""

    @abstractmethod
    async def delete_object(self, key: str) -> None:
        """删除对象。"""

    @abstractmethod
    async def presigned_url(self, key: str, *, expires_sec: int = 3600) -> str:
        """生成临时直传 URL（presigned PUT / GET）。"""


__all__ = ["ObjectStorage"]
