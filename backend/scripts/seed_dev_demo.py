"""开发态种子数据脚本（解 home 空态）。

用途：为开发 / staging 环境注入 demo videos + 诊断报告 + 21 天方案，
让当前用户在首页立即看到任务列表。

幂等性：
- videos：用 (source, video_id) 判重，重复运行不报错、不产生重复数据。
- report / plan：按 user_id + status='active' 判重，已存在则跳过并打印提示。

约束：
- 仅允许 dev / staging 环境；prod 环境直接拒绝。
- 必须手动 commit（不走 FastAPI DI）。

真源：db/init/01-schema.sql / 03-checks.sql / 06-ddl-update-0707.sql +
      app/db/models/*.py + app/services/plan_service.py +
      app/services/users/profile_service.py (focus_parts enum)
"""

from __future__ import annotations

import argparse
import asyncio
import io
import pathlib
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ── 路径准备：backend/app 是顶层包，sys.path 需加 backend/ ──────────────────
_repo_root = pathlib.Path(__file__).resolve().parents[2].as_posix()
_backend_root = f"{_repo_root}/backend"
sys.path.insert(0, _backend_root)

from app.conf.app_config import AppEnv, app_config  # noqa: E402
from app.core.log import logger, setup_logging  # noqa: E402
from app.db.models.plan import Plan  # noqa: E402
from app.db.models.report import Report  # noqa: E402
from app.db.models.user import User  # noqa: E402
from app.db.models.video import Video  # noqa: E402
from app.db.session import get_sessionmaker  # noqa: E402
from app.services.plan_service import generate_plan  # noqa: E402

# ── focus_parts 枚举（与 profile_service.py:_FOCUS_PARTS 完全对齐）─────────────
_FOCUS_PARTS: list[str] = [
    "face",
    "head",
    "shoulder_neck",
    "waist",
    "leg",
    "overall_look",
]

# ── Demo video 数据（8 条，真实风格标题，合法范围值）────────────────────────────
# difficulty ∈ [1,5]；duration_sec ∈ [1,3600]；tags 为 list；status='active'
_DEMO_VIDEOS: list[dict[str, Any]] = [
    {
        "title": "办公室肩颈舒缓 5 分钟",
        "source": "bilibili",
        "video_id": "BV1xx411c7XD_demo_001",
        "url": "https://www.bilibili.com/video/BV1xx411c7XD",
        "duration_sec": 300,
        "difficulty": 2,
        "tags": ["shoulder_neck", "overall_look"],
        "thumbnail": ("https://dummyimage.com/480x270/4A90E2/ffffff?text=肩颈舒缓"),
    },
    {
        "title": "睡前腰部放松拉伸",
        "source": "bilibili",
        "video_id": "BV1xx411c7XD_demo_002",
        "url": "https://www.bilibili.com/video/BV1xx411c7XD",
        "duration_sec": 420,
        "difficulty": 1,
        "tags": ["waist", "overall_look"],
        "thumbnail": ("https://dummyimage.com/480x270/50C878/ffffff?text=腰部放松"),
    },
    {
        "title": "晨间面部唤醒操",
        "source": "xiaohongshu",
        "video_id": "xhs_demo_003",
        "url": "https://www.xiaohongshu.com/explore/demo003",
        "duration_sec": 240,
        "difficulty": 1,
        "tags": ["face", "overall_look"],
        "thumbnail": ("https://dummyimage.com/480x270/F4A460/ffffff?text=面部唤醒"),
    },
    {
        "title": "头部经络穴位放松",
        "source": "xiaohongshu",
        "video_id": "xhs_demo_004",
        "url": "https://www.xiaohongshu.com/explore/demo004",
        "duration_sec": 360,
        "difficulty": 2,
        "tags": ["head", "shoulder_neck"],
        "thumbnail": ("https://dummyimage.com/480x270/9370DB/ffffff?text=头部放松"),
    },
    {
        "title": "久坐腿部肿胀缓解",
        "source": "douyin",
        "video_id": "dy_demo_005",
        "url": "https://www.douyin.com/video/7000000000000005",
        "duration_sec": 480,
        "difficulty": 3,
        "tags": ["leg", "overall_look"],
        "thumbnail": ("https://dummyimage.com/480x270/FF6347/ffffff?text=腿部缓解"),
    },
    {
        "title": "进阶全身气血调理",
        "source": "douyin",
        "video_id": "dy_demo_006",
        "url": "https://www.douyin.com/video/7000000000000006",
        "duration_sec": 540,
        "difficulty": 4,
        "tags": ["face", "head", "shoulder_neck", "waist", "leg", "overall_look"],
        "thumbnail": ("https://dummyimage.com/480x270/20B2AA/ffffff?text=全身调理"),
    },
    {
        "title": "女性肩颈深层放松",
        "source": "youtube",
        "video_id": "yt_demo_007",
        "url": "https://www.youtube.com/watch?v=demo007",
        "duration_sec": 380,
        "difficulty": 3,
        "tags": ["shoulder_neck", "overall_look"],
        "thumbnail": ("https://dummyimage.com/480x270/DC143C/ffffff?text=肩颈深层"),
    },
    {
        "title": "睡前 10 分钟全身放松",
        "source": "youtube",
        "video_id": "yt_demo_008",
        "url": "https://www.youtube.com/watch?v=demo008",
        "duration_sec": 600,
        "difficulty": 2,
        "tags": ["waist", "leg", "overall_look"],
        "thumbnail": ("https://dummyimage.com/480x270/4682B4/ffffff?text=全身放松"),
    },
]


# ── Demo report 数据（1 份，合法 JSONB，tags 用 {"items":[...]} 结构）───────────
_DEMO_REPORT_PHOTOS: dict[str, Any] = {
    "items": [
        "https://dummyimage.com/800x1200/4A90E2/ffffff?text=照片1",
        "https://dummyimage.com/800x1200/50C878/ffffff?text=照片2",
        "https://dummyimage.com/800x1200/F4A460/ffffff?text=照片3",
    ]
}

_DEMO_REPORT_DIRECTIONS: dict[str, Any] = {
    "items": [
        "每日坚持肩颈拉伸，缓解久坐导致的肌肉紧张",
        "注意规律作息，保证充足睡眠配合气血调理",
        "适当增加户外运动，提升整体气色和免疫力",
        "睡前避免长时间看手机，帮助放松神经",
    ]
}

_DEMO_REPORT_TAGS: dict[str, Any] = {
    "items": [
        "肩颈不适",
        "久坐人群",
        "气色暗沉",
        "睡眠质量差",
        "免疫力低下",
        "整体养护",
        "情绪调节",
    ]
}


# ─────────────────────────────────────────────────────────────────────────────
# 环境守卫
# ─────────────────────────────────────────────────────────────────────────────
def _check_environment() -> None:
    """拒绝在 prod 环境运行，避免污染生产数据。"""
    current_env = app_config.app_env
    if current_env == AppEnv.PROD:
        logger.error("seed_refused_on_prod", env=current_env.value)
        raise SystemExit(
            "ERROR: seed_dev_demo.py 拒绝在 prod 环境运行。\n"
            "当前环境：prod\n"
            "允许环境：dev / staging\n"
            "如需在本地运行，请确保 .env 中 APP_ENV=dev 或 APP_ENV=staging。"
        )
    logger.info("seed_env_check_passed", env=current_env.value)


# ─────────────────────────────────────────────────────────────────────────────
# 用户解析
# ─────────────────────────────────────────────────────────────────────────────
async def _resolve_user(session: AsyncSession, user_id_arg: str | None) -> User:
    """根据 CLI 参数或数据库查询确定目标用户。"""
    if user_id_arg:
        try:
            uid = UUID(user_id_arg)
        except ValueError as e:
            raise SystemExit(
                f"ERROR: --user-id 必须为有效 UUID 格式，传入值：「{user_id_arg}」不是合法 UUID。"
            ) from e

        stmt = select(User).where(User.id == uid)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None or user.deleted_at is not None:
            raise SystemExit(
                f"ERROR: 未找到 user_id={user_id_arg} 的用户（可能已删除）。\n"
                f"请先在小程序登录以创建用户记录。"
            )
        return user

    # 未传参数：查找最近活跃用户
    stmt = (
        select(User).where(User.deleted_at.is_(None)).order_by(User.last_active_at.desc()).limit(1)
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise SystemExit(
            "ERROR: 未找到任何用户。\n"
            "请先在小程序完成登录流程，再运行本脚本。\n"
            "或使用 --user-id <uuid> 指定用户。"
        )
    logger.info("seed_user_autodetected", user_id=str(user.id), nickname=user.nickname)
    return user


# ─────────────────────────────────────────────────────────────────────────────
# Videos 插入（幂等：source + video_id 判重）
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_videos(session: AsyncSession, created_by: str) -> int:
    """插入 demo videos，已存在则跳过。返回新增数量。"""
    inserted = 0
    now_ts = datetime.now(UTC)

    for video_data in _DEMO_VIDEOS:
        # 幂等检查
        stmt = select(Video).where(
            Video.source == video_data["source"],
            Video.video_id == video_data["video_id"],
        )
        result = await session.execute(stmt)
        if result.scalar_one_or_none() is not None:
            logger.debug(
                "seed_video_skipped_exists",
                source=video_data["source"],
                video_id=video_data["video_id"],
            )
            continue

        video = Video(
            id=uuid4(),
            title=video_data["title"],
            source=video_data["source"],
            video_id=video_data["video_id"],
            url=video_data["url"],
            duration_sec=video_data["duration_sec"],
            difficulty=video_data["difficulty"],
            tags=video_data["tags"],  # list，元素 ∈ focus_parts 枚举
            thumbnail=video_data["thumbnail"],
            status="active",
            created_at=now_ts,
            updated_at=now_ts,
            created_by=created_by,
            created_time=now_ts,
            last_updated_time=now_ts,
            last_updated_by=created_by,
        )
        session.add(video)
        inserted += 1
        logger.debug(
            "seed_video_inserted",
            title=video_data["title"],
            difficulty=video_data["difficulty"],
        )

    await session.flush()
    logger.info("seed_videos_complete", inserted=inserted, total=len(_DEMO_VIDEOS))
    return inserted


# ─────────────────────────────────────────────────────────────────────────────
# Report 插入（幂等：同一 user 有报告则跳过）
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_report(session: AsyncSession, user: User) -> tuple[Report, bool]:
    """插入 demo report，已存在则跳过。

    Returns:
        (report, is_new): 新建/已有 report 对象，及是否为本次新建。

    """
    user_id_str = str(user.id)
    now_ts = datetime.now(UTC)

    # 幂等检查：同用户已有报告则跳过
    exist_stmt = (
        select(Report)
        .where(
            Report.user_id == user.id,
            Report.deleted_at.is_(None),
        )
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    exist_result = await session.execute(exist_stmt)
    existing = exist_result.scalar_one_or_none()
    if existing is not None:
        logger.info(
            "seed_report_skipped_exists",
            user_id=user_id_str,
            report_id=str(existing.id),
        )
        return existing, False

    report = Report(
        id=uuid4(),
        user_id=user.id,
        photos=_DEMO_REPORT_PHOTOS,
        directions=_DEMO_REPORT_DIRECTIONS,
        tags=_DEMO_REPORT_TAGS,
        summary="基于近期身体状态的综合养护建议报告，注重肩颈、腰部及整体气色调理。",
        llm_model="demo-model",
        llm_cost=0.0,
        created_at=now_ts,
        created_by=user_id_str,
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=user_id_str,
    )
    session.add(report)
    await session.flush()
    logger.info("seed_report_inserted", user_id=user_id_str, report_id=str(report.id))
    return report, True


# ─────────────────────────────────────────────────────────────────────────────
# Plan 生成（幂等：已有 active plan 则跳过）
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_plan(session: AsyncSession, user: User, report: Report) -> tuple[Plan | None, bool]:
    """生成 21 天方案，已存在 active plan 则跳过。

    调用 generate_plan() 服务函数以保证 days 结构与生产一致。

    Returns:
        (plan, is_new): 新建/已有 plan 对象（可能为 None），及是否为本次新建。

    """
    user_id_str = str(user.id)
    report_id_str = str(report.id)

    # 幂等检查
    exist_stmt = select(Plan).where(
        Plan.user_id == user.id,
        Plan.status == "active",
    )
    exist_result = await session.execute(exist_stmt)
    existing = exist_result.scalar_one_or_none()
    if existing is not None:
        logger.info(
            "seed_plan_skipped_exists",
            user_id=user_id_str,
            plan_id=str(existing.id),
        )
        return existing, False

    try:
        plan_result = await generate_plan(
            session,
            user_id=user_id_str,
            report_id=report_id_str,
        )
        # generate_plan 会 flush 但不 commit；重新查询拿到带 id 的对象
        plan_id = plan_result["plan_id"]
        plan_stmt = select(Plan).where(Plan.id == plan_id)
        plan_res = await session.execute(plan_stmt)
        plan_obj = plan_res.scalar_one_or_none()
        if plan_obj is None:
            logger.error("seed_plan_fetch_failed", plan_id=plan_id)
            return None, False
        logger.info(
            "seed_plan_inserted",
            user_id=user_id_str,
            plan_id=plan_id,
            days_count=len(plan_result.get("days", [])),
        )
        return plan_obj, True

    except Exception as e:
        if "E_PLAN_ALREADY_EXISTS" in str(getattr(e, "code", "")) or ("已有进行中的方案" in str(e)):
            logger.info("seed_plan_skipped_already_exists", user_id=user_id_str)
            # 回滚 generate_plan 的部分写入（它已 flush）
            await session.rollback()
            # 重新查询
            stmt = select(Plan).where(Plan.user_id == user.id, Plan.status == "active")
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()
            return existing, False

        logger.exception("seed_plan_generate_error", user_id=user_id_str, error=str(e))
        raise


# ─────────────────────────────────────────────────────────────────────────────
# 种子数据统计结果（用于跨 session 传递 + 减少函数参数）
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class SeedResult:
    """所有种子数据插入的结果聚合。"""

    user: User
    videos_inserted: int
    report: Report
    report_is_new: bool
    plan: Plan | None
    plan_is_new: bool


# ─────────────────────────────────────────────────────────────────────────────
# 辅助：解析 plan 的 days 统计信息
# ─────────────────────────────────────────────────────────────────────────────
def _count_plan_stats(plan_obj: Plan) -> tuple[int, int]:
    """从 Plan 对象解析 days_count 和第 1 天 task_count。"""
    days_count = 0
    day1_task_count = 0
    plan_days = plan_obj.days
    if isinstance(plan_days, dict):
        items: list[dict[str, Any]] = plan_days.get("items", [])
    else:
        items = []
    days_count = len(items)
    if items:
        first_day = items[0]
        day1_tasks: list[dict[str, Any]] = first_day.get("tasks", [])
        day1_task_count = len(day1_tasks)
    return days_count, day1_task_count


# ─────────────────────────────────────────────────────────────────────────────
# 主流程：数据插入
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_all(user_id_arg: str | None) -> SeedResult:
    """执行所有种子数据插入，返回聚合结果。"""
    sm = get_sessionmaker()
    async with sm() as session:
        user = await _resolve_user(session, user_id_arg)
        user_id_str = str(user.id)
        logger.info("seed_target_user", user_id=user_id_str, nickname=user.nickname)

        videos_inserted = await _seed_videos(session, created_by=user_id_str)
        report, report_is_new = await _seed_report(session, user)
        plan, plan_is_new = await _seed_plan(session, user, report)

        await session.commit()
        logger.info("seed_commit_complete")

    return SeedResult(
        user=user,
        videos_inserted=videos_inserted,
        report=report,
        report_is_new=report_is_new,
        plan=plan,
        plan_is_new=plan_is_new,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 主流程：验收输出
# ─────────────────────────────────────────────────────────────────────────────
async def _fetch_plan_stats_async(
    plan_id: UUID,
) -> tuple[int, int]:
    """在 session 外查询 plan.days 并统计。"""
    sm = get_sessionmaker()
    async with sm() as sess:
        stmt = select(Plan).where(Plan.id == plan_id)
        res = await sess.execute(stmt)
        refreshed = res.scalar_one_or_none()
        if refreshed is not None:
            return _count_plan_stats(refreshed)
    return 0, 0


async def _fetch_report_id_async(user_id: UUID, fallback: str) -> str:
    """查询用户最新的 report id。"""
    sm = get_sessionmaker()
    async with sm() as sess:
        stmt = (
            select(Report)
            .where(
                Report.user_id == user_id,
                Report.deleted_at.is_(None),
            )
            .order_by(Report.created_at.desc())
            .limit(1)
        )
        res = await sess.execute(stmt)
        r = res.scalar_one_or_none()
        return str(r.id) if r is not None else fallback


async def _fetch_plan_id_async(user_id: UUID, fallback: str) -> str:
    """查询用户最新的 active plan id。"""
    sm = get_sessionmaker()
    async with sm() as sess:
        stmt = select(Plan).where(Plan.user_id == user_id, Plan.status == "active")
        res = await sess.execute(stmt)
        p = res.scalar_one_or_none()
        return str(p.id) if p is not None else fallback


async def _print_results_async(result: SeedResult) -> tuple[int, int]:
    """异步打印格式化验收结果。返回 (days_count, day1_task_count)。"""
    user_id_str = str(result.user.id)
    report_id_str = str(result.report.id)

    tasks: list[tuple[str, Any]] = []
    if result.plan is not None:
        plan_id = result.plan.id
        tasks.append(("plan_stats", _fetch_plan_stats_async(plan_id)))

    # 幂等复投时重新查询 id
    if not result.report_is_new:
        tasks.append(("report_id", _fetch_report_id_async(result.user.id, report_id_str)))
    if not result.plan_is_new and result.plan is not None:
        tasks.append(("plan_id", _fetch_plan_id_async(result.user.id, str(result.plan.id))))

    # 并行执行所有查询
    results_dict: dict[str, Any] = {}
    if tasks:
        gathered = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        for i, (key, _) in enumerate(tasks):
            val = gathered[i]
            if not isinstance(val, Exception):
                results_dict[key] = val

    days_count, day1_task_count = results_dict.get("plan_stats", (0, 0))
    if "report_id" in results_dict:
        report_id_str = results_dict["report_id"]
    if "plan_id" in results_dict:
        plan_id_str = results_dict["plan_id"]
    else:
        plan_id_str = str(result.plan.id) if result.plan else "N/A"

    total = len(_DEMO_VIDEOS)
    report_tag = "[已存在，跳过]" if not result.report_is_new else "[新建]"
    plan_tag = "[已存在，跳过]" if not result.plan_is_new else "[新建]"

    print("\n" + "=" * 64)
    print("  seed_dev_demo.py  执行结果")
    print("=" * 64)
    print(f"  目标用户     : {result.user.nickname} ({user_id_str})")
    print(f"  Videos 新增  : {result.videos_inserted} 条（总共 {total} 条 demo 数据）")
    print(f"  Report ID    : {report_id_str} {report_tag}")
    print(f"  Plan ID      : {plan_id_str} {plan_tag}")
    print(f"  Plan 天数    : {days_count} 天（应为 21）")
    print(f"  第 1 天任务数: {day1_task_count} 个（phase1 = 1 任务/天）")
    print("=" * 64)
    print()
    if result.videos_inserted > 0 or result.report_is_new or result.plan_is_new:
        print("  [OK] 数据插入成功。重启小程序 / 刷新首页即可看到任务。")
    else:
        print("  [i]  数据已存在，无需重复插入（幂等运行）。")
    print()
    print("  验证方式：")
    print("    小程序 -> 首页 -> 应看到今日任务列表")
    print("    或 API：GET /api/v1/plans/today")
    print()
    print("=" * 64)

    return days_count, day1_task_count


# ─────────────────────────────────────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────────────────────────────────────
async def _main_async(user_id_arg: str | None) -> tuple[int, int]:
    """完整的异步主流程（包含数据插入 + 验收输出）。"""
    setup_logging(level="INFO")
    logger.info("seed_script_started", user_id_provided=user_id_arg)

    seed_result = await _seed_all(user_id_arg)
    days_count, day1_task_count = await _print_results_async(seed_result)

    user_id_str = str(seed_result.user.id)
    report_id_str = str(seed_result.report.id)
    plan_id_str = str(seed_result.plan.id) if seed_result.plan else "N/A"
    logger.info(
        "seed_all_complete",
        user_id=user_id_str,
        videos_inserted=seed_result.videos_inserted,
        report_id=report_id_str,
        report_is_new=seed_result.report_is_new,
        plan_id=plan_id_str,
        plan_is_new=seed_result.plan_is_new,
        days_count=days_count,
        day1_task_count=day1_task_count,
    )
    return days_count, day1_task_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="开发态种子数据脚本：为 dev/staging 环境注入 demo 数据，解首页空态。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 自动查找最近活跃用户
  python -m backend.scripts.seed_dev_demo

  # 指定用户 ID
  python -m backend.scripts.seed_dev_demo --user-id 01234567-89ab-cdef-0123-456789abcdef
        """,
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        metavar="UUID",
        help="目标用户的 UUID（不传则自动查找最近活跃用户）",
    )
    args = parser.parse_args()

    # Windows PowerShell 默认 GBK 输出流；强制 UTF-8 避免 UnicodeEncodeError
    if sys.platform == "win32":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        except Exception:  # noqa: S110  # 降级：回退到 ASCII-safe 输出
            pass

    # 环境守卫
    _check_environment()

    # 单一 asyncio.run() 入口驱动完整异步流程
    asyncio.run(_main_async(args.user_id))


if __name__ == "__main__":
    main()
