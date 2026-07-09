"""对象存储工厂（按 ``app_config.storage.provider`` 选择 MinIO / COS）。

真源：``app.conf.app_config.StorageConfig.provider`` +  # noqa: E501
``docs/architecture/mvp-tech-architecture.md`` §10。

约定：
- MVP ``provider = minio`` 走 ``MinioStorage``（真接入，已可用）。
- ``provider = cos`` 抛 ``NotImplementedError``（Sprint 4 M10 上线时由 M10 worker 真接入）。
- 单例懒加载；可通过 ``reset_storage_cache()`` 重置（用于测试）。
"""

from __future__ import annotations

from threading import Lock

from app.conf.app_config import StorageConfig, app_config
from app.core.log import logger
from app.storage.base import ObjectStorage
from app.storage.cos_impl import CosStorage
from app.storage.minio_impl import MinioStorage

_storage: ObjectStorage | None = None
_lock: Lock = Lock()


def get_storage(config: StorageConfig | None = None) -> ObjectStorage:
    """获取对象存储实例（单例，懒加载）。

    Args:
        config: 可选 ``StorageConfig``；不传则使用全局 ``app_config.storage``。

    Returns:
        ``ObjectStorage`` 实例（当前仅 MinioStorage 真接入；COS 抛 NotImplementedError）。

    Raises:
        NotImplementedError: provider 为 ``cos`` 时（MVP 未实现）。
        ValueError: provider 非法值。

    Example:
        >>> storage = get_storage()
        >>> url = await storage.presigned_url("diagnosis/u/abc.jpg", expires_sec=600)
        >>> assert url.startswith("http")

    """
    global _storage
    cfg = config or app_config.storage
    with _lock:
        if _storage is not None:
            return _storage
        provider = cfg.provider.lower().strip()
        if provider == "minio":
            logger.info("storage_init", provider="minio", bucket=cfg.minio.bucket)
            _storage = MinioStorage(cfg.minio)
        elif provider == "cos":
            logger.info("storage_init", provider="cos", stub=True)
            _storage = CosStorage()
        else:
            raise ValueError(f"Unknown storage provider: {cfg.provider!r}")
        return _storage


def reset_storage_cache() -> None:
    """重置单例缓存（测试用）。"""
    global _storage
    with _lock:
        _storage = None


__all__ = ["get_storage", "reset_storage_cache"]
