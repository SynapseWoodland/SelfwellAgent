"""M3 21 天方案 + 视频匹配路由（``/api/v1/plans`` + ``/api/v1/videos``）。"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.db.models.plan import Plan
from app.services.plan_service import (
    PLAN_LENGTH_DAYS,
    PlanError,
    PlanNotFoundError,
    aggregate_plan_weeks,
    generate_plan,
    get_current_plan,
    get_plan,
    get_plan_preview,
    get_today_plan_tasks,
    match_videos_for_tags,
)
from sqlalchemy import select


async def _load_current_plan_orm(
    session: AsyncSession, *, user_id: str
) -> Plan:
    stmt = (
        select(Plan)
        .where(Plan.user_id == user_id, Plan.status == "active")
        .order_by(Plan.created_at.desc())
        .limit(1)
    )
    res = await session.execute(stmt)
    plan = res.scalar_one_or_none()
    if plan is None:
        raise PlanNotFoundError(field="current_plan")
    return plan


plans_router = APIRouter(prefix="/plans", tags=["plans"])
videos_router = APIRouter(prefix="/videos", tags=["videos"])


class PlanCreateRequest(BaseModel):
    report_id: str


class PlanPreviewDay(BaseModel):
    """方案预览每日条目（前端 plan-delivery/index.ts:loadPreview 契约）。

    字段语义：
    - ``day_index``: 第几天（1-21）
    - ``duration_minutes``: 当日单个任务时长（分钟）
    - ``task``: 任务标签（默认取首个任务的 video_id）
    - ``title``: 当日展示标题（默认取首个任务标题或中文默认文案）
    - ``source``: 任务来源（``video_pool`` / ``placeholder`` 等）
    - ``status``: 任务状态（``pending`` / ``done`` / ``locked``）
    """

    day_index: int
    duration_minutes: int
    task: str | None = None
    title: str
    source: str
    status: str


class PlanData(BaseModel):
    plan_id: str
    report_id: str
    length_days: int
    days: list[PlanPreviewDay]
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
    view: Literal["today", "all"] = Query(
        default="today",
        description="today=今日视图（默认，兼容老契约）；all=3 周 21 天聚合视图",
    ),
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> PlanResponse:
    if view == "all":
        try:
            plan = await _load_current_plan_orm(session, user_id=user_id)
            base = await get_plan(session, user_id=user_id, plan_id=str(plan.id))
        except PlanNotFoundError as exc:
            raise HTTPException(
                status_code=exc.http_status,
                detail={"code": exc.code, "message_zh": exc.render_zh()},
            ) from exc
        weeks = aggregate_plan_weeks(plan)
        elapsed: int
        if plan.started_at is not None:
            elapsed = (date.today() - plan.started_at).days + 1
        else:
            elapsed = 1
        current_day_index = max(1, min(PLAN_LENGTH_DAYS, elapsed))
        data: dict[str, Any] = {
            "plan_id": base["plan_id"],
            "report_id": base.get("report_id"),
            "status": base.get("status"),
            "total_days": PLAN_LENGTH_DAYS,
            "started_at": base.get("started_at"),
            "current_day_index": current_day_index,
            "view": "all",
            "weeks": weeks,
        }
        return PlanResponse(data=data)

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


@plans_router.get("/{plan_id}/preview", summary="方案 21 天预览（plan-delivery 用）")
async def get_plan_preview_endpoint(
    plan_id: str,
    days: int = Query(
        default=21,
        ge=1,
        le=PLAN_LENGTH_DAYS,
        description="预览返回天数（默认 21 = 全量；取 1-21）",
    ),
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    """21 天方案预览,字段对齐前端 plan-delivery/index.ts:loadPreview 契约。

    PR-Contract-Fix C-3:此前端调 ``GET /plans/{id}/preview?days=21`` 不存在,
    只能走 fallback 静态模板;本次新增真端点。
    """
    try:
        result = await get_plan_preview(
            session, user_id=user_id, plan_id=plan_id, days=days,
        )
    except PlanNotFoundError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    return {"code": 0, "data": result}


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
