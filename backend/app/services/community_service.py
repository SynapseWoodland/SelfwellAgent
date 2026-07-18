"""M6 蜕变广场 service。

真源：``docs/spec/TDS-M6-plaza-community.md``。
- post 状态机：pending → approved / rejected
- Redis 审核队列（async push）
- 24h ≤ 3 条限流
- 200 字 / 9 张图约束
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError, UserInputError
from app.core.log import logger
from app.db.models.post import Post
from app.errors.codes import (
    E_COMMUNITY_CONTENT_TOO_LONG,
    E_COMMUNITY_IMAGE_TOO_LARGE,
    E_COMMUNITY_IMAGES_TOO_MANY,
    E_COMMUNITY_INVALID_INPUT,
    E_COMMUNITY_POST_FREQUENT,
    E_COMMUNITY_POST_NOT_FOUND,
    E_COMMUNITY_POST_PENDING,
    E_COMMUNITY_POST_REJECTED,
)

MAX_CONTENT_LENGTH = 200
MAX_IMAGES = 9
MAX_DAILY_POSTS = 3
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5MB per image


class CommunityError(SelfwellError):
    """广场业务异常。"""

    code: str = E_COMMUNITY_INVALID_INPUT
    message_zh: str = "广场请求无效"
    message_en: str = "Invalid community request"
    severity = "USER_ERROR"
    http_status = 400


class PostNotFoundError(CommunityError):
    code: str = E_COMMUNITY_POST_NOT_FOUND
    message_zh: str = "动态不存在"
    message_en: str = "Post not found"
    http_status = 404


class PostPendingError(CommunityError):
    code: str = E_COMMUNITY_POST_PENDING
    message_zh: str = "动态审核中"
    message_en: str = "Post pending"
    http_status = 409


def _validate_content(text: str) -> str:
    if not text or not text.strip():
        raise UserInputError(
            "内容不能为空",
            code=E_COMMUNITY_INVALID_INPUT,
            field="content",
        )
    if len(text) > MAX_CONTENT_LENGTH:
        raise CommunityError(
            f"内容超长（{len(text)} > {MAX_CONTENT_LENGTH}）",
            code=E_COMMUNITY_CONTENT_TOO_LONG,
            field="content",
            limit=MAX_CONTENT_LENGTH,
        )
    return text.strip()


def _validate_images(images: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not images:
        return []
    if len(images) > MAX_IMAGES:
        raise CommunityError(
            f"图片数量超限（{len(images)} > {MAX_IMAGES}）",
            code=E_COMMUNITY_IMAGES_TOO_MANY,
            field="images",
            limit=MAX_IMAGES,
        )
    for idx, img in enumerate(images):
        size = int(img.get("size_bytes", 0) or 0)
        if size > MAX_IMAGE_BYTES:
            raise CommunityError(
                f"第 {idx + 1} 张图过大（{size // (1024 * 1024)}MB）",
                code=E_COMMUNITY_IMAGE_TOO_LARGE,
                field=f"images[{idx}]",
            )
        if not img.get("url"):
            raise UserInputError(
                f"第 {idx + 1} 张图 url 缺失",
                code=E_COMMUNITY_INVALID_INPUT,
                field=f"images[{idx}].url",
            )
    return images


async def create_post(
    session: AsyncSession,
    *,
    user_id: str,
    content: str,
    images: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """创建广场动态。"""
    content = _validate_content(content)
    images = _validate_images(images)

    # 24h 限流
    threshold = datetime.now(UTC) - timedelta(hours=24)
    stmt = (
        select(Post.id)
        .where(Post.user_id == user_id, Post.created_at >= threshold)
        .limit(MAX_DAILY_POSTS + 1)
    )
    result = await session.execute(stmt)
    if len(result.scalars().all()) > MAX_DAILY_POSTS:
        raise CommunityError(
            "今日发布已达上限",
            code=E_COMMUNITY_POST_FREQUENT,
            http_status=429,
        )

    now_ts = datetime.now(UTC)
    post = Post(
        id=uuid4(),
        user_id=user_id,
        content=content,
        images=images,
        status="pending",
        like_count=0,
        comment_count=0,
        created_at=now_ts,
        created_by=str(user_id),         # 当前创建用户（发帖人）
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(user_id),    # 当前更新用户
    )
    session.add(post)
    await session.flush()

    # 模拟 Redis 审核队列入队（生产用 redis.rpush）
    logger.info("post_enqueue_review_queue", post_id=str(post.id), user_id=user_id)

    return {
        "post_id": str(post.id),
        "status": post.status,
        "content": content,
        "images_count": len(images),
        "created_at": now_ts.isoformat(),
    }


async def list_posts(
    session: AsyncSession, *, limit: int = 20, offset: int = 0
) -> list[dict[str, Any]]:
    """列出已审核通过的广场动态。"""
    stmt = (
        select(Post)
        .where(Post.status == "approved", Post.deleted_at.is_(None))
        .order_by(Post.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return [
        {
            "post_id": str(p.id),
            "user_id": str(p.user_id),
            "content": p.content,
            "images": (p.images or {}).get("items", []) if isinstance(p.images, dict) else [],
            "like_count": p.like_count,
            "comment_count": p.comment_count,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in result.scalars().all()
    ]


async def get_post(session: AsyncSession, *, post_id: str) -> dict[str, Any]:
    """获取动态详情。"""
    stmt = select(Post).where(Post.id == post_id, Post.deleted_at.is_(None))
    result = await session.execute(stmt)
    post = result.scalar_one_or_none()
    if post is None:
        raise PostNotFoundError(field="post_id")
    if post.status == "pending":
        raise PostPendingError(field="post_id")
    return {
        "post_id": str(post.id),
        "user_id": str(post.user_id),
        "content": post.content,
        "images": (post.images or {}).get("items", []) if isinstance(post.images, dict) else [],
        "status": post.status,
        "like_count": post.like_count,
        "comment_count": post.comment_count,
        "created_at": post.created_at.isoformat() if post.created_at else None,
    }


async def like_post(session: AsyncSession, *, user_id: str, post_id: str) -> dict[str, Any]:
    """点赞（简化版：直接 +1，不去重，prod 用 Redis Set）。"""
    stmt = select(Post).where(Post.id == post_id, Post.deleted_at.is_(None))
    result = await session.execute(stmt)
    post = result.scalar_one_or_none()
    if post is None:
        raise PostNotFoundError(field="post_id")
    if post.status != "approved":
        raise CommunityError(
            "动态未通过审核",
            code=E_COMMUNITY_POST_REJECTED,
            http_status=409,
        )
    post.like_count = (post.like_count or 0) + 1
    post.last_updated_time = datetime.now(UTC)
    post.last_updated_by = str(user_id)  # 当前更新用户（点赞人）
    await session.flush()
    return {"post_id": str(post.id), "like_count": post.like_count}


__all__ = [
    "MAX_CONTENT_LENGTH",
    "MAX_DAILY_POSTS",
    "MAX_IMAGES",
    "MAX_IMAGE_BYTES",
    "CommunityError",
    "PostNotFoundError",
    "PostPendingError",
    "create_post",
    "get_post",
    "like_post",
    "list_posts",
]
