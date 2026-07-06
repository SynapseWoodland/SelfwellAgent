"""M4 每日打卡 service。

真源：``docs/spec/SPEC-M4-checkin-loop.md`` + facts-anchor §4.
- 累积碎片 +1 / 连续天数
- 19:00 推送提醒
- 三档话术（warm / neutral / slight_hug）
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError, UserInputError
from app.core.log import logger
from app.db.models.checkin import Checkin
from app.db.models.plan import Plan
from app.db.models.user import User
from app.errors.codes import (
    E_CHECKIN_DAY_COMPLETED,
    E_CHECKIN_DAY_INVALID,
    E_CHECKIN_DUPLICATE,
    E_CHECKIN_FEELING_TOO_LONG,
    E_CHECKIN_INVALID_INPUT,
    E_CHECKIN_PLAN_NOT_FOUND,
    E_CHECKIN_RATE_LIMIT,
    E_CHECKIN_VIDEO_NOT_FOUND,
)

MAX_FEELING_LENGTH = 50
PLAN_LENGTH = 21


class CheckinError(SelfwellError):
    """打卡业务异常。"""

    code: str = E_CHECKIN_INVALID_INPUT
    message_zh: str = "打卡请求无效"
    message_en: str = "Invalid checkin request"
    severity = "USER_ERROR"
    http_status = 400


class CheckinRateLimitError(CheckinError):
    code: str = E_CHECKIN_RATE_LIMIT
    message_zh: str = "打卡过于频繁"
    message_en: str = "Checkin rate limit"
    http_status = 429


def _compute_message_tone(streak_days: int) -> str:
    """三档话术（PRD §3.4.2）。"""
    if streak_days <= 3:
        return "warm"
    if streak_days <= 14:
        return "neutral"
    return "slight_hug"


def _render_message(tone: str, streak_days: int, fragments: int) -> str:
    """三档话术文案。"""
    templates = {
        "warm": "今天打卡了！慢慢来，先从轻柔开始。",
        "neutral": f"已连续 {streak_days} 天，节奏很稳。碎片 {fragments} 颗，继续保持。",
        "slight_hug": f"已坚持 {streak_days} 天，每一次努力都算数。{fragments} 颗碎片为你加油。",
    }
    return templates.get(tone, templates["warm"])


async def _find_user(session: AsyncSession, user_id: str) -> User:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise UserInputError(
            "用户不存在",
            code="E_USER_NOT_FOUND",
            http_status=404,
            field="user_id",
        )
    return user


async def _find_plan(session: AsyncSession, user_id: str, plan_id: str) -> Plan:
    stmt = select(Plan).where(Plan.id == plan_id, Plan.user_id == user_id)
    result = await session.execute(stmt)
    plan = result.scalar_one_or_none()
    if plan is None or plan.deleted_at is not None:
        raise CheckinError(
            "方案不存在",
            code=E_CHECKIN_PLAN_NOT_FOUND,
            http_status=404,
        )
    return plan


async def create_checkin(
    session: AsyncSession,
    *,
    user_id: str,
    plan_id: str,
    day: int,
    video_id: str,
    feeling: str | None = None,
) -> dict[str, Any]:
    """用户打卡。"""
    # 1. 输入校验
    if day < 1 or day > PLAN_LENGTH:
        raise CheckinError(
            f"day 必须在 1-{PLAN_LENGTH}",
            code=E_CHECKIN_DAY_INVALID,
            field="day",
        )
    if feeling and len(feeling) > MAX_FEELING_LENGTH:
        raise CheckinError(
            f"feeling 超长（{len(feeling)} > {MAX_FEELING_LENGTH}）",
            code=E_CHECKIN_FEELING_TOO_LONG,
            field="feeling",
            limit=MAX_FEELING_LENGTH,
        )
    if not video_id:
        raise CheckinError(
            "video_id 缺失",
            code=E_CHECKIN_VIDEO_NOT_FOUND,
            field="video_id",
        )

    # 2. 加载 user / plan
    user = await _find_user(session, user_id)
    plan = await _find_plan(session, user_id, plan_id)

    # 3. 查重复打卡（同 plan + day + video）
    today = date.today()
    dup_stmt = (
        select(Checkin)
        .where(
            Checkin.user_id == user.id,
            Checkin.plan_id == plan_id,
            Checkin.day == day,
        )
        .limit(1)
    )
    dup_result = await session.execute(dup_stmt)
    existing = dup_result.scalar_one_or_none()
    if existing is not None:
        raise CheckinError(
            "今日已打卡，请勿重复提交",
            code=E_CHECKIN_DUPLICATE,
            http_status=409,
        )

    # 4. 检查 day 是否已完成（plan.days 中该 day 任务数 = 0）
    plan_days = plan.days.get("items", []) if isinstance(plan.days, dict) else []
    day_item = next((d for d in plan_days if d.get("day") == day), None)
    if day_item is not None and not day_item.get("tasks"):
        raise CheckinError(
            f"day {day} 已无可执行任务",
            code=E_CHECKIN_DAY_COMPLETED,
            http_status=409,
        )

    # 5. 写 checkin
    now_ts = datetime.now(UTC)
    checkin = Checkin(
        id=uuid4(),
        user_id=user.id,
        plan_id=plan_id,
        day=day,
        video_id=video_id,
        feeling=feeling,
        created_at=now_ts,
        created_by=str(user.id),
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by="M4",
    )
    session.add(checkin)

    # 6. 更新 user 碎片 + 连续天数
    fragments = int(user.report_cache.get("fragments", 0)) if user.report_cache else 0
    fragments += 1
    streak_days = int(user.report_cache.get("streak_days", 0)) if user.report_cache else 0
    streak_days += 1
    user.report_cache = {
        **(user.report_cache or {}),
        "fragments": fragments,
        "streak_days": streak_days,
        "last_checkin_date": today.isoformat(),
    }
    user.last_active_at = now_ts
    user.last_updated_time = now_ts

    await session.flush()

    # 7. 三档话术
    tone = _compute_message_tone(streak_days)
    message = _render_message(tone, streak_days, fragments)
    logger.info(
        "checkin_created",
        user_id=user_id,
        plan_id=plan_id,
        day=day,
        streak=streak_days,
        fragments=fragments,
    )
    return {
        "checkin_id": str(checkin.id),
        "day": day,
        "fragments": fragments,
        "streak_days": streak_days,
        "tone": tone,
        "message": message,
        "date": today.isoformat(),
    }


async def get_today_checkin(
    session: AsyncSession, *, user_id: str, plan_id: str, day: int
) -> dict[str, Any] | None:
    """查询指定 day 的打卡记录。"""
    stmt = (
        select(Checkin)
        .where(Checkin.user_id == user_id, Checkin.plan_id == plan_id, Checkin.day == day)
        .limit(1)
    )
    result = await session.execute(stmt)
    c = result.scalar_one_or_none()
    if c is None:
        return None
    return {
        "checkin_id": str(c.id),
        "day": c.day,
        "video_id": c.video_id,
        "feeling": c.feeling,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


async def list_user_checkins(
    session: AsyncSession, *, user_id: str, plan_id: str | None = None
) -> list[dict[str, Any]]:
    """列出用户所有打卡。"""
    stmt = select(Checkin).where(Checkin.user_id == user_id)
    if plan_id:
        stmt = stmt.where(Checkin.plan_id == plan_id)
    stmt = stmt.order_by(Checkin.created_at.desc()).limit(100)
    result = await session.execute(stmt)
    return [
        {
            "checkin_id": str(c.id),
            "plan_id": c.plan_id,
            "day": c.day,
            "video_id": c.video_id,
            "feeling": c.feeling,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in result.scalars().all()
    ]


__all__ = [
    "CheckinError",
    "CheckinRateLimitError",
    "MAX_FEELING_LENGTH",
    "PLAN_LENGTH",
    "create_checkin",
    "get_today_checkin",
    "list_user_checkins",
]
