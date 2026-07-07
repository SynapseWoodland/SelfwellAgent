"""Sprint 3-4 routers: checkin, assistant, feedback, community, recall, share."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.services.assistant_service import (
    DEFAULT_PRIMARY_INTENT,
    AssistantError,
    SessionClosedError,
    SessionNotFoundError,
    create_session,
    list_messages,
    send_message,
)
from app.services.checkin_service import (
    CheckinError,
    create_checkin,
    get_today_checkin_summary,
    list_user_checkins,
)
from app.services.community_service import (
    CommunityError,
    PostNotFoundError,
    PostPendingError,
    create_post,
    get_post,
    like_post,
    list_posts,
)
from app.services.feedback_service import (
    FeedbackDailyLimitError,
    FeedbackError,
    create_feedback,
    list_user_feedbacks,
)
from app.services.plan_service import get_today_plan_tasks
from app.services.recall_service import (
    RecallDailyLimitError,
    RecallError,
    generate_recall,
    get_recall,
)
from app.services.share_service import ShareError, generate_hug_card, get_template_meta

# Sprint 3
checkin_router = APIRouter(prefix="/checkins", tags=["checkin"])
assistant_router = APIRouter(prefix="/assistant", tags=["assistant"])
feedback_router = APIRouter(prefix="/feedback", tags=["feedback"])

# Sprint 4
community_router = APIRouter(prefix="/community", tags=["community"])
butler_router = APIRouter(prefix="/butler", tags=["butler"])
share_router = APIRouter(prefix="/share", tags=["share"])


# ── Schemas ─────────────────────────────────────────────────────────────────
class CheckinCreate(BaseModel):
    """MVP 打卡请求 Schema（兼容前端 v2 + 原生后端两种格式）。

    前端 v2 传参（来自 checkin/index.ts §17.15）：
        { date: ISODate, task_ids: string[], mood_text?: string }

    原生后端传参（兼容旧调用方）：
        { plan_id: str, day: int, video_id: str, feeling?: str }

    MVP 优先策略：前端体验不变，后端同时支持两种格式。
    task_ids 多选时，拆成多条打卡记录。
    """

    # ── 前端 v2 格式字段 ──────────────────────────────────────────────────────
    date: str | None = Field(default=None, description="ISO 日期 YYYY-MM-DD（前端传）")
    task_ids: list[str] | None = Field(default=None, description="任务 ID 列表（前端传）")
    mood_text: str | None = Field(default=None, description="心情文本（前端传）")

    # ── 原生后端格式字段（保留兼容）─────────────────────────────────────────────
    plan_id: str | None = Field(default=None, description="方案 ID（原生格式）")
    day: int | None = Field(default=None, ge=1, le=21, description="第几天（原生格式）")
    video_id: str | None = Field(default=None, description="视频 ID（原生格式）")
    feeling: str | None = Field(default=None, description="心情文本（原生格式）")

    @model_validator(mode="after")
    def validate_schema(self) -> "CheckinCreate":
        """必须满足两种格式之一：前端 v2 格式 OR 原生后端格式。"""
        has_v2 = self.date is not None and self.task_ids is not None
        has_native = (
            self.plan_id is not None
            and self.day is not None
            and self.video_id is not None
        )
        if not has_v2 and not has_native:
            raise ValueError(
                "必须提供前端格式（date + task_ids）或原生格式（plan_id + day + video_id）"
            )
        return self

    def to_backend_format(self) -> dict:
        """将原生格式转为 service 层参数（前端格式由 endpoint 层处理）。

        前端格式调用时抛 :class:`pydantic.ValidationError`,因为契约上
        ``to_backend_format`` 只接受原生后端字段。
        """
        if self.plan_id is None or self.day is None or self.video_id is None:
            err = ValueError(
                "to_backend_format 需要原生格式字段 (plan_id, day, video_id)"
            )
            payload: list[dict] = [
                {
                    "type": "missing",
                    "loc": ("to_backend_format",),
                    "input": {},
                    "ctx": {"error": err},
                }
            ]
            raise ValidationError.from_exception_data(  # type: ignore[attr-defined]
                self.__class__.__name__,
                payload,
            )
        return {
            "plan_id": self.plan_id,
            "day": self.day,
            "video_id": self.video_id,
            "feeling": self.feeling,
        }


class AssistantCreate(BaseModel):
    """M5 智能管家 - 创建会话请求 Schema。

    字段默认值与 DDL ``chk_ai_session_intent`` / ``chk_ai_session_entry`` 强一致：
    - ``entry_card`` 为 NULL（默认）时走"自由输入"路径，DDL 允许
    - ``primary_intent`` 默认 ``"unknown"``（DDL 允许；前端若传 ``general``/``chat``/``checkin`` 等
      历史值，由 service 层 ``_normalize_primary_intent()`` 兜底映射到合法白名单）

    See Also:
        - ``docs/bugfix/mvp-bugfix-record.md`` §八 阶段三（2026-07-07）

    """

    entry_card: str | None = None
    primary_intent: str = DEFAULT_PRIMARY_INTENT


class AssistantMessage(BaseModel):
    text: str


class FeedbackCreate(BaseModel):
    feedback_type: str
    text_content: str | None = None
    photo_url: str | None = None
    photo_size_bytes: int | None = None
    body_part: str | None = None


class PostCreate(BaseModel):
    content: str
    images: list[dict] | None = None


class HugCardRequest(BaseModel):
    day: int
    nickname: str = "我"
    stats: dict | None = None


# ── M4 Checkin ──────────────────────────────────────────────────────────────
@checkin_router.post("")
async def create_checkin_endpoint(
    body: CheckinCreate,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    try:
        if body.task_ids is not None and body.plan_id is None:
            plan_data = await get_today_plan_tasks(session, user_id=user_id, day_index=body.day or 1)
            plan_id = plan_data.get("plan_id", "")
            task_video_map: dict[str, str] = {}
            for task in plan_data.get("tasks", []):
                if isinstance(task, dict) and "task_id" in task and "video_id" in task:
                    task_video_map[task["task_id"]] = task["video_id"]
            first_task_id = body.task_ids[0] if body.task_ids else ""
            video_id = task_video_map.get(first_task_id, first_task_id)
            backend_params = {
                "plan_id": plan_id,
                "day": body.day or 1,
                "video_id": video_id,
                "feeling": body.mood_text,
            }
        else:
            backend_params = {
                "plan_id": body.plan_id or "",
                "day": body.day or 1,
                "video_id": body.video_id or "",
                "feeling": body.feeling,
            }
        result = await create_checkin(session, user_id=user_id, **backend_params)
        return {
            "code": 0,
            "data": {
                "checkin_id": result.get("checkin_id"),
                "new_streak": result.get("streak_days", 0),
                "ack_text": result.get("message", ""),
            },
        }
    except CheckinError as exc:
        raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})


@checkin_router.get("")
async def list_checkin_endpoint(
    plan_id: str | None = None,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    return {
        "code": 0,
        "data": await list_user_checkins(session, user_id=user_id, plan_id=plan_id),
    }


@checkin_router.get("/today", summary="今日打卡进度（home 页用）")
async def today_checkin_endpoint(
    day: int = 1,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    """返回 ``{date, total, done, percent, done_task_ids}``。无 plan 时全为 0。"""
    data = await get_today_checkin_summary(session, user_id=user_id, day_index=day)
    return {"code": 0, "data": data}


# ── M5 Assistant ────────────────────────────────────────────────────────────
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


@assistant_router.post("/sessions/{session_id}/messages")
async def send_message_endpoint(
    session_id: str,
    body: AssistantMessage,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    try:
        return {
            "code": 0,
            "data": await send_message(session, user_id=user_id, session_id=session_id, text=body.text),
        }
    except (AssistantError, SessionNotFoundError, SessionClosedError) as exc:
        raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})


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


# ── M7 Feedback ─────────────────────────────────────────────────────────────
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


# ── M6 Community ────────────────────────────────────────────────────────────
@community_router.get("/posts")
async def list_posts_endpoint(
    limit: int = 20,
    offset: int = 0,
    _user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    return {"code": 0, "data": await list_posts(session, limit=limit, offset=offset)}


@community_router.post("/posts")
async def create_post_endpoint(
    body: PostCreate,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    try:
        return {
            "code": 0,
            "data": await create_post(
                session, user_id=user_id, content=body.content, images=body.images or []
            ),
        }
    except CommunityError as exc:
        raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})


@community_router.get("/posts/{post_id}")
async def get_post_endpoint(
    post_id: str,
    _user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    try:
        return {"code": 0, "data": await get_post(session, post_id=post_id)}
    except (PostNotFoundError, PostPendingError, CommunityError) as exc:
        raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})


@community_router.post("/posts/{post_id}/like")
async def like_post_endpoint(
    post_id: str,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    try:
        return {
            "code": 0,
            "data": await like_post(session, user_id=user_id, post_id=post_id),
        }
    except (PostNotFoundError, CommunityError) as exc:
        raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})


# ── M8 Butler Recall ────────────────────────────────────────────────────────
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


# ── M10 Share ───────────────────────────────────────────────────────────────
@share_router.post("/hug-card")
async def hug_card_endpoint(body: HugCardRequest, _user_id: str = Depends(current_user_id)) -> dict:
    try:
        return {
            "code": 0,
            "data": await generate_hug_card(
                user_id=_user_id, day=body.day, nickname=body.nickname, stats=body.stats
            ),
        }
    except ShareError as exc:
        raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})


@share_router.get("/hug-card/{day}/template")
async def hug_card_template_endpoint(day: int) -> dict:
    try:
        return {"code": 0, "data": await get_template_meta(day)}
    except ShareError as exc:
        raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})


__all__ = [
    "assistant_router",
    "butler_router",
    "checkin_router",
    "community_router",
    "feedback_router",
    "share_router",
]
