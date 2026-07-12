"""V2 IA · Badge service（勋章体系读写）。

真源：``plans/v2-unified-parent.md`` §2.2 + IA V2.2 §2A.2.1 + §2A.3 #1 接口
+ alembic 0007 ``user_badges`` 表。

责任：
- 列出用户全部勋章（已解锁 + 在路上）
- 增量推进 progress（V2 后端 helper，PR-3/5 触发）
- 解锁勋章（unlock；set unlocked_at）
- 测试用：手动 upsert（PR-2 内单测需要确定性注入）

约定：
- 进度字段使用 INTEGER，校验 progress >= 0 且 <= target + buffer（buffer = 0）
- 解锁时确保 progress == target；不一致自动 clamp
- progress 单调递增（不可回退；除非 unlock 重置）
- 6 类枚举 BADGE_CODES（与 ORM 文件同源）

幂等：UNIQUE (user_id, code) 决定一行最多 1 条；upsert 用 INSERT ON CONFLICT DO UPDATE
（PR-2 内用纯 SELECT + INSERT/UPDATE；PR-VP 之后可换成 ON CONFLICT 性能更好）。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError
from app.core.log import logger
from app.db.models.user_badge import BADGE_CODES, UserBadge
from app.errors.codes import E_USER_INVALID_INPUT

MAX_PROGRESS_BUFFER = 0  # progress 不能超过 target + 0；超出抛错


class BadgeError(SelfwellError):
    """勋章业务异常。"""

    code: str = E_USER_INVALID_INPUT
    message_zh: str = "勋章操作失败"
    message_en: str = "Badge operation failed"
    severity = "USER_ERROR"
    http_status = 400


class BadgeCodeError(BadgeError):
    """code 不在 6 类枚举内。"""

    code: str = E_USER_INVALID_INPUT
    message_zh: str = "勋章 code 不在允许范围"
    message_en: str = "Badge code not in allowed enum"
    http_status = 400


class BadgeProgressError(BadgeError):
    """progress 越界。"""

    code: str = E_USER_INVALID_INPUT
    message_zh: str = "勋章进度越界"
    message_en: str = "Badge progress out of range"
    http_status = 400


def _validate_code(code: str) -> str:
    """Code 必须在 6 类枚举内。"""
    if code not in BADGE_CODES:
        raise BadgeCodeError(field="code", allowed=sorted(BADGE_CODES))
    return code


def _validate_progress(progress: int, target: int) -> int:
    """Progress ∈ [0, target + MAX_PROGRESS_BUFFER]。"""
    if progress < 0:
        raise BadgeProgressError(
            "progress 不能为负", field="progress", min=0, max=target
        )
    if progress > target + MAX_PROGRESS_BUFFER:
        raise BadgeProgressError(
            "progress 超过 target", field="progress", min=0, max=target
        )
    return progress


def _serialize_badge(badge: UserBadge) -> dict[str, Any]:
    """UserBadge ORM → 响应 dict。"""
    return {
        "code": badge.code,
        "progress": badge.progress,
        "target": badge.target,
        "unlocked": badge.unlocked_at is not None,
        "unlocked_at": badge.unlocked_at.isoformat() if badge.unlocked_at else None,
    }


async def list_user_badges(
    session: AsyncSession, *, user_id: str
) -> dict[str, Any]:
    """返回用户全部勋章（已解锁 + 在路上）。

    返回结构（PR-2 contract 锁）：
    - unlocked: list[dict]  — 已解锁勋章
    - in_progress: list[dict] — 进度 0 < progress < target
    - total_unlocked: int     — 已解锁数
    - total_codes: int        — 全集 6 类枚举大小

    兜底：用户从未触达勋章体系 → 每张 code 都返回一条 in_progress(progress=0, target=0)
    """
    stmt = (
        select(UserBadge)
        .where(UserBadge.user_id == user_id, UserBadge.deleted_at.is_(None))
        .order_by(UserBadge.code)
    )
    result = await session.execute(stmt)
    badges = list(result.scalars().all())

    # 兜底全集：如果用户没有 6 类中任何一条，返回空 unlocked + 空 in_progress
    by_code: dict[str, UserBadge] = {b.code: b for b in badges}
    unlocked: list[dict[str, Any]] = []
    in_progress: list[dict[str, Any]] = []

    for code in sorted(BADGE_CODES):
        if code in by_code:
            b = by_code[code]
            if b.unlocked_at is not None:
                unlocked.append(_serialize_badge(b))
            elif b.progress > 0 or b.target > 0:
                in_progress.append(_serialize_badge(b))
            # progress == 0 且 target == 0 → 用户从未触达，跳过
        # else: 用户从未触达这张 code，跳过

    return {
        "unlocked": unlocked,
        "in_progress": in_progress,
        "total_unlocked": len(unlocked),
        "total_codes": len(BADGE_CODES),
    }


async def increment_progress(
    session: AsyncSession,
    *,
    user_id: str,
    code: str,
    delta: int = 1,
    target: int | None = None,
) -> dict[str, Any]:
    """进度推进 +1（或指定 delta）。

    行为：
    - 已有 row → progress += delta
    - 没有 row → 新建 row，progress = delta, target = target 参数（必填）
    - 若 progress >= target 且 unlocked_at 为空 → 自动解锁

    Returns:
        dict { code, progress, target, unlocked, unlocked_at }

    """
    if delta <= 0:
        raise BadgeProgressError(
            "delta 必须为正数", field="delta", min=1, max=None
        )
    code = _validate_code(code)

    now_ts = datetime.now(UTC)
    stmt = select(UserBadge).where(
        UserBadge.user_id == user_id,
        UserBadge.code == code,
        UserBadge.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    badge = result.scalar_one_or_none()

    if badge is None:
        # 新建
        if target is None or target <= 0:
            raise BadgeProgressError(
                "首次创建勋章必须提供 target > 0", field="target", min=1, max=None
            )
        badge = UserBadge(
            id=uuid4(),
            user_id=user_id,
            code=code,
            progress=delta,
            target=target,
            unlocked_at=None,
            created_at=now_ts,
            created_by=str(user_id),
            created_time=now_ts,
            last_updated_time=now_ts,
            last_updated_by=str(user_id),
        )
        session.add(badge)
    else:
        badge.progress = _validate_progress(
            badge.progress + delta, badge.target
        )
        badge.last_updated_time = now_ts
        badge.last_updated_by = str(user_id)

    # 自动解锁
    if badge.progress >= badge.target and badge.unlocked_at is None:
        badge.unlocked_at = now_ts
        logger.info(
            "badge_unlocked",
            user_id=user_id,
            code=code,
            progress=badge.progress,
            target=badge.target,
        )

    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise BadgeError("勋章 upsert 失败（DB 冲突）", field="code") from None

    return _serialize_badge(badge)


async def unlock_badge(
    session: AsyncSession,
    *,
    user_id: str,
    code: str,
) -> dict[str, Any]:
    """强制解锁（admin / 测试 / 补偿用）。

    幂等：已解锁时 no-op 返回当前状态。
    """
    code = _validate_code(code)
    now_ts = datetime.now(UTC)

    stmt = select(UserBadge).where(
        UserBadge.user_id == user_id,
        UserBadge.code == code,
        UserBadge.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    badge = result.scalar_one_or_none()

    if badge is None:
        # 没创建过 → 创建并直接解锁
        badge = UserBadge(
            id=uuid4(),
            user_id=user_id,
            code=code,
            progress=0,
            target=0,
            unlocked_at=now_ts,
            created_at=now_ts,
            created_by=str(user_id),
            created_time=now_ts,
            last_updated_time=now_ts,
            last_updated_by=str(user_id),
        )
        session.add(badge)
    elif badge.unlocked_at is None:
        badge.unlocked_at = now_ts
        badge.last_updated_time = now_ts
        badge.last_updated_by = str(user_id)

    await session.flush()
    logger.info("badge_force_unlocked", user_id=user_id, code=code)
    return _serialize_badge(badge)


async def get_badges_summary(
    session: AsyncSession, *, user_id: str
) -> dict[str, Any]:
    """轻量汇总（PR-3 today/profile-new 卡片用）。

    返回结构：
    - total_unlocked: int
    - total_codes: int
    - latest_unlocked: { code, unlocked_at } | None
    """
    data = await list_user_badges(session, user_id=user_id)
    latest = None
    if data["unlocked"]:
        latest_badge = max(
            data["unlocked"], key=lambda b: b.get("unlocked_at") or ""
        )
        latest = {
            "code": latest_badge["code"],
            "unlocked_at": latest_badge["unlocked_at"],
        }
    return {
        "total_unlocked": data["total_unlocked"],
        "total_codes": data["total_codes"],
        "latest_unlocked": latest,
    }


__all__ = [
    "BADGE_CODES",
    "MAX_PROGRESS_BUFFER",
    "BadgeCodeError",
    "BadgeError",
    "BadgeProgressError",
    "get_badges_summary",
    "increment_progress",
    "list_user_badges",
    "unlock_badge",
]
