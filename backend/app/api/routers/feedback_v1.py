"""M7 反馈路由（``/api/v1/feedback``）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.services.feedback_service import (
    FeedbackDailyLimitError,
    FeedbackError,
    create_feedback,
    list_user_feedbacks,
)

feedback_router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    feedback_type: str
    text_content: str | None = None
    photo_url: str | None = None
    photo_size_bytes: int | None = None
    body_part: str | None = None


@feedback_router.post("")
async def create_feedback_endpoint(
    body: FeedbackCreate,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    try:
        return {"code": 0, "data": await create_feedback(
            session, user_id=user_id, payload=body.model_dump(exclude_none=True)
        )}
    except (FeedbackError, FeedbackDailyLimitError) as exc:
        raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})


@feedback_router.get("")
async def list_feedback_endpoint(
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    return {"code": 0, "data": await list_user_feedbacks(session, user_id=user_id)}


__all__ = ["FeedbackCreate", "feedback_router"]
