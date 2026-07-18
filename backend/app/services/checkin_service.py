"""M4 每日打卡 service。

真源：``docs/spec/TDS-M4-checkin-loop.md`` + facts-anchor §4.
- 累积碎片 +1 / 连续天数
- 19:00 推送提醒
- 三档话术（warm / neutral / slight_hug）
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError, UserInputError
from app.core.log import logger
from app.db.models.checkin import Checkin
from app.db.models.plan import Plan
from app.db.models.user import User

if TYPE_CHECKING:
    pass
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


class CheckinDuplicateError(CheckinError):
    """同 plan+day 重复打卡（业务层唯一会返回 409 的场景）。"""

    code: str = E_CHECKIN_DUPLICATE
    message_zh: str = "今日已打卡，请勿重复提交"
    message_en: str = "Already checked in today"
    http_status = 409


class CheckinRateLimitError(CheckinError):
    code: str = E_CHECKIN_RATE_LIMIT
    message_zh: str = "打卡过于频繁"
    message_en: str = "Checkin rate limit"
    http_status = 429


def _parse_date(date_str: str | None) -> date | None:
    """Parse ISO date string to date object."""
    if date_str is None:
        return None
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def _calculate_streak(user: User, current_date: date) -> int:
    """计算连续打卡天数。

    - 当前日期打卡成功: +1
    - 检查昨天是否打卡 (日期连续)
    - 不连续则重置为 1
    """
    last_checkin_date = user.report_cache.get("last_checkin_date") if user.report_cache else None
    if last_checkin_date is None:
        return 1

    last_date = _parse_date(last_checkin_date)
    if last_date is None:
        return 1

    days_diff = (current_date - last_date).days
    current_streak = int(user.report_cache.get("streak_days", 0)) if user.report_cache else 0

    if days_diff == 1:
        return current_streak + 1
    elif days_diff == 0:
        return current_streak
    else:
        return 1


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
    """用户打卡（单个 video）。"""
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
        raise CheckinDuplicateError(
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
        created_by=str(user.id),  # 当前创建用户（打卡人）
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(user.id),  # 当前更新用户（打卡人）
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
    user.last_updated_by = str(user.id)  # 当前更新用户（打卡人）

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


async def create_batch_checkin(
    session: AsyncSession,
    *,
    user_id: str,
    plan_id: str,
    day: int,
    task_ids: list[str] | None = None,
    feeling: str | None = None,
) -> dict[str, Any]:
    """一键打卡：task_ids 为空或 None 时，为当天所有任务创建 checkin。

    Args:
        session: 数据库会话
        user_id: 用户 ID
        plan_id: 方案 ID
        day: 第几天 (1-21)
        task_ids: 任务 ID 列表。None 或 [] = 一键打卡（当天所有任务）
        feeling: 心情文本

    Returns:
        {
            "checkin_ids": list[str],       # 创建的所有打卡记录 ID
            "new_streak": int,               # 新连续天数
            "ack_text": str,                 # 鼓励文案
            "all_done_task_ids": list[str],  # 当天所有完成的任务 ID
        }
    """
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

    # 2. 加载 user / plan
    user = await _find_user(session, user_id)
    plan = await _find_plan(session, user_id, plan_id)

    # 3. 检查是否重复打卡（该 day 已有任何 checkin）
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
        raise CheckinDuplicateError(
            "今日已打卡，请勿重复提交",
            code=E_CHECKIN_DUPLICATE,
            http_status=409,
        )

    # 4. 获取当天任务
    plan_days = plan.days.get("items", []) if isinstance(plan.days, dict) else []
    day_item = next((d for d in plan_days if d.get("day") == day), None)
    all_tasks: list[dict[str, Any]] = day_item.get("tasks", []) if isinstance(day_item, dict) else []

    if not all_tasks:
        raise CheckinError(
            f"day {day} 已无可执行任务",
            code=E_CHECKIN_DAY_COMPLETED,
            http_status=409,
        )

    # 5. 确定要打卡的任务（task_ids 为空或 None 时，使用所有任务）
    target_tasks = all_tasks
    if task_ids is not None and task_ids:
        target_video_ids = set(task_ids)
        target_tasks = [t for t in all_tasks if t.get("video_id") in target_video_ids]

    # 6. 批量创建 checkin 记录
    now_ts = datetime.now(UTC)
    today = date.today()
    checkin_ids: list[str] = []
    all_done_task_ids: list[str] = []

    for task in target_tasks:
        video_id = task.get("video_id")
        if not video_id:
            continue
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
            last_updated_by=str(user.id),
        )
        session.add(checkin)
        checkin_ids.append(str(checkin.id))
        all_done_task_ids.append(video_id)

    # 7. 所有任务标记为完成
    for task in all_tasks:
        vid = task.get("video_id")
        if vid and vid not in all_done_task_ids:
            all_done_task_ids.append(vid)

    # 8. 计算连续天数（使用新的 _calculate_streak 函数）
    new_streak = _calculate_streak(user, today)

    # 9. 更新用户缓存
    fragments = int(user.report_cache.get("fragments", 0)) if user.report_cache else 0
    fragments += 1
    user.report_cache = {
        **(user.report_cache or {}),
        "fragments": fragments,
        "streak_days": new_streak,
        "last_checkin_date": today.isoformat(),
    }
    user.last_active_at = now_ts
    user.last_updated_time = now_ts
    user.last_updated_by = str(user.id)

    await session.flush()

    # 10. 生成鼓励文案
    tone = _compute_message_tone(new_streak)
    ack_text = _render_message(tone, new_streak, fragments)

    logger.info(
        "batch_checkin_created",
        user_id=user_id,
        plan_id=plan_id,
        day=day,
        checkin_count=len(checkin_ids),
        new_streak=new_streak,
        fragments=fragments,
    )

    return {
        "checkin_ids": checkin_ids,
        "new_streak": new_streak,
        "ack_text": ack_text,
        "all_done_task_ids": all_done_task_ids,
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


async def get_today_checkin_summary(
    session: AsyncSession, *, user_id: str, day_index: int | None = None
) -> dict[str, Any]:
    """今日打卡进度（home 页用）。

    Returns:
        ``{date, total, done, percent, done_task_ids}``。
        当日没有 plan 时返回 ``done=0, total=0``。

    """
    from app.db.models.plan import Plan as _Plan

    today = date.today()
    # 1. 找当前用户的 active plan
    plan_stmt = (
        select(_Plan)
        .where(_Plan.user_id == user_id, _Plan.status == "active")
        .order_by(_Plan.created_at.desc())
        .limit(1)
    )
    plan_res = await session.execute(plan_stmt)
    plan = plan_res.scalar_one_or_none()
    if plan is None:
        return {
            "date": today.isoformat(),
            "total": 0,
            "done": 0,
            "percent": 0,
            "done_task_ids": [],
        }

    # 自动计算 day_index（与 get_today_plan_tasks 保持一致）
    if day_index is None:
        if plan.started_at is not None:
            elapsed = (today - plan.started_at).days + 1
            day_index = max(1, min(PLAN_LENGTH, elapsed))
        else:
            day_index = 1

    # 2. 取出 day_index 当天所有 task
    days = plan.days.get("items", []) if isinstance(plan.days, dict) else []
    day_item = next((d for d in days if d.get("day") == day_index), None)
    tasks = day_item.get("tasks", []) if isinstance(day_item, dict) else []
    task_ids = [t.get("video_id") for t in tasks if isinstance(t, dict) and t.get("video_id")]

    # 3. 查该 plan + day 已打卡记录
    stmt = select(Checkin.video_id).where(
        Checkin.user_id == user_id,
        Checkin.plan_id == str(plan.id),
        Checkin.day == day_index,
    )
    result = await session.execute(stmt)
    done_ids = [v for v in result.scalars().all() if v]

    total = len(task_ids)
    done = sum(1 for tid in task_ids if tid in done_ids)
    percent = round(done / total * 100) if total > 0 else 0
    return {
        "date": today.isoformat(),
        "total": total,
        "done": done,
        "percent": percent,
        "done_task_ids": done_ids,
        "checkin_complete": done > 0 and done == total,
    }


__all__ = [
    "MAX_FEELING_LENGTH",
    "PLAN_LENGTH",
    "CheckinDuplicateError",
    "CheckinError",
    "CheckinRateLimitError",
    "create_batch_checkin",
    "create_checkin",
    "get_today_checkin",
    "get_today_checkin_summary",
    "list_user_checkins",
]
