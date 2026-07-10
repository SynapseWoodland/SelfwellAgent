"""Photos URL 公共 helper（assistant + diagnosis 双路径复用）。

V5.2.1-PR2 T14（V5.2.1 §3.4 / §6.6）：
- 抽 ``diagnosis_service._photo_image_urls`` 内联实现
- 抽 ``assistant_service`` photos 段 inline dict 构造
- 单一入口，含公网 URL 优先 + ``presigned_get_url`` 失败兜底

约束：
- helper 文件路径：app/services/_photo_urls.py（前下划线表示模块内私有但可被 import）
- 单函数 ≤ 50 行（含 import / docstring / type hint）
- 复用 diagnosis_service._check_text_safety 不在本 PR 范围（PR4）
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from app.conf.app_config import app_config  # 模块顶层 import，便于 unittest.mock.patch


async def build_photo_urls(photos: list[dict[str, Any]]) -> list[str]:
    """生成多模态模型可用的图片 URL 列表。

    关键：必须生成公网可访问的预签名 URL（Ark SDK 在云端，
    无法访问 localhost MinIO 存储）。

    行为：
    1. 若 photo 含 ``url`` 且为 ``http(s)://`` 或 ``data:image/`` → 直接 passthrough
    2. 若 photo 含 ``object_key`` 或 ``url`` 是裸 key → 调
       ``storage.presigned_get_url(key, expires_sec=3600)``
    3. storage 抛异常 → 构造 MinIO 直连 URL 兜底
       ``{scheme}://{endpoint}/{bucket}/{quote(key)}``

    参数：
        photos: ``[{"object_key": "...", "body_part": "..."}, ...]`` 或
                ``[{"url": "https://..."}, ...]``

    返回：
        公网可访问图片 URL 列表（按 photos 顺序；空 url 跳过）
    """
    from app.storage.factory import get_storage

    cfg = app_config.storage
    storage = get_storage()
    urls: list[str] = []

    for photo in photos:
        url = str(photo.get("url", photo.get("object_key", ""))).strip()
        if not url:
            continue
        if url.startswith(("http://", "https://", "data:image/")):
            urls.append(url)
            continue
        try:
            urls.append(await storage.presigned_get_url(url, expires_sec=3600))
        except Exception:
            scheme = "https" if cfg.minio.secure else "http"
            key = quote(url, safe="/")
            urls.append(f"{scheme}://{cfg.minio.endpoint}/{cfg.minio.bucket}/{key}")

    return urls


__all__ = ["build_photo_urls"]
