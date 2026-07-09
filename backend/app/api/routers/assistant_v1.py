"""M5 智能管家路由（``/api/v1/assistant``）。

真源：``docs/spec/SPEC-M5-persona-chat.md`` + ADR-0015。

PR-A2（worker C）增量：``POST /sessions/{id}/messages`` 切换为 ``StreamingResponse``，
事件序列见 ``assistant_service.send_message_stream`` 注释（start/progress/report/end/error）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.services.assistant_service import (
    DEFAULT_PRIMARY_INTENT,
    AssistantError,
    SessionClosedError,
    SessionNotFoundError,
    create_session,
    list_messages,
    send_message_stream,
)

assistant_router = APIRouter(prefix="/assistant", tags=["assistant"])


class AssistantCreate(BaseModel):
    """M5 智能管家 - 创建会话请求 Schema。

    字段默认值与 DDL ``chk_ai_session_intent`` / ``chk_ai_session_entry`` 强一致。
    """

    entry_card: str | None = None
    primary_intent: str = DEFAULT_PRIMARY_INTENT


class AssistantMessage(BaseModel):
    text: str


@assistant_router.post("/sessions")
async def create_session_endpoint(
    body: AssistantCreate,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    try:
        return {"code": 0, "data": await create_session(
            session, user_id=user_id, **body.model_dump()
        )}
    except AssistantError as exc:
        raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})


@assistant_router.post(
    "/sessions/{session_id}/messages",
    summary="发送消息（SSE 流式回复，PR-A2）",
    response_class=StreamingResponse,
)
async def send_message_endpoint(
    session_id: str,
    body: AssistantMessage,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> StreamingResponse:
    """SSE 流式返回智能管家回复（事件：start / progress / report / end / error）。

    事件 schema：
      start    data: {"step": 0}
      progress data: {"step": 1|2|3, "percent": 33|66|100, "label": "..."}
      report   data: {"directions": [{num, title, level, description}, ...]}
      end      data: {"ok": true, "reply": "...", "persona_state": "...", "medical_guarded"?: bool}
      error    data: {"code": "E_*", "message_zh": "..."}

    会话不存在 / 已关闭 → 在进入流之前以 HTTPException 抛出（保留 404 / 410 语义）。
    其它业务异常 → 在流中以 error 事件下发（前端可识别并 toast）。
    """
    try:
        # 同步路径失败但保留 SSE：把基本校验留给 stream 内部；
        # 仅 session 缺失 / 关闭提前拦截，避免返回空流后才告知 404。
        from app.db.models.ai_sessions import AISession  # noqa: PLC0415
        from sqlalchemy import select  # noqa: PLC0415
        from uuid import UUID  # noqa: PLC0415

        stmt = select(AISession).where(
            AISession.id == session_id, AISession.user_id == user_id
        )
        result = await session.execute(stmt)
        ai_session = result.scalar_one_or_none()
        if ai_session is None:
            try:
                session_uuid = UUID(str(session_id))
                user_uuid = UUID(str(user_id))
            except ValueError as exc:
                raise SessionNotFoundError(field="session_id") from exc
            stmt_uuid = select(AISession).where(
                AISession.id == session_uuid, AISession.user_id == user_uuid
            )
            result = await session.execute(stmt_uuid)
            ai_session = result.scalar_one_or_none()
        if ai_session is None:
            raise SessionNotFoundError(field="session_id")
        if not ai_session.user_active or ai_session.closed_at is not None:
            raise SessionClosedError(field="session_id")
    except (SessionNotFoundError, SessionClosedError) as exc:
        raise HTTPException(
            exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()}
        )

    return StreamingResponse(
        send_message_stream(
            session,
            user_id=user_id,
            session_id=session_id,
            text=body.text,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@assistant_router.get("/sessions/{session_id}/messages")
async def list_messages_endpoint(
    session_id: str,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    return {
        "code": 0,
        "data": await list_messages(session, user_id=user_id, session_id=session_id),
    }


@assistant_router.get("/entry-state", summary="智能管家入口卡 4 状态")
async def entry_state_endpoint(
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    """返回 4 张入口卡的当前状态。

    实现委托 ``assistant_service.compute_entry_state``。
    """
    from app.services.assistant_service import compute_entry_state

    cards = compute_entry_state(
        session, user_id=user_id, recent_feedbacks=[], latest_report=None
    )
    return {"code": 0, "data": cards}


__all__ = ["AssistantCreate", "AssistantMessage", "assistant_router"]
