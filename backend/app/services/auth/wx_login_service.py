"""微信登录业务服务层（M1-FR-01 / M1-FR-02 / M1-FR-03 / M1-FR-05 / M1-FR-06）。

真源：``docs/spec/SPEC-M1-wechat-login.md`` V1.1 §2 + §5。

核心流程：
1. ``code`` -> 微信 ``jscode2session`` 换 openid + session_key（可能含 unionid）
2. APP 端：``code`` -> 微信开放平台 OAuth -> openid_app + unionid
3. 用 openid / unionid 查询 user 表（unionid 跨端打通）
4. 命中 -> 更新 platform / last_active_at；未命中 -> 新建 draft user
5. 签发 JWT
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.wechat_client import WeChatClient, WeChatClientError
from app.core.errors import SelfwellError, UserInputError
from app.core.log import logger
from app.db.models import Feedback  # noqa: F401  trigger mapper configure before User use
from app.db.models.user import User
from app.errors.codes import (
    E_AUTH_CODE_INVALID,
    E_AUTH_UNIONID_MISMATCH,
    E_USER_INVALID_INPUT,
)
from app.services.auth.jwt_service import issue_token

# 合法 platform 枚举（与 User ORM CHECK 约束对齐 + facts-anchor §3.1）
_VALID_PLATFORMS: frozenset[str] = frozenset({"wx_mp", "ios", "android", "harmony"})


class WxLoginError(SelfwellError):
    """微信登录业务异常（封装 4xx/5xx 错误码）。"""

    code: str = E_AUTH_CODE_INVALID
    message_zh: str = "微信授权失败"
    message_en: str = "WeChat login failed"
    severity = "USER_ERROR"
    http_status = 401


class UnionidMismatchError(WxLoginError):
    """encryptedData 解密失败 / iv 不匹配（与预期 unionid 不符）。"""

    code: str = E_AUTH_UNIONID_MISMATCH
    message_zh: str = "微信 unionid 解密失败，请重试"
    message_en: str = "Failed to decrypt WeChat unionid"


def _validate_platform(client: str) -> str:
    if client not in _VALID_PLATFORMS:
        raise UserInputError(
            "client/platform 非法",
            code=E_USER_INVALID_INPUT,
            http_status=400,
            field="client",
        )
    return client


async def _find_user_by_openid(
    session: AsyncSession, *, openid_mp: str | None, openid_app: str | None, unionid: str | None
) -> User | None:
    """按 openid_mp / openid_app / unionid 顺序查询 user。"""
    if openid_mp:
        stmt = select(User).where(User.openid_mp == openid_mp)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is not None:
            return user
    if openid_app:
        stmt = select(User).where(User.openid_app == openid_app)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is not None:
            return user
    if unionid:
        stmt = select(User).where(User.unionid == unionid)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    return None


async def _create_draft_user(  # noqa: PLR0913  draft user constructor needs 7 kwargs
    session: AsyncSession,
    *,
    openid_mp: str | None,
    openid_app: str | None,
    unionid: str | None,
    platform: str,
    nickname: str | None = None,
    avatar: str | None = None,
) -> User:
    """创建 draft 用户（status='draft'）。"""
    now_ts = datetime.now(UTC)
    new_user = User(
        id=uuid4(),
        unionid=unionid or f"wx_openid_{openid_mp or openid_app or uuid4()}",
        openid_mp=openid_mp,
        openid_app=openid_app,
        platform=platform,
        nickname=nickname or "微信用户",
        avatar=avatar or "",
        status="draft",
        created_at=now_ts,
        last_active_at=now_ts,
        created_by="wx-login",
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by="wx-login",
        version=0,
    )
    session.add(new_user)
    await session.flush()
    logger.info(
        "wx_user_created",
        user_id=str(new_user.id),
        platform=platform,
        is_new=True,
    )
    return new_user


async def _update_user_login(
    user: User,
    *,
    openid_mp: str | None = None,
    openid_app: str | None = None,
    platform: str,
) -> None:
    """登录后更新 platform / last_active_at / openid_* 字段。"""
    user.platform = platform
    user.last_active_at = datetime.now(UTC)
    user.last_updated_time = user.last_active_at
    user.last_updated_by = "wx-login"
    if openid_mp and user.openid_mp != openid_mp:
        user.openid_mp = openid_mp
    if openid_app and user.openid_app != openid_app:
        user.openid_app = openid_app


async def login_via_wx(
    session: AsyncSession,
    *,
    code: str,
    client: str,
    user_profile_nickname: str | None = None,
    user_profile_avatar: str | None = None,
) -> tuple[str, str, bool, str, int]:
    """微信登录主入口。

    Args:
        session: DB session（外部控制事务）。
        code: 前端 ``wx.login()`` 或 APP OAuth 的 auth_code。
        client: ``wx_mp`` / ``ios`` / ``android`` / ``harmony``。
        user_profile_nickname: 首次登录同步昵称（可选）。
        user_profile_avatar: 首次登录同步头像（可选）。

    Returns:
        ``(user_id, token, is_new_user, user_status, expires_in)``。

    Raises:
        UserInputError: client 非法。
        WxLoginError: 微信 code 无效 / unionid mismatch。
        WeChatClientError: 微信侧 4xx。

    """
    platform = _validate_platform(client)

    if not code or len(code) < 10:
        raise UserInputError(
            "code 缺失或过短",
            code=E_USER_INVALID_INPUT,
            http_status=400,
            field="code",
        )

    # 1. code2session（含 openid_mp / openid_app / unionid 兼容）
    wx_client = WeChatClient()
    try:
        wx_resp: dict[str, str] = await wx_client.code2session(code)
    except WeChatClientError as exc:
        logger.warning("wx_login_code2session_failed", code=code[:8], error=str(exc))
        raise WxLoginError(
            "微信授权码无效或已过期",
            code=exc.code,
            http_status=exc.http_status,
        ) from exc

    openid_mp = wx_resp.get("openid") if client == "wx_mp" else None
    openid_app = wx_resp.get("openid") if client != "wx_mp" else None
    unionid = wx_resp.get("unionid")

    # 2. 查 user
    user = await _find_user_by_openid(
        session, openid_mp=openid_mp, openid_app=openid_app, unionid=unionid
    )
    is_new = user is None
    if user is None:
        user = await _create_draft_user(
            session,
            openid_mp=openid_mp,
            openid_app=openid_app,
            unionid=unionid,
            platform=platform,
            nickname=user_profile_nickname,
            avatar=user_profile_avatar,
        )
    else:
        await _update_user_login(
            user, openid_mp=openid_mp, openid_app=openid_app, platform=platform
        )

    await session.flush()

    # 3. 签发 JWT
    token, expires_in = issue_token(
        user_id=str(user.id),
        platform=platform,
        openid_mp=user.openid_mp,
        openid_app=user.openid_app,
        unionid=user.unionid,
    )
    logger.info(
        "wx_login_success",
        user_id=str(user.id),
        platform=platform,
        is_new=is_new,
        user_status=user.status,
    )
    return (
        str(user.id),
        token,
        is_new,
        user.status or "draft",
        expires_in,
    )


__all__ = [
    "UnionidMismatchError",
    "WxLoginError",
    "login_via_wx",
]
