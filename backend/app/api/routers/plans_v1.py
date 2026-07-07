"""M3 21 天方案 + 视频匹配路由（``/api/v1/plans`` + ``/api/v1/videos``）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.services.plan_service import (
    PlanError,
    PlanNotFoundError,
    generate_plan,
    get_current_plan,
    get_plan,
    get_today_plan_tasks,
    match_videos_for_tags,
)

plans_router = APIRouter(prefix="/plans", tags=["plans"])
videos_router = APIRouter(prefix="/videos", tags=["videos"])


class PlanCreateRequest(BaseModel):
    report_id: str


class PlanData(BaseModel):
    plan_id: str
    report_id: str
    length_days: int
    days: list[dict]
    started_at: str | None = None


class PlanResponse(BaseModel):
    code: int = 0
    data: PlanData | dict


@plans_router.post("/generate", response_model=PlanResponse, summary="生成 21 天方案")
async def generate_plan_endpoint(
    body: PlanCreateRequest,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> PlanResponse:
    try:
        result = await generate_plan(session, user_id=user_id, report_id=body.report_id)
    except PlanError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    return PlanResponse(data=PlanData(**result))


@plans_router.get("/current", response_model=PlanResponse, summary="当前进行中方案")
async def get_current_plan_endpoint(
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> PlanResponse:
    try:
        result = await get_current_plan(session, user_id=user_id)
    except PlanNotFoundError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    return PlanResponse(data=result)


@plans_router.get("/today", summary="今日方案任务（home 页用）")
async def get_today_plan_endpoint(
    day: int | None = Query(default=None, ge=1, le=21, description="指定第几天（默认按 started_at 推算）"),
    _user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    """无 active plan 时返回 ``tasks=[]`` + ``day_index=1``，前端走空状态。"""
    data = await get_today_plan_tasks(session, user_id=_user_id, day_index=day)
    return {"code": 0, "data": data}


@plans_router.get("/{plan_id}", response_model=PlanResponse, summary="获取方案详情")
async def get_plan_endpoint(
    plan_id: str,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> PlanResponse:
    try:
        result = await get_plan(session, user_id=user_id, plan_id=plan_id)
    except PlanNotFoundError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    return PlanResponse(data=result)


@videos_router.get("/match", summary="按 tags 匹配视频")
async def match_videos_endpoint(
    tags: str = Query(..., description="逗号分隔的标签列表"),
    intensity: str = Query(default="适中"),
    preferred_time: str = Query(default="不固定"),
    top_k: int = Query(default=10, ge=1, le=50),
    _user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    ranked = await match_videos_for_tags(
        session,
        tags=tag_list,
        intensity=intensity,
        preferred_time=preferred_time,
        top_k=top_k,
    )
    return {"code": 0, "data": {"videos": ranked, "count": len(ranked)}}


__all__ = ["plans_router", "videos_router"]
