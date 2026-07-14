"""M3 21 天方案生成服务。

真源：``docs/spec/SPEC-M3-21day-plan.md`` + facts-anchor §5。

约束：
- 3 阶段配比：phase 1（1-7 天）1 任务 / phase 2（8-14 天）1-2 / phase 3（15-21 天）2-3
- 同一 video_id 在 21 天内不重复
- 视频库 < 50 条时使用标准模板
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError
from app.core.log import logger
from app.db.models.plan import Plan
from app.db.models.report import Report
from app.db.models.video import Video
from app.errors.codes import (
    E_PLAN_ALREADY_EXISTS,
    E_PLAN_INVALID_INPUT,
    E_PLAN_NO_REPORT,
    E_PLAN_NOT_FOUND,
)
from app.services.video_match import rank_videos

PLAN_LENGTH_DAYS = 21
MIN_VIDEO_LIBRARY = 50

# 三阶段任务数（plan_length=21）
_PHASE_TASKS: dict[int, int] = {1: 1, 2: 2, 3: 3}


class PlanError(SelfwellError):
    """方案生成业务异常基类。"""

    code: str = E_PLAN_INVALID_INPUT
    message_zh: str = "方案请求无效"
    message_en: str = "Invalid plan request"
    severity = "USER_ERROR"
    http_status = 400


class PlanNotFoundError(PlanError):
    code: str = E_PLAN_NOT_FOUND
    message_zh: str = "方案不存在"
    message_en: str = "Plan not found"
    http_status = 404


class PlanNoReportError(PlanError):
    code: str = E_PLAN_NO_REPORT
    message_zh: str = "请先生成诊断报告"
    message_en: str = "Please generate a diagnosis report first"
    http_status = 400


def _phase_for_day(day: int) -> int:
    if day <= 7:
        return 1
    if day <= 14:
        return 2
    return 3


def _phase_tasks(day: int) -> int:
    return _PHASE_TASKS[_phase_for_day(day)]


_WEEK_TITLES: dict[int, str] = {
    1: "第一阶段 · 习惯启动",
    2: "第二阶段 · 强化提升",
    3: "第三阶段 · 稳定养成",
}


def _to_preview_day(
    day_index: int, first_task: dict[str, Any] | None
) -> dict[str, Any]:
    """把内部 ``plan.days["items"]`` 单日条目转成 ``PlanPreviewDay`` 响应字段。

    对齐 ``backend/app/api/routers/plans_v1.py:PlanPreviewDay`` schema。

    Args:
        day_index: 第几天（1-21）。
        first_task: 当日 ``tasks[0]`` 原始 dict；允许为 ``None``。

    Returns:
        ``PlanPreviewDay`` 形态的 dict。
    """
    task_obj = first_task if isinstance(first_task, dict) else {}
    title = task_obj.get("title") or f"第 {day_index} 天 · 核心养护"
    task_label = (
        task_obj.get("task")
        or task_obj.get("video_id")
        or f"task-d{day_index}"
    )
    return {
        "day_index": day_index,
        "title": title,
        "task": task_label,
        "duration_minutes": task_obj.get("duration_minutes", 12),
        "source": task_obj.get("source", "video_pool"),
        "status": task_obj.get("status", "pending"),
    }


def _transform_raw_days_to_preview(
    raw_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """把 ``plan.days["items"]`` 数组转换成 ``PlanPreviewDay`` 数组。

    容错：跳过非 dict 元素；缺失 ``day`` 时按下标兜底。
    """
    preview: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        day_no = item.get("day")
        if not isinstance(day_no, int):
            day_no = index + 1
        tasks_raw = item.get("tasks")
        first_task = (
            tasks_raw[0]
            if isinstance(tasks_raw, list) and tasks_raw
            else None
        )
        preview.append(_to_preview_day(day_no, first_task))
    return preview


def aggregate_plan_weeks(
    plan: Plan, *, today: date | None = None
) -> list[dict[str, Any]]:
    """把 21 天 ``plan.days["items"]`` 聚合成 3 周视图（每周 7 天）。

    Args:
        plan: 已加载的 ``Plan`` ORM；只读，不修改入参。
        today: 计算 ``current_day_index`` 的基准日期；默认 ``date.today()``。

    Returns:
        ``list[dict]``，长度 3（week 1-3）。每个元素：

        ``{"week_no": int, "title": str, "days": list[dict]}``

        其中 ``days[i]`` 形如：

        ``{"day": int, "state": "done"|"today"|"locked", "tasks_count": int, "phase": int}``

    """
    if today is None:
        today = date.today()

    if plan.started_at is not None:
        elapsed = (today - plan.started_at).days + 1
        current_day_index = max(1, min(PLAN_LENGTH_DAYS, elapsed))
    else:
        current_day_index = 1

    days_payload: list[dict[str, object]] = []
    if isinstance(plan.days, dict):
        raw = plan.days.get("items")
        if isinstance(raw, list):
            days_payload = [d for d in raw if isinstance(d, dict)]

    by_day: dict[int, dict[str, object]] = {
        int(d["day"]): d for d in days_payload if isinstance(d.get("day"), int)
    }

    weeks: list[dict[str, Any]] = []
    for week_no in (1, 2, 3):
        day_cells: list[dict[str, Any]] = []
        for offset in range(7):
            day = (week_no - 1) * 7 + offset + 1
            day_item = by_day.get(day, {})
            tasks = day_item.get("tasks")
            tasks_count = len(tasks) if isinstance(tasks, list) else 0
            raw_phase = day_item.get("phase")
            phase = int(raw_phase) if isinstance(raw_phase, int) else _phase_for_day(day)
            if day < current_day_index:
                state = "done"
            elif day == current_day_index:
                state = "today"
            else:
                state = "locked"
            day_cells.append(
                {
                    "day": day,
                    "state": state,
                    "tasks_count": tasks_count,
                    "phase": phase,
                }
            )
        weeks.append(
            {
                "week_no": week_no,
                "title": _WEEK_TITLES[week_no],
                "days": day_cells,
            }
        )
    return weeks


async def list_active_videos(
    session: AsyncSession, *, limit: int = 200
) -> list[dict[str, Any]]:
    """加载所有 active 视频。"""
    stmt = select(Video).where(Video.status == "active").limit(limit)
    result = await session.execute(stmt)
    return [
        {
            "id": str(v.id),
            "title": v.title,
            "duration_sec": v.duration_sec,
            "difficulty": v.difficulty,
            "tags": v.tags if isinstance(v.tags, list) else list((v.tags or {}).keys()),
            "url": v.url,
        }
        for v in result.scalars().all()
    ]


async def generate_plan(
    session: AsyncSession,
    *,
    user_id: str,
    report_id: str,
    intensity: str | None = "适中",
    preferred_time: str | None = "不固定",
) -> dict[str, Any]:
    """生成 21 天方案（基于 report_id 的 tags）。

    Returns:
        方案 dict（plan_id + 21 天映射 + 视频来源）。

    """
    # 1. 加载 report
    rpt_stmt = select(Report).where(Report.id == report_id, Report.user_id == user_id)
    rpt_result = await session.execute(rpt_stmt)
    report = rpt_result.scalar_one_or_none()
    if report is None or report.deleted_at is not None:
        raise PlanNoReportError(field="report_id")

    # 2. 检查是否已有 plan
    exist_stmt = select(Plan).where(Plan.user_id == user_id, Plan.status == "active")
    exist_result = await session.execute(exist_stmt)
    if exist_result.scalar_one_or_none() is not None:
        raise PlanError(
            "已有进行中的方案",
            code=E_PLAN_ALREADY_EXISTS,
            http_status=409,
        )

    # 3. 取 report tags
    report_tags = report.tags.get("items", []) if isinstance(report.tags, dict) else []
    if not report_tags:
        report_tags = ["基础养护", "规律作息"]

    # 4. 视频库 + 排序
    videos = await list_active_videos(session)
    if len(videos) < MIN_VIDEO_LIBRARY:
        logger.warning("plan_video_library_below_min", actual=len(videos))
        ranked = [{"id": v["id"], "title": v["title"], "score": 0.5} for v in videos]
    else:
        ranked = rank_videos(
            videos, report_tags, intensity=intensity, preferred_time=preferred_time
        )

    # 5. 组装 21 天（不重复 video_id）
    used_ids: set[str] = set()
    days_payload: list[dict[str, Any]] = []
    pointer = 0
    # 当视频库为空时，用占位任务（生成 ≥ 63 个 = 1+2+3)*21 不重复 ID）
    if not ranked:
        ranked = [
            {"id": f"placeholder-{i:03d}", "title": f"占位训练 {i + 1}"}
            for i in range(PLAN_LENGTH_DAYS * 3 + 10)
        ]
    for d in range(1, PLAN_LENGTH_DAYS + 1):
        phase = _phase_for_day(d)
        tasks_needed = _phase_tasks(d)
        tasks: list[dict[str, Any]] = []
        attempts = 0
        while len(tasks) < tasks_needed and attempts < len(ranked) * 2:
            if pointer >= len(ranked):
                # 循环复用（实际生产可补新视频）
                pointer = 0
            v = ranked[pointer]
            pointer += 1
            attempts += 1
            if v["id"] in used_ids:
                continue
            used_ids.add(v["id"])
            tasks.append({"video_id": v["id"], "title": v.get("title", "")})
        # 内部存储保留旧 schema（{day, phase, tasks}），保证数据库向后兼容。
        days_payload.append({"day": d, "phase": phase, "tasks": tasks})

    # 6. 写 plan
    now_ts = datetime.now(UTC)
    plan = Plan(
        id=uuid4(),
        user_id=user_id,
        report_id=report_id,
        days={"items": days_payload},
        status="active",
        started_at=date.today(),
        created_at=now_ts,
        created_by=str(user_id),         # 当前创建用户（方案发起人）
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(user_id),    # 当前更新用户
    )
    session.add(plan)
    await session.flush()
    logger.info(
        "plan_created",
        plan_id=str(plan.id),
        user_id=user_id,
        total_videos=len(used_ids),
    )
    # API 响应层：转 PlanPreviewDay 形态（对齐 PlanData 字段契约）。
    api_days = _transform_raw_days_to_preview(days_payload)
    return {
        "plan_id": str(plan.id),
        "report_id": report_id,
        "length_days": PLAN_LENGTH_DAYS,
        "days": api_days,
        "started_at": plan.started_at.isoformat() if plan.started_at else None,
    }


async def get_plan(session: AsyncSession, *, user_id: str, plan_id: str) -> dict[str, Any]:
    """获取方案详情。

    Returns:
        方案 dict（``plan_id`` + ``days`` 已转换为 ``PlanPreviewDay`` 形态）。
    """
    stmt = select(Plan).where(Plan.id == plan_id, Plan.user_id == user_id)
    result = await session.execute(stmt)
    plan = result.scalar_one_or_none()
    if plan is None or plan.deleted_at is not None:
        raise PlanNotFoundError(field="plan_id")
    raw_items = plan.days.get("items", []) if isinstance(plan.days, dict) else []
    return {
        "plan_id": str(plan.id),
        "report_id": plan.report_id,
        "status": plan.status,
        "days": _transform_raw_days_to_preview(raw_items),
        "started_at": plan.started_at.isoformat() if plan.started_at else None,
    }


async def get_current_plan(session: AsyncSession, *, user_id: str) -> dict[str, Any]:
    """获取当前用户的进行中方案。"""
    stmt = (
        select(Plan)
        .where(Plan.user_id == user_id, Plan.status == "active")
        .order_by(Plan.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    plan = result.scalar_one_or_none()
    if plan is None:
        raise PlanNotFoundError(field="current_plan")
    return await get_plan(session, user_id=user_id, plan_id=str(plan.id))


async def get_plan_preview(
    session: AsyncSession,
    *,
    user_id: str,
    plan_id: str,
    days: int = 21,
) -> dict[str, Any]:
    """21 天方案预览,字段对齐前端 plan-delivery 契约。

    与 ``get_plan`` 不同:这里把 ``days.items[].tasks[]`` 扁平化成预览项,
    每项含前端期望的 ``day / day_index / title / task / duration_minutes / source / status``。

    直读 ``plan.days["items"]``（内部存储形态），不走 ``get_plan`` 的响应层转换，
    避免重复加工导致字段错位。

    Args:
        days: 预览返回前 N 天(默认 21,即全量);取值 1-21。

    Raises:
        PlanNotFoundError: plan 不存在或被删。

    Returns:
        ``{plan_id, days: [{day, day_index, title, task, duration_minutes, source, status}, ...]}``
    """
    if not 1 <= days <= PLAN_LENGTH_DAYS:
        days = PLAN_LENGTH_DAYS

    stmt = select(Plan).where(Plan.id == plan_id, Plan.user_id == user_id)
    result = await session.execute(stmt)
    plan = result.scalar_one_or_none()
    if plan is None or plan.deleted_at is not None:
        raise PlanNotFoundError(field="plan_id")

    raw_items = plan.days.get("items", []) if isinstance(plan.days, dict) else []
    total = min(days, len(raw_items) if raw_items else days)
    preview_days: list[dict[str, Any]] = []
    for index in range(total):
        item = raw_items[index] if isinstance(raw_items, list) else {}
        if not isinstance(item, dict):
            item = {}
        tasks = item.get("tasks")
        first_task = tasks[0] if isinstance(tasks, list) and tasks else None
        day_no = item.get("day")
        if not isinstance(day_no, int):
            day_no = index + 1
        cell = _to_preview_day(day_no, first_task)
        cell["day"] = day_no
        preview_days.append(cell)

    return {
        "plan_id": str(plan.id),
        "report_id": plan.report_id,
        "status": plan.status,
        "total_days": len(preview_days),
        "days": preview_days,
    }


async def get_today_plan_tasks(
    session: AsyncSession, *, user_id: str, day_index: int | None = None
) -> dict[str, Any]:
    """今日任务列表（home 页用）。

    Returns:
        ``{plan_id, day_index, total_days, tasks}``。
        - 无 active plan → ``day_index=1, total_days=21, tasks=[]``
        - 已有 plan → 计算当前已进行到第几天（按 ``started_at`` 到今天的天数 + 1）。

    """
    from app.db.models.checkin import Checkin

    stmt = (
        select(Plan)
        .where(Plan.user_id == user_id, Plan.status == "active")
        .order_by(Plan.created_at.desc())
        .limit(1)
    )
    res = await session.execute(stmt)
    plan = res.scalar_one_or_none()
    if plan is None:
        return {
            "plan_id": "",
            "day_index": 1,
            "total_days": PLAN_LENGTH_DAYS,
            "tasks": [],
        }

    days = plan.days.get("items", []) if isinstance(plan.days, dict) else []
    if day_index is None:
        if plan.started_at is not None:
            elapsed = (date.today() - plan.started_at).days + 1
            day_index = max(1, min(PLAN_LENGTH_DAYS, elapsed))
        else:
            day_index = 1

    day_item = next((d for d in days if d.get("day") == day_index), None)
    raw_tasks: list[dict[str, Any]] = (
        day_item.get("tasks", []) if isinstance(day_item, dict) else []
    )

    # 已打卡的 video_id 集合
    done_stmt = select(Checkin.video_id).where(
        Checkin.user_id == user_id,
        Checkin.plan_id == str(plan.id),
        Checkin.day == day_index,
    )
    done_res = await session.execute(done_stmt)
    done_ids = {v for v in done_res.scalars().all() if v}

    # 加载视频元数据（title/subtitle/cover_url/duration_sec/tags）
    video_ids = [t.get("video_id") for t in raw_tasks if t.get("video_id")]
    video_meta: dict[str, Video] = {}
    if video_ids:
        vid_stmt = select(Video).where(Video.id.in_(video_ids))
        vid_res = await session.execute(vid_stmt)
        for v in vid_res.scalars().all():
            video_meta[str(v.id)] = v

    tasks: list[dict[str, Any]] = []
    for t in raw_tasks:
        if not isinstance(t, dict):
            continue
        vid = t.get("video_id") or ""
        meta = video_meta.get(vid)
        tags = (
            meta.tags
            if isinstance(meta, Video) and isinstance(meta.tags, list)
            else []
        )
        tasks.append(
            {
                "task_id": vid,
                "title": t.get("title") or (meta.title if meta else "训练任务"),
                "subtitle": (
                    f"{int(meta.difficulty) if meta and meta.difficulty else '—'} · "
                    f"{int(meta.duration_sec) // 60 if meta and meta.duration_sec else 0} 分钟"
                    if meta
                    else ""
                ),
                "video_id": vid,
                "video_url": meta.url if meta and meta.url else "",
                "cover_url": meta.thumbnail if meta and meta.thumbnail else "",
                "duration_sec": int(meta.duration_sec) if meta and meta.duration_sec else 0,
                "body_part_tags": tags,
                "done": vid in done_ids,
            }
        )

    return {
        "plan_id": str(plan.id),
        "day_index": day_index,
        "total_days": PLAN_LENGTH_DAYS,
        "tasks": tasks,
    }


async def match_videos_for_tags(
    session: AsyncSession,
    *,
    tags: list[str],
    intensity: str | None = "适中",
    preferred_time: str | None = "不固定",
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """按 tags 匹配视频（公开 endpoint 用）。"""
    videos = await list_active_videos(session)
    return rank_videos(
        videos, tags, intensity=intensity, preferred_time=preferred_time, top_k=top_k
    )


__all__ = [
    "MIN_VIDEO_LIBRARY",
    "PLAN_LENGTH_DAYS",
    "PlanError",
    "PlanNoReportError",
    "PlanNotFoundError",
    "aggregate_plan_weeks",
    "generate_plan",
    "get_current_plan",
    "get_plan",
    "get_today_plan_tasks",
    "match_videos_for_tags",
]
