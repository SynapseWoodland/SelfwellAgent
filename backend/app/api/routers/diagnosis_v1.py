"""M2 诊断路由（``/api/v1/diagnosis``）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
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
    photos: list[PhotoInput] = Field(..., min_length=3, max_length=3)
    complaint: str | None = Field(default=None, max_length=500)


class DiagnosisData(BaseModel):
    report_id: str | None = None
    directions: list[dict]
    tags: list[str]
    summary: str
    cached: bool = False
    llm_model: str | None = None


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
            photos=[p.model_dump() for p in body.photos],
            complaint=body.complaint,
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
