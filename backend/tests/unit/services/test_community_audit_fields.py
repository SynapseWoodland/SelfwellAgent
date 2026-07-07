"""Unit tests for ``app.services.community_service`` audit fields。

真源：本次 audit 整改
- post.created_by = str(user_id)           （发帖人）
- post.last_updated_by = str(user_id)       （发帖时即创建 + 更新）
- post.like_count +1 时：post.last_updated_by = str(user_id)  （点赞人）
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.community_service import create_post, like_post


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalars_result(values: list) -> MagicMock:
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
    return r


# ─────────────────────────────────────────────────────────────────────────────
# create_post
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_post_audit_fields_use_current_user_id() -> None:
    user_id = "u-author-1"
    session = AsyncMock()
    # 限流检查：返回 []（未超限）
    session.execute.return_value = _scalars_result([])
    session.flush = AsyncMock()
    session.add = MagicMock()

    await create_post(session, user_id=user_id, content="今天打卡啦")

    post = session.add.call_args[0][0]
    forbidden = {"M6", "M6-like", "m6", "community", "system"}
    assert post.created_by not in forbidden
    assert post.last_updated_by not in forbidden
    assert post.created_by == user_id
    assert post.last_updated_by == user_id


@pytest.mark.asyncio
async def test_create_post_audit_time_is_utc() -> None:
    user_id = "u-1"
    session = AsyncMock()
    session.execute.return_value = _scalars_result([])
    session.flush = AsyncMock()
    session.add = MagicMock()

    before = datetime.now(UTC)
    await create_post(session, user_id=user_id, content="hi")
    after = datetime.now(UTC)

    post = session.add.call_args[0][0]
    assert before <= post.created_time <= after
    assert before <= post.last_updated_time <= after


# ─────────────────────────────────────────────────────────────────────────────
# like_post：要点赞的人
# ─────────────────────────────────────────────────────────────────────────────
def _make_approved_post(post_id: str = "p-1", like_count: int = 0) -> MagicMock:
    post = MagicMock()
    post.id = post_id
    post.like_count = like_count
    post.status = "approved"
    post.deleted_at = None
    return post


@pytest.mark.asyncio
async def test_like_post_audit_last_updated_by_is_the_liker() -> None:
    """点赞时 last_updated_by 必须 = 点赞人 user_id，不能是 "M6-like" 字面量。"""
    liker_id = "u-liker-99"
    post = _make_approved_post()
    session = AsyncMock()
    session.execute.return_value = _scalar_result(post)
    session.flush = AsyncMock()

    await like_post(session, user_id=liker_id, post_id="p-1")

    forbidden = {"M6-like", "m6-like", "like", "system"}
    assert post.last_updated_by not in forbidden
    assert post.last_updated_by == liker_id


@pytest.mark.asyncio
async def test_like_post_increments_count_and_updates_audit_time() -> None:
    liker_id = "u-1"
    post = _make_approved_post(like_count=3)
    session = AsyncMock()
    session.execute.return_value = _scalar_result(post)
    session.flush = AsyncMock()

    before = datetime.now(UTC)
    await like_post(session, user_id=liker_id, post_id="p-1")
    after = datetime.now(UTC)

    assert post.like_count == 4
    assert before <= post.last_updated_time <= after
