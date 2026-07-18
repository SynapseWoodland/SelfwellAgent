"""草稿用户 24h 自动转正 job（M1-FR-06 / AC-M1-03）。

真源：``docs/spec/TDS-M1-wechat-login.md`` §5.1。

转正条件（任一满足）：
- 至少 1 条 ``feedback`` 记录
- ``last_active_at`` 与 ``created_at`` 差 ≥ 24h
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log import logger
from app.db.models.feedback import Feedback
from app.db.models.user import User

DRAFT_TTL_HOURS = 24


async def promote_due_drafts(session: AsyncSession) -> int:
    """把符合条件的 draft 用户转正。

    Returns:
        转正的用户数量。

    """
    threshold = datetime.now(UTC) - timedelta(hours=DRAFT_TTL_HOURS)

    # 1. 拿所有 draft 用户
    stmt = select(User).where(User.status == "draft")
    result = await session.execute(stmt)
    draft_users = result.scalars().all()
    if not draft_users:
        return 0

    promoted = 0
    for user in draft_users:
        should_promote = False
        if user.created_at and user.created_at <= threshold:
            # 24h 到期
            should_promote = True
        else:
            # 查 feedback 记录
            fb_stmt = select(Feedback).where(Feedback.user_id == str(user.id)).limit(1)
            fb_result = await session.execute(fb_stmt)
            if fb_result.scalar_one_or_none() is not None:
                should_promote = True
        if should_promote:
            user.status = "active"
            user.last_updated_time = datetime.now(UTC)
            user.last_updated_by = "cron:promote-drafts"
            promoted += 1
            logger.info("draft_user_promoted", user_id=str(user.id))

    if promoted:
        await session.flush()
    return promoted


__all__ = [
    "DRAFT_TTL_HOURS",
    "promote_due_drafts",
]
