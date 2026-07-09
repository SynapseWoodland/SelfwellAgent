"""M6 社区路由（``/api/v1/community``）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.services.community_service import (
    CommunityError,
    PostNotFoundError,
    PostPendingError,
    create_post,
    get_post,
    like_post,
    list_posts,
)

community_router = APIRouter(prefix="/community", tags=["community"])


class PostCreate(BaseModel):
    content: str
    images: list[dict] | None = None


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


__all__ = ["PostCreate", "community_router"]
