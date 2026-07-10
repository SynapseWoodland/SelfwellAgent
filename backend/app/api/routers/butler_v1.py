"""M8 主动回忆路由（``/api/v1/butler`` recall 部分）。

v4.1-prep（子任务 4）：router 内 ``raise HTTPException`` 改为 ``raise AppBusinessError(...)``，
最终 envelope 形态由 ``app/errors/envelope.AppBusinessError`` + exception_handler 出。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.errors.envelope import AppBusinessError
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
        raise AppBusinessError(
            code=exc.code,
            message_zh=exc.render_zh(),
            http_status=exc.http_status,
            **exc.context,
        ) from exc


@butler_router.get("/recall/{recall_id}")
async def get_recall_endpoint(
    recall_id: str,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    try:
        return {"code": 0, "data": await get_recall(session, user_id=user_id, recall_id=recall_id)}
    except RecallError as exc:
        raise AppBusinessError(
            code=exc.code,
            message_zh=exc.render_zh(),
            http_status=exc.http_status,
            **exc.context,
        ) from exc


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
