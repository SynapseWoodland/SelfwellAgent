"""M7 反馈路由（``/api/v1/feedback``）。

V1.1.1：GET 端点支持 ``X-Caller-Id`` 白名单校验
（``mood_diary_list / recall_retrieve / time_album_list``），
对齐 ``docs/architecture/api.yaml``。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
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

# GET /feedback 允许的 caller 白名单（与 openapi.yaml 一致）
_ALLOWED_LIST_CALLERS: frozenset[str] = frozenset(
    {"mood_diary_list", "recall_retrieve", "time_album_list"}
)


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
    x_caller_id: Annotated[
        str | None,
        Header(alias="X-Caller-Id", description="调用方标识（白名单校验）"),
    ] = None,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    if x_caller_id is None or x_caller_id not in _ALLOWED_LIST_CALLERS:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "E_GENERAL_FORBIDDEN",
                "message_zh": "X-Caller-Id 不在白名单中",
            },
        )
    return {"code": 0, "data": await list_user_feedbacks(session, user_id=user_id)}


__all__ = ["FeedbackCreate", "feedback_router"]