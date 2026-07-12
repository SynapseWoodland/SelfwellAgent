"""用户档案服务（首登补全 + 通用 get_me / update_me）。

真源：``docs/spec/SPEC-M1-wechat-login.md`` §3.1 + §4.3。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UserInputError
from app.core.log import logger
from app.db.models.user import User
from app.errors.codes import E_USER_INVALID_ENUM, E_USER_INVALID_INPUT, E_USER_NOT_FOUND

# 5 个 age_range 档位（与 SPEC-M1 §3.1 + User ORM CHECK 对齐）
_AGE_RANGES: frozenset[str] = frozenset({"18-22", "23-28", "29-35", "36-45", "45+"})
# intensity 枚举（SPEC-M1 §3.1 中文值）
_INTENSITIES: frozenset[str] = frozenset({"轻柔", "适中", "进阶"})
# preferred_time 枚举（SPEC-M1 §3.1 中文值）
_PREFERRED_TIMES: frozenset[str] = frozenset({"早", "中", "晚", "不固定"})
# sitting_hours 范围 0-24（小时）
_SITTING_HOURS_MIN = 0
_SITTING_HOURS_MAX = 24
# focus_parts 6 部位（与 docs/data/body-parts.yaml 一致）
_FOCUS_PARTS: frozenset[str] = frozenset(
    {"face", "head", "shoulder_neck", "waist", "leg", "overall_look"}
)


class ProfileNotFoundError(UserInputError):
    """用户不存在。"""

    code: str = E_USER_NOT_FOUND
    message_zh: str = "用户不存在"
    message_en: str = "User not found"
    http_status = 404


class ProfileEnumError(UserInputError):
    """枚举字段非法值。"""

    code: str = E_USER_INVALID_ENUM
    message_zh: str = "字段值不在允许范围内"
    message_en: str = "Field value not in allowed enum set"
    http_status = 400


def _ensure_str(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProfileEnumError(f"{field} 必须是字符串", field=field)
    return value


def _ensure_list(value: object, field: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ProfileEnumError(f"{field} 必须是列表", field=field)
    return [str(v) for v in value]


def validate_profile(payload: dict[str, Any]) -> dict[str, Any]:
    """校验首登档案字段。返回标准化后的 dict（只含有效字段）。"""
    result: dict[str, Any] = {}

    age_range = _ensure_str(payload.get("age_range"), "age_range")
    if age_range is not None and age_range not in _AGE_RANGES:
        raise ProfileEnumError(
            "age_range 不在 5 档内",
            field="age_range",
            allowed=sorted(_AGE_RANGES),
        )
    if age_range is not None:
        result["age_range"] = age_range

    focus_parts = _ensure_list(payload.get("focus_parts"), "focus_parts")
    if focus_parts is not None:
        invalid = [p for p in focus_parts if p not in _FOCUS_PARTS]
        if invalid:
            raise ProfileEnumError(
                "focus_parts 包含非法部位",
                field="focus_parts",
                invalid=invalid,
            )
        result["focus_parts"] = focus_parts

    intensity = _ensure_str(payload.get("intensity"), "intensity")
    if intensity is not None and intensity not in _INTENSITIES:
        raise ProfileEnumError(
            "intensity 枚举非法",
            field="intensity",
            allowed=sorted(_INTENSITIES),
        )
    if intensity is not None:
        result["intensity"] = intensity

    preferred_time = _ensure_str(payload.get("preferred_time"), "preferred_time")
    if preferred_time is not None and preferred_time not in _PREFERRED_TIMES:
        raise ProfileEnumError(
            "preferred_time 枚举非法",
            field="preferred_time",
            allowed=sorted(_PREFERRED_TIMES),
        )
    if preferred_time is not None:
        result["preferred_time"] = preferred_time

    sitting_hours = _ensure_str(payload.get("sitting_hours"), "sitting_hours")
    if sitting_hours is not None and sitting_hours != "":
        if not sitting_hours.isdigit():
            raise ProfileEnumError(
                "sitting_hours 必须是 0-24 的整数",
                field="sitting_hours",
                allowed=[str(i) for i in range(_SITTING_HOURS_MIN, _SITTING_HOURS_MAX + 1)],
            )
        value = int(sitting_hours)
        if value < _SITTING_HOURS_MIN or value > _SITTING_HOURS_MAX:
            raise ProfileEnumError(
                "sitting_hours 超出范围",
                field="sitting_hours",
                allowed=[str(i) for i in range(_SITTING_HOURS_MIN, _SITTING_HOURS_MAX + 1)],
            )
        result["sitting_hours"] = sitting_hours

    if not result:
        raise UserInputError(
            "未提供任何档案字段",
            code=E_USER_INVALID_INPUT,
            http_status=400,
            field="payload",
        )
    return result


async def get_user_profile(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """获取用户档案。"""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise ProfileNotFoundError(field="user_id", user_id=user_id)
    return _serialize_user(user)


async def update_user_profile(
    session: AsyncSession, user_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """更新用户档案（首登补全 / 日常修改）。"""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise ProfileNotFoundError(field="user_id", user_id=user_id)

    patch = validate_profile(payload)
    now_ts = datetime.now(UTC)
    for k, v in patch.items():
        setattr(user, k, v)
    user.last_active_at = now_ts
    user.last_updated_time = now_ts
    user.last_updated_by = user_id          # 当前更新用户（改自己档案的人）
    # 首登补全：5 字段齐了立即转正（AC-M1-04）
    if user.status == "draft" and _has_minimum_profile(user):
        user.status = "active"
        logger.info("user_promoted_on_profile_complete", user_id=user_id)
    await session.flush()
    return _serialize_user(user)


def _has_minimum_profile(user: User) -> bool:
    """检查是否满足 5 字段首登要求。"""
    return bool(
        user.age_range
        and user.focus_parts
        and user.intensity
        and user.preferred_time
        and user.sitting_hours
    )


def _serialize_user(user: User) -> dict[str, Any]:
    """User ORM -> 响应 dict。

    字段名对齐 ``docs/api/openapi.yaml`` V1.1 + 前端 ``UserMe`` 类型。
    PR-2（V2 IA）增量：响应顶层加 ``badges_summary`` + ``streak_days``（PR-3 today/profile-new 用）。
    """
    cache = user.report_cache if isinstance(user.report_cache, dict) else {}
    return {
        "user_id": str(user.id),
        "user_id_pseudo": str(user.id),
        "nickname": user.nickname or "",
        "avatar": user.avatar or "",
        "avatar_url": user.avatar or "",
        "age_range": user.age_range,
        "focus_parts": user.focus_parts or [],
        "intensity": user.intensity,
        "preferred_time": user.preferred_time,
        "sitting_hours": user.sitting_hours,
        "push_channel": user.push_channel,
        "email": user.email,
        "phone": user.phone,
        "status": user.status or "draft",
        "current_streak_days": int(cache.get("streak_days", 0)),
        "fragments": int(cache.get("fragments", 0)),
        "version": user.version,
        "registered_at": user.created_at.isoformat() if user.created_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
        # PR-2 V2 增量：badges_summary / streak_days（PR-3 today/profile-new 用）
        # 字段值需异步加载时由 router 层注入；此层只放同步可达的占位，避免循环 import。
        "badges_summary": {
            "total_unlocked": 0,
            "total_codes": 6,
            "latest_unlocked": None,
        },
        "streak_days": int(cache.get("streak_days", 0)),
    }


__all__ = [
    "ProfileEnumError",
    "ProfileNotFoundError",
    "get_user_profile",
    "update_user_profile",
    "validate_profile",
]
