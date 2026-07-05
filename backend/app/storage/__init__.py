"""app.storage — 对象存储抽象 + MinIO / COS 实现占位（Sprint 0）。"""

from app.storage.base import ObjectStorage
from app.storage.cos_impl import CosStorage
from app.storage.minio_impl import MinioStorage

__all__ = ["CosStorage", "MinioStorage", "ObjectStorage"]
