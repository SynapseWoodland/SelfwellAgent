"""M8 主动回忆路由（``/api/v1/butler`` recall 部分）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.services.recall_service import (
    RecallDailyLimitError,
    RecallError,
    generate_recall,
    get_recall,
)

butler_router = APIRouter(prefix="/butler", tags=["butler"])


@butler_router.post("/recall")
async def generate_recall_endpoint(
    body: dict | None = None,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    payload = body or {}
    try:
        return {
            "code": 0,
            "data": await generate_recall(
                session,
                user_id=user_id,
                trigger=payload.get("trigger", "user_manual"),
                plan_id=payload.get("plan_id"),
            ),
        }
    except (RecallError, RecallDailyLimitError) as exc:
        raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})


@butler_router.get("/recall/{recall_id}")
async def get_recall_endpoint(
    recall_id: str,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    try:
        return {"code": 0, "data": await get_recall(session, user_id=user_id, recall_id=recall_id)}
    except RecallError as exc:
        raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})


@butler_router.get("/recall/day/{day}")
async def get_recall_by_day_endpoint(
    day: int,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    from app.services.recall_service import get_recall_by_day

    data = await get_recall_by_day(session, user_id=user_id, day=day)
    return {"code": 0, "data": data or {}}


__all__ = ["butler_router"]
