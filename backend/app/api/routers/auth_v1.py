"""M1 认证路由（``/api/v1/auth``）。

真源：``docs/spec/TDS-M1-wechat-login.md`` §4.1 + §4.2
+ ``docs/api/openapi.yaml`` tag ``auth``。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.core.log import logger
from app.services.auth.phone_login_service import (
    SMS_SEND_RATE_LIMIT,
    PhoneLoginError,
    login_via_phone,
    request_sms_code,
)
from app.services.auth.wx_login_service import WxLoginError, login_via_wx

router = APIRouter(prefix="/auth", tags=["auth"])


# ─────────────────────────────────────────────────────────────────────────────
# §一 Schema
# ─────────────────────────────────────────────────────────────────────────────
class WxLoginRequest(BaseModel):
    """微信登录请求（小程序 + APP 共用）。"""

    code: str = Field(..., min_length=10, max_length=64, description="wx.login() / OAuth auth_code")
    client: str = Field(default="wx_mp", description="wx_mp | ios | android | harmony")
    user_profile: dict[str, str] | None = Field(
        default=None, description="首次登录同步的档案（nickname/avatar）"
    )

    model_config = {"json_schema_extra": {"examples": [{"code": "x" * 20, "client": "wx_mp"}]}}

    @field_validator("client")
    @classmethod
    def _validate_client(cls, v: str) -> str:
        if v not in {"wx_mp", "ios", "android", "harmony"}:
            raise ValueError(f"client 必须是 wx_mp/ios/android/harmony 之一，得到 {v}")
        return v


class WxLoginData(BaseModel):
    """登录返回 data。"""

    user_id: str
    access_token: str
    expires_in: int
    is_new_user: bool
    user_status: str


class WxLoginResponse(BaseModel):
    code: int = 0
    data: WxLoginData


class PhoneCodeRequest(BaseModel):
    """请求发送短信验证码。"""

    phone: str = Field(..., min_length=11, max_length=11, description="11 位手机号")


class PhoneCodeData(BaseModel):
    sent: bool
    remaining_seconds: int = 60


class PhoneCodeResponse(BaseModel):
    code: int = 0
    data: PhoneCodeData


class PhoneLoginRequest(BaseModel):
    """手机号 + 验证码登录。"""

    phone: str = Field(..., min_length=11, max_length=11)
    code: str = Field(..., min_length=4, max_length=6)


# ─────────────────────────────────────────────────────────────────────────────
# §二 路由
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/wx-login",
    response_model=WxLoginResponse,
    summary="微信小程序 / APP 登录",
)
async def wx_login(
    body: WxLoginRequest,
    session: AsyncSession = Depends(db_session),  # noqa: B008  FastAPI Depends
) -> WxLoginResponse:
    """``code`` -> 微信 ``jscode2session`` -> upsert user -> JWT。"""
    nickname = None
    avatar = None
    if body.user_profile:
        nickname = body.user_profile.get("nickname")
        avatar = body.user_profile.get("avatar")
    try:
        user_id, token, is_new, user_status, expires_in = await login_via_wx(
            session,
            code=body.code,
            client=body.client,
            user_profile_nickname=nickname,
            user_profile_avatar=avatar,
        )
    except WxLoginError as exc:
        logger.warning("wx_login_failed", code=body.code[:8], error_code=exc.code)
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    return WxLoginResponse(
        data=WxLoginData(
            user_id=user_id,
            access_token=token,
            expires_in=expires_in,
            is_new_user=is_new,
            user_status=user_status,
        ),
    )


@router.post(
    "/phone-code",
    response_model=PhoneCodeResponse,
    summary="请求发送短信验证码（APP 端回退）",
)
async def request_phone_code(body: PhoneCodeRequest) -> PhoneCodeResponse:
    """MVP 阶段：开发态固定验证码，60s 内 ≥ 5 次拒发。"""
    try:
        await request_sms_code(body.phone, recent_send_count=0)
    except PhoneLoginError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    return PhoneCodeResponse(
        data=PhoneCodeData(
            sent=True,
            remaining_seconds=60,
            # 触发剩余次数的提示（语义化）
        ),
    )


@router.post(
    "/phone-login",
    response_model=WxLoginResponse,
    summary="手机号 + 验证码登录",
)
async def phone_login(
    body: PhoneLoginRequest,
    session: AsyncSession = Depends(db_session),  # noqa: B008  FastAPI Depends
) -> WxLoginResponse:
    """手机号 + 验证码登录（M1 §4.2）。"""
    try:
        user_id, token, is_new, user_status, expires_in = await login_via_phone(
            session, phone=body.phone, code=body.code
        )
    except PhoneLoginError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    return WxLoginResponse(
        data=WxLoginData(
            user_id=user_id,
            access_token=token,
            expires_in=expires_in,
            is_new_user=is_new,
            user_status=user_status,
        ),
    )


__all__ = ["router"]


# 抑制 unused warning
_ = SMS_SEND_RATE_LIMIT
