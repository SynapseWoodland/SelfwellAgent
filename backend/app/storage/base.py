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

    async def presigned_get_url(self, key: str, *, expires_sec: int = 3600) -> str:
        """生成临时读取 URL（GET presigned）。

        默认实现：调 ``presigned_url``（PUT）；子类可 override 提供真 GET presigned。
        用途：把 object_key 解析为可访问 URL，供下游 LLM/前端读取。
        """
        return await self.presigned_url(key, expires_sec=expires_sec)

    async def presigned_post_form(
        self,
        key: str,
        *,
        expires_sec: int = 3600,
        content_type: str = "application/octet-stream",
        max_size: int = 10 * 1024 * 1024,
    ) -> dict[str, str]:
        """生成 presigned POST 表单（multipart/form-data），返回签名字段 dict。

        返回 dict 含：x-amz-algorithm / x-amz-credential / x-amz-date /
        policy / x-amz-signature。调用方需自行加上 ``key`` 字段并拼装
        multipart/form-data 请求体。

        用途：wx.uploadFile / axios 等浏览器端上传工具需要 multipart/form-data，
        无法使用 presigned PUT URL（S3 不兼容）。
        """
        raise NotImplementedError(
            f"{type(self).__name__} 不支持 presigned POST 表单，请使用 presigned_url"
        )

    @property
    def public_host(self) -> str:
        """公网域名（用于拼接 form_url / cdn_url）。默认空字符串。"""
        return ""


__all__ = ["ObjectStorage"]
