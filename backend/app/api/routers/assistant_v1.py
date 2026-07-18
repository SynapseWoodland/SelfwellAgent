"""M5 智能管家路由（``/api/v1/assistant``）。

真源：``docs/spec/TDS-M5-persona-chat.md`` + ADR-0015。

PR-A2（worker C）增量：``POST /sessions/{id}/messages`` 切换为 ``StreamingResponse``，
事件序列见 ``assistant_service.send_message_stream`` 注释（start/progress/report/end/error）。

错误处理约定：router 不做 ``XxxError -> AppBusinessError`` 的 re-wrap，
所有 ``SelfwellError`` 子类（``AssistantError`` / ``SessionNotFoundError`` /
``SessionClosedError`` 等）冒泡到 ``app.api.middleware.ExceptionHandlerMiddleware``
后由统一的 envelope handler 渲染响应。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session, get_redis
from app.core.ratelimit import (
    RateLimitExceeded,
    build_key,
    check_rate_limit,
    raise_if_exceeded,
)
from app.services.assistant_service import (
    DEFAULT_PRIMARY_INTENT,
    SessionClosedError,
    SessionNotFoundError,
    create_session,
    list_messages,
    send_message_stream,
)

assistant_router = APIRouter(prefix="/assistant", tags=["assistant"])


async def _wrap_sse_with_disconnect_tracking(endpoint: str, inner):
    """包装一个 SSE async generator，记录提前断连。

    Phase 4 批次 4：当 client 在 ``end`` 事件之前断开（EventSource reconnect、
    浏览器切后台、网络中断），正常 ``yield`` 路径会抛
    ``httpx.ConnectError`` / ``GeneratorExit`` 等。我们在此捕获并计
    ``SSE_DISCONNECTED_TOTAL{reason=...}``，方便排查前端无声丢流。
    """
    saw_end = False
    saw_error = False
    try:
        async for chunk in inner:
            # 简单判断：本帧是否以 "event: end" / "event: error" 开头
            # （避免依赖 service 层结构改动）
            try:
                head = chunk.split("\n", 1)[0]
            except Exception:
                head = ""
            if head.startswith("event: end"):
                saw_end = True
            elif head.startswith("event: error"):
                saw_error = True
            yield chunk
    except GeneratorExit:
        # client 主动断开
        if not saw_end and not saw_error:
            try:
                from app.core.log import logger
                from app.core.observability import observe_sse_disconnect

                observe_sse_disconnect(endpoint=endpoint, reason="client_closed")
            except Exception as exc_inner:
                logger.debug(
                    "sse_disconnect_observe_failed",
                    exc_type=type(exc_inner).__name__,
                )
        raise
    except Exception as exc:  # pragma: no cover - 保护路径
        if not saw_end and not saw_error:
            try:
                from app.core.log import logger
                from app.core.observability import observe_sse_disconnect

                observe_sse_disconnect(endpoint=endpoint, reason=f"exc:{type(exc).__name__}")
            except Exception as exc_inner:
                logger.debug(
                    "sse_disconnect_observe_failed",
                    exc_type=type(exc_inner).__name__,
                )
        raise


class AssistantCreate(BaseModel):
    """M5 智能管家 - 创建会话请求 Schema。

    字段默认值与 DDL ``chk_ai_session_intent`` / ``chk_ai_session_entry`` 强一致。
    """

    entry_card: str | None = None
    primary_intent: str = DEFAULT_PRIMARY_INTENT


class AssistantMessage(BaseModel):
    """智能管家消息请求。

    字段：
    - text: 消息内容。smart_analyze 模式下为 '智能分析' 等描述性文本。
    - image_keys: 图片 object_key 列表（可选）。有值时触发 smart_analyze 模式。
    - body_parts: 部位标签列表（可选），如 ['face', 'neck']。
    """

    text: str
    image_keys: list[str] = Field(default_factory=list, max_length=3)
    body_parts: list[str] = Field(default_factory=list, max_length=3)

    @field_validator("image_keys")
    @classmethod
    def _validate_image_keys(cls, v: list[str]) -> list[str]:
        if len(v) > 3:
            raise ValueError("image_keys 最多 3 张")
        for k in v:
            if not k.startswith(("assistant/", "diagnosis/")):
                raise ValueError(f"非法 object_key 前缀: {k}")
        return v


@assistant_router.post("/sessions")
async def create_session_endpoint(
    body: AssistantCreate,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    return {"code": 0, "data": await create_session(session, user_id=user_id, **body.model_dump())}


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
    redis: Redis = Depends(get_redis),
) -> StreamingResponse:
    """SSE 流式返回智能管家回复。

    事件 schema（chat 模式）：
      token_delta data: {"token": "单字"}
      end        data: {"ok": true, "reply": "...", "persona_state": "...", "medical_guarded"?: bool}

    事件 schema（smart_analyze 模式）：
      start      data: {"step": 0}
      progress   data: {"step": 1|2|3, "percent": 33|66|100, "label": "..."}
      report     data: {"directions": [{num, title, level, description}, ...]}
      end        data: {"ok": true, "reply": "...", "persona_state": "...", "medical_guarded"?: bool}

    模式路由：
      - image_keys 有值 → smart_analyze 模式
      - image_keys 为空 → chat 模式（token_delta 流）

    限流（Step 1.6）：
      - per-user sliding window：60s window 内最多 5 次（5 RPS = 合理 chat 打字速度上限）
      - 超出返回 429 + Retry-After 头，envelope error.code = E_ASSISTANT_RATE_LIMIT

    会话不存在 / 已关闭 → 在进入流之前以 HTTPException 抛出（保留 404 / 410 语义）。
    其它业务异常 → 在流中以 error 事件下发（前端可识别并 toast）。
    """
    # ── 限流（Step 1.6）：per-user 5RPM ───────────────────────────────────
    rl_key = build_key("chat", user_id)
    try:
        decision = await check_rate_limit(redis, rl_key, limit=5, window_sec=10)
        raise_if_exceeded(decision, action="chat", key=rl_key)
    except RateLimitExceeded as exc:
        # 直接返回带 Retry-After 的 429（绕过 SSE StreamingResponse）
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": exc.code,
                    "message_zh": exc.message_zh,
                    "message_en": "Rate limit exceeded, please retry later",
                }
            },
            headers={"Retry-After": str(exc.retry_after_sec)},
        )

    await _assert_ai_session_open(session, session_id=session_id, user_id=user_id)

    return StreamingResponse(
        _wrap_sse_with_disconnect_tracking(
            "assistant.send_message_stream",
            send_message_stream(
                session,
                user_id=user_id,
                session_id=session_id,
                text=body.text,
                image_keys=body.image_keys,
                body_parts=body.body_parts,
            ),
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


async def _assert_ai_session_open(
    session: AsyncSession,
    *,
    session_id: str,
    user_id: str,
) -> None:
    """加载 ai_session 并断言其未关闭。

    失败抛 :class:`SessionNotFoundError` / :class:`SessionClosedError`，
    由 ``ExceptionHandlerMiddleware`` 统一渲染 envelope。
    """
    from uuid import UUID

    from sqlalchemy import select

    from app.db.models.ai_sessions import AISession

    stmt = select(AISession).where(AISession.id == session_id, AISession.user_id == user_id)
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

    cards = compute_entry_state(session, user_id=user_id, recent_feedbacks=[], latest_report=None)
    return {"code": 0, "data": cards}


__all__ = ["AssistantCreate", "AssistantMessage", "assistant_router"]
