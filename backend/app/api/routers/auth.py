"""微信小程序登录（Sprint 1 M1）。

真源：``docs/spec/SPEC-M1-wechat-login.md``。

流程：``wx.login()`` code → code2session(openid) → 查询/创建 user → JWT。

无状态接口，所有上下文由 JWT 承载。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import JWTError, sign_access_token
from app.auth.wechat_client import WeChatClient, WeChatClientError
from app.core.log import logger
from app.db.session import get_session


# ─────────────────────────────────────────────────────────────────────────────
# §一 Schema
# ─────────────────────────────────────────────────────────────────────────────
class WxLoginRequest(BaseModel):
    """微信小程序登录请求。

    小程序前端调用 ``wx.login()`` 后，将返回的 code 发送至此接口。
    """

    code: str = Field(..., min_length=10, max_length=64, description="wx.login() 返回的 code")


class WxLoginResponse(BaseModel):
    """登录成功响应。"""

    access_token: str = Field(..., description="JWT access token")
    user_id: str = Field(..., description="用户 UUID（sub claim）")


# ─────────────────────────────────────────────────────────────────────────────
# §二 路由
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/wx-login",
    response_model=WxLoginResponse,
    summary="微信小程序登录（code 换 openid → JWT）",
)
async def wx_login(
    body: WxLoginRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> WxLoginResponse:
    """微信小程序登录。

    1. 用 code 调用微信 ``jscode2session`` 换 openid
    2. 用 openid 查询/创建用户记录（upsert by openid_mp）
    3. 签发 JWT 并返回

    Raises:
        401: 微信 code 无效或已过期
        503: 微信服务不可用
        500: 内部错误

    """
    # 1. 调用微信接口
    try:
        client = WeChatClient()
        wx_resp: dict[str, str] = await client.code2session(body.code)
    except WeChatClientError as exc:
        logger.warning("wx_login_code2session_failed", code=body.code[:8])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.code, "message_zh": exc.message_zh},
        ) from exc
    except Exception:
        logger.exception("wx_login_code2session_error")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "E_GENERAL_SERVICE_UNAVAILABLE", "message_zh": "微信服务暂不可用"},
        ) from None

    openid: str | None = wx_resp.get("openid")
    if not openid:
        logger.warning("wx_login_no_openid", wx_resp_keys=list(wx_resp.keys()))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "E_AUTH_CODE_INVALID", "message_zh": "微信授权失败：未获取到 openid"},
        )

    logger.info("wx_code2session_ok", openid=openid[:12])

    # 2. Upsert 用户（by openid_mp）
    try:
        user_id: str = await _upsert_user_by_openid_mp(session, openid)
    except Exception as exc:
        logger.exception("wx_login_upsert_user_failed", openid=openid[:12])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "E_GENERAL_INTERNAL_ERROR", "message_zh": "用户创建失败"},
        ) from exc

    # 3. 签发 JWT
    try:
        token: str = sign_access_token(
            user_id=user_id,
            extra_claims={"platform": "wx_mp", "openid_mp": openid},
        )
    except JWTError as exc:
        logger.exception("wx_login_sign_token_failed", user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "E_GENERAL_INTERNAL_ERROR", "message_zh": "Token 签发失败"},
        ) from exc

    logger.info("wx_login_success", user_id=user_id, openid=openid[:12])
    return WxLoginResponse(access_token=token, user_id=user_id)


# ─────────────────────────────────────────────────────────────────────────────
# §三 Upsert 用户
# ─────────────────────────────────────────────────────────────────────────────
async def _upsert_user_by_openid_mp(session: AsyncSession, openid: str) -> str:
    """按 openid_mp 查询用户，若不存在则创建。

    Returns:
        用户 UUID 字符串。

    """
    from app.db.models.user import User

    # 查询
    stmt = select(User).where(User.openid_mp == openid)
    result = await session.execute(stmt)
    user: User | None = result.scalar_one_or_none()

    if user is not None:
        return str(user.id)

    # 创建（首次登录）
    now_ts = datetime.now(UTC)
    new_user = User(
        id=uuid4(),
        unionid=f"wx_openid_{openid}",  # unionid 不可用时用 openid 占位
        openid_mp=openid,
        platform="wx_mp",
        nickname="微信用户",
        avatar="",
        created_at=now_ts,
        last_active_at=now_ts,
        created_by="wx-login",
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by="wx-login",
        version=0,
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    logger.info("wx_user_created", user_id=str(new_user.id), openid=openid[:12])
    return str(new_user.id)


__all__ = ["router"]
