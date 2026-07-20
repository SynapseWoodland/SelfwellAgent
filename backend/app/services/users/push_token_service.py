"""推送 Token 注册服务（M1-FR-05 / M9 推送门面共用）。

真源：``docs/spec/TDS-M1-wechat-login.md`` §4.4 + §5.3
+ ``docs/architecture/api.yaml`` ``#/components/schemas/PushTokenPayload``。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UserInputError
from app.db.models.user import User
from app.errors.codes import E_USER_NOT_FOUND, E_USER_PUSH_CHANNEL_INVALID

# 合法 push_channel 枚举（与 User ORM CHECK 约束对齐 + ADR-0008）
_PUSH_CHANNELS: frozenset[str] = frozenset({"wx_subscribe", "apns", "fcm", "hms", "email"})


class PushTokenError(UserInputError):
    """推送 token 注册失败。"""

    code: str = E_USER_PUSH_CHANNEL_INVALID
    message_zh: str = "推送渠道非法"
    message_en: str = "Invalid push channel"
    http_status = 400


async def register_push_token(
    session: AsyncSession,
    *,
    user_id: str,
    push_token: str,
    push_channel: str,
) -> dict[str, str]:
    """注册 / 更新推送 token。

    Args:
        session: AsyncSession。
        user_id: 用户 UUID 字符串。
        push_token: APNs/FCM/HMS/WX 推送 token。
        push_channel: 5 档之一。

    Returns:
        ``{"user_id": ..., "push_channel": ...}``。

    Raises:
        PushTokenError: push_channel 非法 / token 缺失。
        UserInputError: user 不存在。

    """
    if push_channel not in _PUSH_CHANNELS:
        raise PushTokenError(field="push_channel", value=push_channel)
    if not push_token or len(push_token) > 512:
        raise PushTokenError(field="push_token", reason="missing_or_too_long")

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise UserInputError(
            "用户不存在",
            code=E_USER_NOT_FOUND,
            http_status=404,
            field="user_id",
        )
    now_ts = datetime.now(UTC)
    user.push_token = push_token
    user.push_channel = push_channel
    user.last_active_at = now_ts
    user.last_updated_time = now_ts
    user.last_updated_by = user_id          # 当前更新用户（注册推送的人）
    await session.flush()
    return {"user_id": str(user.id), "push_channel": push_channel}


def default_push_channel_for(platform: str) -> str:
    """根据 platform 返回默认 push_channel（M1 §5.3）。"""
    return {
        "wx_mp": "wx_subscribe",
        "ios": "apns",
        "android": "fcm",
        "harmony": "hms",
    }.get(platform, "email")


__all__ = [
    "PushTokenError",
    "default_push_channel_for",
    "register_push_token",
]
