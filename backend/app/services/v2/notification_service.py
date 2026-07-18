"""V2 IA · Notification prefs service（通知偏好读写）。

真源：``plans/v2-unified-parent.md`` §2.2 + IA V2.2 §2A.2.2 + §2A.3 #5 / #6
+ alembic 0007 ``user_notification_prefs`` 表。

责任：
- 读取 user 全部 pref（GET）
- 批量更新 user pref（PUT）
- 默认 pref seed（用户首次访问时填入）

约定：
- pref_value 必须是 dict（JSONB）
- 未知 pref_key 写入时落默认值（V2 暂不抛错；PR-5 前端允许用户自由加自定义 key）
- 写入路径：upsert（UPDATE 优先 → INSERT 兜底）
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError
from app.core.log import logger
from app.db.models.user_notification_pref import PREF_KEYS, UserNotificationPref
from app.errors.codes import E_NOTIF_PREF_INVALID

DEFAULT_PREF_VALUES: dict[str, dict[str, Any]] = {
    "daily_checkin": {"enabled": True, "time": "08:00"},
    "weekly_recall": {"enabled": True, "time": "20:00"},
    "feedback_ack": {"enabled": True},
    "plan_milestone": {"enabled": True},
    "album_unlock": {"enabled": True},
    "hug_card_ready": {"enabled": True},
}


class NotificationPrefError(SelfwellError):
    """通知偏好业务异常。"""

    code: str = E_NOTIF_PREF_INVALID
    message_zh: str = "通知偏好操作失败"
    message_en: str = "Notification prefs operation failed"
    severity = "USER_ERROR"
    http_status = 400


def _serialize(pref: UserNotificationPref) -> dict[str, Any]:
    return {
        "pref_key": pref.pref_key,
        "pref_value": pref.pref_value if isinstance(pref.pref_value, dict) else {},
        "updated_at": pref.updated_at.isoformat() if pref.updated_at else None,
    }


async def list_notification_prefs(
    session: AsyncSession, *, user_id: str
) -> dict[str, Any]:
    """读取 user 全部 pref。

    返回结构（PR-2 contract 锁）：
    - prefs: dict[str, dict]  — key → value map
    - total: int              — key 总数
    """
    stmt = (
        select(UserNotificationPref)
        .where(UserNotificationPref.user_id == user_id)
        .order_by(UserNotificationPref.pref_key)
    )
    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    prefs: dict[str, dict[str, Any]] = {r.pref_key: r.pref_value for r in rows}
    return {"prefs": prefs, "total": len(prefs)}


async def update_notification_prefs(
    session: AsyncSession, *, user_id: str, prefs: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """批量更新 user pref（PUT 全量替换）。

    约定：
    - prefs 是新全量；不在 prefs 里的旧 key 保留（**not** delete-all）
    - 空 prefs = 跳过更新

    Returns:
        { updated_keys: list[str], total: int }

    """
    if prefs is None or not isinstance(prefs, dict):
        raise NotificationPrefError("prefs 必须是 dict", field="prefs")
    if not prefs:
        return {"updated_keys": [], "total": 0}

    now_ts = datetime.now(UTC)
    updated: list[str] = []

    for key, value in prefs.items():
        if not isinstance(key, str):
            raise NotificationPrefError("pref_key 必须是 str", field="pref_key")
        if key not in PREF_KEYS:
            raise NotificationPrefError(
                f"pref_key 不在允许范围：{key}",
                field="pref_key",
                allowed=sorted(PREF_KEYS),
            )
        if not isinstance(value, dict):
            raise NotificationPrefError(
                f"{key} 的 value 必须是 dict", field="pref_value", pref_key=key
            )

        # PostgreSQL upsert via ON CONFLICT (user_id, pref_key)
        # Use index_elements (not constraint="...") so the upsert is portable
        # and does not depend on the PK constraint's exact DB-side name.
        stmt = (
            pg_insert(UserNotificationPref)
            .values(
                user_id=user_id,
                pref_key=key,
                pref_value=value,
                updated_at=now_ts,
                created_by=str(user_id),
                created_time=now_ts,
                last_updated_time=now_ts,
                last_updated_by=str(user_id),
            )
            .on_conflict_do_update(
                index_elements=["user_id", "pref_key"],
                set_={
                    "pref_value": value,
                    "updated_at": now_ts,
                    "last_updated_time": now_ts,
                    "last_updated_by": str(user_id),
                },
            )
        )
        await session.execute(stmt)
        updated.append(key)

    logger.info(
        "notification_prefs_updated", user_id=user_id, updated_keys=updated
    )

    # 返回最新全集（DB 视角）
    fresh = await list_notification_prefs(session, user_id=user_id)
    return {"updated_keys": updated, "total": fresh["total"]}


async def seed_default_prefs(
    session: AsyncSession, *, user_id: str
) -> dict[str, Any]:
    """首次访问时填入 6 类默认 pref（仅对缺 key 写入；不覆盖已存在）。

    Idempotent：调用多次结果一致。
    """
    existing = await list_notification_prefs(session, user_id=user_id)
    existing_keys = set(existing["prefs"].keys())

    now_ts = datetime.now(UTC)
    seeded: list[str] = []

    for key in sorted(PREF_KEYS):
        if key in existing_keys:
            continue
        default_value = DEFAULT_PREF_VALUES.get(key, {"enabled": True})
        # Use index_elements (not constraint="...") so the upsert is portable
        # and does not depend on the PK constraint's exact DB-side name.
        stmt = (
            pg_insert(UserNotificationPref)
            .values(
                user_id=user_id,
                pref_key=key,
                pref_value=default_value,
                updated_at=now_ts,
                created_by=str(user_id),
                created_time=now_ts,
                last_updated_time=now_ts,
                last_updated_by=str(user_id),
            )
            .on_conflict_do_update(
                index_elements=["user_id", "pref_key"],
                set_={"updated_at": now_ts},
            )
        )
        await session.execute(stmt)
        seeded.append(key)

    if seeded:
        logger.info(
            "notification_prefs_seeded", user_id=user_id, seeded_keys=seeded
        )

    return {"seeded_keys": seeded}


__all__ = [
    "DEFAULT_PREF_VALUES",
    "NotificationPrefError",
    "list_notification_prefs",
    "seed_default_prefs",
    "update_notification_prefs",
]
