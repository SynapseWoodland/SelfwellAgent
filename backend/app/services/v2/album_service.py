"""V2 IA · Album service（时光相册照片 + 统计）。

真源：``plans/v2-unified-parent.md`` §2.2 + IA V2.2 §2A.3 #2 / #3 接口
+ 现有 ``feedback`` 表（V2 复用 M7 photo_url 字段作为相册照片）。

责任：
- 按周（YYYY-WNN）取相册照片
- 聚合统计：总照片数 / 连续天数 / 日记数 / 在 App 天数

约定：
- 相册照片来源 = feedback.photo_url IS NOT NULL（不限 type）
- 顺序：created_time DESC
- 周格式：ISO 周 ``YYYY-WNN``（与日历库无关；纯字符串解析）
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError
from app.db.models.checkin import Checkin
from app.db.models.feedback import Feedback
from app.db.models.user import User
from app.errors.codes import E_ALBUM_WEEK_FORMAT, E_USER_INVALID_INPUT

WEEK_PATTERN = re.compile(r"^(\d{4})-W(\d{2})$")
PHOTO_TYPES: frozenset[str] = frozenset(
    {"mood_photo", "period_photo", "plan_compare_photo"}
)


class AlbumError(SelfwellError):
    """相册业务异常。"""

    code: str = E_USER_INVALID_INPUT
    message_zh: str = "相册操作失败"
    message_en: str = "Album operation failed"
    severity = "USER_ERROR"
    http_status = 400


class AlbumWeekFormatError(AlbumError):
    """week 参数格式非法。"""

    code: str = E_ALBUM_WEEK_FORMAT
    message_zh: str = "week 参数必须是 YYYY-WNN 格式"
    message_en: str = "week must be YYYY-WNN"
    http_status = 400


def _parse_week(week: str) -> tuple[int, int]:
    """解析 ``YYYY-WNN`` → (year, week_num)。"""
    match = WEEK_PATTERN.match(week)
    if not match:
        raise AlbumWeekFormatError(field="week", week=week)
    return int(match.group(1)), int(match.group(2))


def _week_range(year: int, week: int) -> tuple[datetime, datetime]:
    """ISO 周 → 起止 datetime（UTC）。"""
    # ISO 周一作为周首日
    from datetime import date

    try:
        monday = date.fromisocalendar(year, week, 1)
    except ValueError as exc:
        raise AlbumWeekFormatError(
            f"week 解析失败：{year}-W{week}", field="week"
        ) from exc
    start = datetime(monday.year, monday.month, monday.day, tzinfo=UTC)
    end = start + timedelta(days=7)
    return start, end


async def list_album_photos_by_week(
    session: AsyncSession, *, user_id: str, week: str
) -> dict[str, Any]:
    """按 ISO 周（YYYY-WNN）取相册照片。

    照片源 = feedback.photo_url IS NOT NULL；不限 feedback_type。

    返回结构（PR-2 contract 锁）：
    - week: "2026-W28"
    - count: int
    - photos: list[{ feedback_id, photo_url, body_part, feedback_type, created_at }]
    """
    year, week_num = _parse_week(week)
    start, end = _week_range(year, week_num)

    stmt = (
        select(Feedback)
        .where(
            Feedback.user_id == user_id,
            Feedback.photo_url.is_not(None),
            Feedback.created_time >= start,
            Feedback.created_time < end,
        )
        .order_by(Feedback.created_time.desc())
    )
    result = await session.execute(stmt)
    photos = [
        {
            "feedback_id": str(f.id),
            "photo_url": f.photo_url,
            "body_part": f.body_part,
            "feedback_type": f.feedback_type,
            "created_at": f.created_time.isoformat() if f.created_time else None,
        }
        for f in result.scalars().all()
    ]
    return {
        "week": week,
        "count": len(photos),
        "photos": photos,
    }


async def get_album_stats(
    session: AsyncSession, *, user_id: str
) -> dict[str, Any]:
    """相册聚合统计（PR-5 时光相册 / 我的 用）。

    返回结构（PR-2 contract 锁）：
    - total_photos: int          — feedback 含 photo_url 数
    - total_checkin_days: int    — 实际打卡的 unique 日期数（按 plan.day 去重）
    - total_diary_entries: int   — mood_text 数
    - days_in_app: int           — 从 created_at 到 today 的天数
    """
    # 1. 总照片数
    photo_stmt = (
        select(func.count())
        .select_from(Feedback)
        .where(
            Feedback.user_id == user_id,
            Feedback.photo_url.is_not(None),
        )
    )
    total_photos = (await session.execute(photo_stmt)).scalar_one()

    # 2. 日记数（mood_text）
    diary_stmt = (
        select(func.count())
        .select_from(Feedback)
        .where(
            Feedback.user_id == user_id,
            Feedback.feedback_type == "mood_text",
        )
    )
    total_diary = (await session.execute(diary_stmt)).scalar_one()

    # 3. 连续打卡天数 = checkin.distinct date 数（用 distinct 函数计数不同 created_time::date）
    checkin_date_expr = func.date(Checkin.created_time).label("d")
    checkin_stmt = (
        select(func.count(func.distinct(checkin_date_expr)))
        .select_from(Checkin)
        .where(Checkin.user_id == user_id)
    )
    total_checkin_days = (await session.execute(checkin_stmt)).scalar_one()

    # 4. 在 App 天数（user.created_at → today）
    user_stmt = select(User.created_at).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    created_at = user_result.scalar_one_or_none()
    if created_at is None:
        days_in_app = 0
    else:
        delta = datetime.now(UTC) - created_at
        days_in_app = max(0, delta.days)

    return {
        "total_photos": int(total_photos or 0),
        "total_checkin_days": int(total_checkin_days or 0),
        "total_diary_entries": int(total_diary or 0),
        "days_in_app": int(days_in_app),
    }


__all__ = [
    "PHOTO_TYPES",
    "AlbumError",
    "AlbumWeekFormatError",
    "get_album_stats",
    "list_album_photos_by_week",
]
