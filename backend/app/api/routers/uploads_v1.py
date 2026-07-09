"""M2 上传 presign 路由（``/api/v1/uploads``）。

真源：``docs/spec/SPEC-M2-multimodal-diagnosis.md`` §上传通道
+ ``docs/api/openapi.yaml`` ``#/components/responses/PresignResponse``。

约定：
- ``object_key`` 命名规范：``{purpose}/{user_id}/{uuid4()}.{ext}``
- ``upload_url`` = ``storage.presigned_url(object_key, expires_sec=3600)``（PUT 直传 URL）
- ``cdn_url`` = 同源（MVP 不实现专门 CDN；前端直接从 ``upload_url`` 自取读路径）
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import current_user_id
from app.core.log import logger
from app.errors.codes import E_UPLOAD_INVALID_CONTENT_TYPE, E_UPLOAD_INVALID_PURPOSE
from app.storage.factory import get_storage

router = APIRouter(prefix="/uploads", tags=["uploads"])


# ─────────────────────────────────────────────────────────────────────────────
# §一 Schema
# ─────────────────────────────────────────────────────────────────────────────
class PresignRequest(BaseModel):
    """presign 上传请求。

    Attributes:
        contentType: MIME 类型，仅允许 ``image/jpeg|image/png|image/webp``。
        purpose: 用途，``diagnosis | feedback``（按业务模块扩展）。

    """

    contentType: str = Field(  # noqa: N815
        ..., description="MIME 类型：image/jpeg | image/png | image/webp"
    )
    purpose: str = Field(..., description="用途：diagnosis | feedback")


class PresignResponse(BaseModel):
    """presign 上传响应。

    Attributes:
        upload_url: PUT 直传 URL（前端把文件 PUT 到这个 URL）。
        object_key: 服务端约定的对象 key（前端上传完成后需把 object_key 传给后续业务 endpoint）。
        expires_in: URL 有效期（秒）。
        cdn_url: 读路径（MVP = upload_url；预留 CDN 改造）。

    """

    upload_url: str
    object_key: str
    expires_in: int
    cdn_url: str


# ─────────────────────────────────────────────────────────────────────────────
# §二 常量
# ─────────────────────────────────────────────────────────────────────────────
_ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset({"image/jpeg", "image/png", "image/webp"})
_ALLOWED_PURPOSES: frozenset[str] = frozenset({"diagnosis", "feedback"})
_CONTENT_TYPE_TO_EXT: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_PRESIGN_EXPIRES_SEC: int = 3600


# ─────────────────────────────────────────────────────────────────────────────
# §三 路由
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/presign",
    response_model=PresignResponse,
    summary="申请对象存储 PUT 直传 URL",
)
async def presign_upload_endpoint(
    body: PresignRequest,
    user_id: str = Depends(current_user_id),
) -> PresignResponse:
    """申请对象存储直传 URL。

    Raises:
        UserInputError (400): ``contentType`` 或 ``purpose`` 不在白名单。

    Returns:
        ``PresignResponse``（含 upload_url / object_key / expires_in / cdn_url）。

    """
    content_type = body.contentType.strip().lower()
    purpose = body.purpose.strip().lower()

    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": E_UPLOAD_INVALID_CONTENT_TYPE,
                "message_zh": f"contentType 不允许：{body.contentType}",
                "field": "contentType",
                "allowed": sorted(_ALLOWED_CONTENT_TYPES),
            },
        )
    if purpose not in _ALLOWED_PURPOSES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": E_UPLOAD_INVALID_PURPOSE,
                "message_zh": f"purpose 不允许：{body.purpose}",
                "field": "purpose",
                "allowed": sorted(_ALLOWED_PURPOSES),
            },
        )

    ext = _CONTENT_TYPE_TO_EXT[content_type]
    object_key = f"{purpose}/{user_id}/{uuid4().hex}.{ext}"

    storage = get_storage()
    upload_url = await storage.presigned_url(object_key, expires_sec=_PRESIGN_EXPIRES_SEC)

    logger.info(
        "upload_presigned",
        user_id=user_id,
        purpose=purpose,
        content_type=content_type,
        object_key=object_key,
        expires_sec=_PRESIGN_EXPIRES_SEC,
    )
    return PresignResponse(
        upload_url=upload_url,
        object_key=object_key,
        expires_in=_PRESIGN_EXPIRES_SEC,
        cdn_url=upload_url,
    )


__all__ = ["router"]
