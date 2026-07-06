"""Sprint 3-4 routers: checkin, assistant, feedback, community, recall, share."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.services.assistant_service import (
    AssistantError,
    SessionClosedError,
    SessionNotFoundError,
    create_session,
    list_messages,
    send_message,
)
from app.services.checkin_service import CheckinError, create_checkin, list_user_checkins
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
from app.services.recall_service import RecallDailyLimitError, RecallError, generate_recall, get_recall
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
    plan_id: str
    day: int
    video_id: str
    feeling: str | None = None


class AssistantCreate(BaseModel):
    entry_card: str | None = None
    primary_intent: str = "general"


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
        return {"code": 0, "data": await create_checkin(
            session, user_id=user_id, **body.model_dump()
        )}
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
