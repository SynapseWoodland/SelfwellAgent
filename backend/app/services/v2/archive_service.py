"""V2 IA · Archive service（21 天小档案）。

真源：``plans/v2-unified-parent.md`` §2.2 + IA V2.2 §2A.3 #4 接口。

责任：聚合用户 21 天档案概要（基本信息 + 标签汇总 + 阶段小结）。
数据源：users + user_self_tags + plans + checkins + recall_sessions。

约定：
- 返回结构（PR-2 contract 锁）必须字段：
    - profile: { nickname, avatar, status }
    - tags: { body_part, concern, lifestyle, intensity } — 仅 is_selected=TRUE 的标签
    - plan: { active_plan_id, current_day, total_days, stage } | None
    - checkin: { total, streak_days, last_checkin_date }
    - archive_generated_at: ISO8601
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.checkin import Checkin
from app.db.models.plan import Plan
from app.db.models.user import User
from app.db.models.user_self_tag import UserSelfTag
from app.errors.codes import E_USER_NOT_FOUND

DAY_IN_PLAN = 21
PLAN_STAGES: tuple[tuple[int, str], ...] = (
    (7, "习惯启动"),
    (14, "稳步提升"),
    (21, "进阶养护"),
)


class ArchiveError(Exception):
    """档案聚合失败。"""

    def __init__(self, message: str, code: str = E_USER_NOT_FOUND, http_status: int = 404) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.message = message

    def render_zh(self) -> str:
        """中文文案（与 exception message 同源）。"""
        return self.message


def _stage_for(current_day: int) -> str:
    """根据 current_day 推断阶段。"""
    last_label = "刚刚开始"
    for threshold, label in PLAN_STAGES:
        if current_day <= threshold:
            return label
        last_label = label
    return last_label


async def get_archive_summary(
    session: AsyncSession, *, user_id: str
) -> dict[str, Any]:
    """21 天小档案聚合。

    Raises:
        ArchiveError 404: user 不存在

    """
    # 1. profile
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if user is None:
        raise ArchiveError("用户不存在")

    profile = {
        "nickname": user.nickname or "",
        "avatar": user.avatar or "",
        "status": user.status or "draft",
    }

    # 2. tags（按 category 分桶）
    tags_stmt = (
        select(UserSelfTag.tag_category, UserSelfTag.tag_value)
        .where(
            UserSelfTag.user_id == user_id,
            UserSelfTag.is_selected.is_(True),
            UserSelfTag.deleted_at.is_(None),
        )
        .order_by(UserSelfTag.tag_category, UserSelfTag.tag_value)
    )
    tags_result = await session.execute(tags_stmt)
    tags_buckets: dict[str, list[str]] = {
        "body_part": [],
        "concern": [],
        "lifestyle": [],
        "intensity": [],
    }
    for category, value in tags_result.all():
        if category in tags_buckets:
            tags_buckets[category].append(value)

    # 3. 当前方案
    plan_stmt = (
        select(Plan)
        .where(Plan.user_id == user_id, Plan.status == "active")
        .order_by(desc(Plan.created_at))
        .limit(1)
    )
    plan_result = await session.execute(plan_stmt)
    plan = plan_result.scalar_one_or_none()
    plan_block: dict[str, Any] | None
    if plan is None:
        plan_block = None
    else:
        # 计算 current_day = 已打卡 day 数（最大 day）+ 1（如果未完成）
        max_day_stmt = (
            select(func.coalesce(func.max(Checkin.day), 0))
            .where(Checkin.plan_id == str(plan.id), Checkin.user_id == user_id)
        )
        max_day_result = await session.execute(max_day_stmt)
        max_day = int(max_day_result.scalar_one() or 0)
        current_day = max_day + 1 if max_day < DAY_IN_PLAN else DAY_IN_PLAN
        plan_block = {
            "active_plan_id": str(plan.id),
            "current_day": current_day,
            "total_days": DAY_IN_PLAN,
            "stage": _stage_for(current_day),
            "started_at": plan.started_at.isoformat() if plan.started_at else None,
        }

    # 4. checkin 汇总
    total_checkin_stmt = (
        select(func.count())
        .select_from(Checkin)
        .where(Checkin.user_id == user_id)
    )
    total_checkin = int((await session.execute(total_checkin_stmt)).scalar_one() or 0)

    # streak_days = 最近连续打卡天数（按 created_time::date 倒序连续天数）
    recent_checkin_stmt = (
        select(func.date(Checkin.created_time).label("d"))
        .where(Checkin.user_id == user_id)
        .group_by(func.date(Checkin.created_time))
        .order_by(desc("d"))
        .limit(60)
    )
    recent_result = await session.execute(recent_checkin_stmt)
    checkin_dates = [row[0] for row in recent_result.all()]

    today = datetime.now(UTC).date()
    streak_days = 0
    if checkin_dates:
        # 第一项必须是 today 或 yesterday（否则 streak = 0）
        first_date = checkin_dates[0]
        if isinstance(first_date, str):
            first_date = datetime.fromisoformat(first_date).date()
        if (today - first_date).days > 1:
            streak_days = 0
        else:
            expected = first_date
            for d in checkin_dates:
                if isinstance(d, str):
                    d = datetime.fromisoformat(d).date()
                if d == expected:
                    streak_days += 1
                    expected = expected - __import__("datetime").timedelta(days=1)
                elif d < expected:
                    # 中断
                    break

    last_checkin_date = (
        checkin_dates[0].isoformat()
        if checkin_dates
        else None
    )

    return {
        "profile": profile,
        "tags": tags_buckets,
        "plan": plan_block,
        "checkin": {
            "total": total_checkin,
            "streak_days": streak_days,
            "last_checkin_date": last_checkin_date,
        },
        "archive_generated_at": datetime.now(UTC).isoformat(),
    }


__all__ = [
    "DAY_IN_PLAN",
    "PLAN_STAGES",
    "ArchiveError",
    "get_archive_summary",
]
