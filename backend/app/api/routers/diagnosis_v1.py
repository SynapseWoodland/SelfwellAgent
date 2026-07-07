"""M2 诊断路由（``/api/v1/diagnosis``）。

真源：前端 diagnosis-upload/index.ts §4.3 + openapi.yaml tag=diagnosis。

契约兼容：
- 前端传单图：{ objectKey, user_note }  （diagnosis-upload/index.ts L88-89）
- 原生多图：   { photos: [url, body_part, ...], complaint }（后端期望）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.services.diagnosis_service import (
    DiagnosisError,
    DiagnosisNotFoundError,
    create_diagnosis,
    get_diagnosis,
)

router = APIRouter(prefix="/diagnosis", tags=["diagnosis"])


class PhotoInput(BaseModel):
    url: str = Field(..., min_length=1)
    body_part: str = Field(..., description="face | head | shoulder_neck")
    format: str = Field(default="jpg")
    size_bytes: int = Field(default=0, ge=0)


class DiagnosisCreateRequest(BaseModel):
    """MVP 诊断请求 Schema（兼容前端单图 + 原生多图两种格式）。

    前端单图格式（来自 diagnosis-upload/index.ts §4.3）：
        { objectKey: string, user_note?: string }

    原生多图格式：
        { photos: PhotoInput[3], complaint?: string }

    MVP 优先策略：后端同时支持两种格式，前端体验不变。
    """

    # ── 前端单图格式 ─────────────────────────────────────────────────────────
    objectKey: str | None = Field(
        default=None, description="已上传图片的 objectKey（前端单图格式）"
    )
    user_note: str | None = Field(default=None, description="用户备注（前端单图格式）")

    # ── 原生多图格式 ─────────────────────────────────────────────────────────
    photos: list[PhotoInput] | None = Field(default=None)
    complaint: str | None = Field(default=None, max_length=500)

    def resolve_photos(self) -> list[dict]:
        """将请求转换为 service 层期望的 photos 参数格式。

        前端单图格式：构造 1 张虚假的 photo 对象（body_part=face, url=objectKey）。
        原生多图格式：直接透传。

        Raises:
            ValidationError: 当既无 ``photos`` 也无 ``objectKey`` 时。

        """
        if self.photos:
            return [p.model_dump() for p in self.photos]
        if self.objectKey:
            return [
                {
                    "url": self.objectKey,
                    "body_part": "face",
                    "format": "jpg",
                    "size_bytes": 0,
                }
            ]
        err = ValueError("缺少 photos 或 objectKey")
        raise ValidationError.from_exception_data(  # type: ignore[attr-defined]
            self.__class__.__name__,
            [
                {
                    "type": "missing",
                    "loc": ("resolve_photos",),
                    "input": {},
                    "ctx": {"error": err},
                }
            ],
        )

    def resolve_complaint(self) -> str | None:
        return self.user_note if self.user_note else self.complaint


class DiagnosisData(BaseModel):
    report_id: str | None = None
    directions: list[dict]
    tags: list[str]
    summary: str
    cached: bool = False
    llm_model: str | None = None

    @field_validator("directions", mode="before")
    @classmethod
    def _flatten_directions(cls, v: object) -> object:
        """兜底 LLM/缓存中可能出现的 ``{"items": [...]}`` 嵌套 dict。

        历史背景：早期 Sprint 2 实现把 ``directions``/``tags`` 存为 ``{"items": [...]}``
        形式，导致 500 (Pydantic list_type 校验失败)。当前 service 层已拍扁为 list，
        但 user.report_cache 仍可能存在旧格式数据；本 validator 在响应构造时拍扁兜底。

        Args:
            v: 原始输入（可能是 list 或 ``{"items": [...]}`` dict）。

        Returns:
            拍扁后的 list。

        """
        if isinstance(v, dict) and "items" in v:
            items = v["items"]
            if not isinstance(items, list):
                return []
            normalized: list[dict] = []
            for item in items:
                if isinstance(item, str):
                    normalized.append({"title": item, "description": item})
                elif isinstance(item, dict):
                    normalized.append(item)
                else:
                    normalized.append({"title": str(item)})
            return normalized
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def _flatten_tags(cls, v: object) -> object:
        """同 ``_flatten_directions``，但接受 ``{"items": [...]}`` 嵌套 dict。"""
        if isinstance(v, dict) and "items" in v:
            items = v["items"]
            if not isinstance(items, list):
                return []
            return [str(x) for x in items]
        return v


class DiagnosisResponse(BaseModel):
    code: int = 0
    data: DiagnosisData


class ReportGetResponse(BaseModel):
    code: int = 0
    data: dict


@router.post("", response_model=DiagnosisResponse, summary="创建多模态诊断报告")
async def create_diagnosis_endpoint(
    body: DiagnosisCreateRequest,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> DiagnosisResponse:
    try:
        result = await create_diagnosis(
            session,
            user_id=user_id,
            photos=body.resolve_photos(),
            complaint=body.resolve_complaint(),
        )
    except DiagnosisError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    return DiagnosisResponse(data=DiagnosisData(**result))


@router.get("/{report_id}", response_model=ReportGetResponse, summary="获取诊断报告")
async def get_diagnosis_endpoint(
    report_id: str,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> ReportGetResponse:
    try:
        result = await get_diagnosis(session, user_id=user_id, report_id=report_id)
    except DiagnosisNotFoundError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    return ReportGetResponse(data=result)


__all__ = ["router"]
