"""M8 主动回忆路由（``/api/v1/butler`` recall 部分）。

V1.1.1：新增 ``GET /recall/history`` 与 ``GET /recall/{id}/messages``，
对齐 ``docs/api/openapi.yaml``。

错误处理约定：router 不做 ``XxxError -> AppBusinessError`` 的 re-wrap，
所有 ``SelfwellError`` 子类（含 ``RecallError`` / ``RecallDailyLimitError`` /
``AssistantError`` 等）冒泡到 ``app.api.middleware.ExceptionHandlerMiddleware``
后统一渲染 envelope（service 异常已自带 ``code/http_status/message_zh``）。
仅业务校验分支直接 ``raise AppBusinessError(...)``（如 404 / 403）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.db.models.ai_messages import AIMessage
from app.db.models.ai_sessions import AISession
from app.db.models.recall_sessions import RecallSession
from app.errors.codes import E_RECALL_NOT_FOUND
from app.errors.envelope import AppBusinessError
from app.services.recall_service import generate_recall, get_recall

butler_router = APIRouter(prefix="/butler", tags=["butler"])


class RecallGenerateRequest(BaseModel):
    """Request contract for a manual or scheduled recall."""

    trigger: str = "user_manual"
    plan_id: str | None = None
    days_offset: int = Field(default=7, ge=1, le=365)


@butler_router.post("/recall")
async def generate_recall_endpoint(
    body: RecallGenerateRequest | None = None,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict[str, object]:
    """生成一次主动回忆。

    Raises:
        RecallError / RecallDailyLimitError: 由 ``ExceptionHandlerMiddleware``
            接管为标准 envelope；service 异常已自带 ``code/http_status/message_zh``，
            router 不做 re-wrap 避免上下文丢失。

    """
    payload = body or RecallGenerateRequest()
    return {
        "code": 0,
        "data": await generate_recall(
            session,
            user_id=user_id,
            trigger=payload.trigger,
            plan_id=payload.plan_id,
            days_offset=payload.days_offset,
        ),
    }


@butler_router.get("/recall/day/{day}")
async def get_recall_by_day_endpoint(
    day: int,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict[str, object]:
    from app.services.recall_service import get_recall_by_day

    data = await get_recall_by_day(session, user_id=user_id, day=day)
    return {"code": 0, "data": data or {}}


@butler_router.get("/recall/history")
async def list_recall_history_endpoint(
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict[str, object]:
    """V1.1.1：用户主动回忆历史（分页）。"""
    stmt = (
        select(RecallSession)
        .where(
            RecallSession.user_id == user_id,
            RecallSession.deleted_at.is_(None),
        )
        .order_by(RecallSession.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    sessions = result.scalars().all()
    items: list[dict[str, Any]] = [
        {
            "recall_id": str(rs.id),
            "trigger": rs.trigger,
            "summary": rs.ai_summary,
            "encourage": rs.ai_encourage,
            "safety_passed": rs.safety_passed,
            "created_at": rs.created_at.isoformat() if rs.created_at else None,
        }
        for rs in sessions
    ]
    return {
        "code": 0,
        "data": {"items": items, "pagination": {"limit": limit, "offset": offset}},
    }


@butler_router.get("/recall/{recall_id}")
async def get_recall_endpoint(
    recall_id: str,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict[str, object]:
    """按 recall_id 返回一次主动回忆。

    Raises:
        RecallError: 由 ``ExceptionHandlerMiddleware`` 接管。

    """
    return {"code": 0, "data": await get_recall(session, user_id=user_id, recall_id=recall_id)}


@butler_router.get("/recall/{recall_id}/messages")
async def get_recall_messages_endpoint(
    recall_id: str,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict[str, object]:
    """V1.1.1：单次回忆的完整对话流（recall_session + ai_session + messages[]）。

    Raises:
        AppBusinessError 404: recall_session 不存在或归属不符。

    """
    stmt = select(RecallSession).where(
        RecallSession.id == recall_id,
        RecallSession.deleted_at.is_(None),
    )
    rs = (await session.execute(stmt)).scalar_one_or_none()
    if rs is None:
        raise AppBusinessError(
            code=E_RECALL_NOT_FOUND,
            message_zh="主动回忆记录不存在",
            http_status=404,
        )
    if str(rs.user_id) != str(user_id):
        raise AppBusinessError(
            code="E_GENERAL_FORBIDDEN",
            message_zh="无权查看他人回忆",
            http_status=403,
        )

    ai_session_data: dict[str, Any] = {}
    messages: list[dict[str, Any]] = []
    if rs.ai_session_id is not None:
        ai_stmt = select(AISession).where(AISession.id == rs.ai_session_id)
        ai_session = (await session.execute(ai_stmt)).scalar_one_or_none()
        if ai_session is not None:
            ai_session_data = {
                "id": str(ai_session.id),
                "persona_state_start": ai_session.persona_state_start,
                "persona_state_end": ai_session.persona_state_end,
                "message_count": ai_session.message_count,
            }
        msg_stmt = (
            select(AIMessage)
            .where(AIMessage.session_id == rs.ai_session_id)
            .order_by(AIMessage.seq.asc())
        )
        for m in (await session.execute(msg_stmt)).scalars().all():
            messages.append(
                {
                    "seq": m.seq,
                    "role": m.role,
                    "content": m.content,
                    "trigger": m.trigger,
                    "intent": m.intent,
                    "referenced_feedback_ids": [
                        str(fid) for fid in (m.referenced_feedback_ids or [])
                    ],
                    "safety_passed": m.safety_passed,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
            )

    return {
        "code": 0,
        "data": {
            "recall_session": {
                "recall_id": str(rs.id),
                "trigger": rs.trigger,
                "summary": rs.ai_summary,
                "encourage": rs.ai_encourage,
                "safety_passed": rs.safety_passed,
                "created_at": rs.created_at.isoformat() if rs.created_at else None,
            },
            "session": ai_session_data,
            "messages": messages,
        },
    }


__all__ = ["RecallGenerateRequest", "butler_router"]
