"""User Context FastAPI Router.

迁移自 api/routers/auth_v1.py + users_v1.py。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.contexts.user.application.user_service import (
    SMS_SEND_RATE_LIMIT,
    PhoneLoginError,
    ProfileNotFoundError,
    UserApplicationService,
    WxLoginError,
)
from app.core.log import logger

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Schema ──────────────────────────────────────────────────────────────────


class WxLoginRequest(BaseModel):
    code: str = Field(..., min_length=10, max_length=64)
    client: str = Field(default="wx_mp")
    user_profile: dict[str, str] | None = Field(default=None)

    model_config = {"json_schema_extra": {"examples": [{"code": "x" * 20, "client": "wx_mp"}]}}

    @field_validator("client")
    @classmethod
    def _validate_client(cls, v: str) -> str:
        if v not in {"wx_mp", "ios", "android", "harmony"}:
            raise ValueError(f"client 必须是 wx_mp/ios/android/harmony 之一，得到 {v}")
        return v


class WxLoginData(BaseModel):
    user_id: str
    access_token: str
    expires_in: int
    is_new_user: bool
    user_status: str


class WxLoginResponse(BaseModel):
    code: int = 0
    data: WxLoginData


class PhoneCodeRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11)


class PhoneCodeData(BaseModel):
    sent: bool
    remaining_seconds: int = 60


class PhoneCodeResponse(BaseModel):
    code: int = 0
    data: PhoneCodeData


class PhoneLoginRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11)
    code: str = Field(..., min_length=4, max_length=6)


# ─── Routes ─────────────────────────────────────────────────────────────────


@router.post("/wx-login", response_model=WxLoginResponse)
async def wx_login(
    body: WxLoginRequest,
    session: AsyncSession = Depends(db_session),  # noqa: B008  FastAPI Depends
) -> WxLoginResponse:
    svc = UserApplicationService(session)
    nickname = body.user_profile.get("nickname") if body.user_profile else None
    avatar = body.user_profile.get("avatar") if body.user_profile else None
    try:
        user_id, token, is_new, user_status, expires_in = await svc.wx_login(
            code=body.code,
            client=body.client,
            nickname=nickname,
            avatar=avatar,
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


@router.post("/phone-code", response_model=PhoneCodeResponse)
async def request_phone_code(body: PhoneCodeRequest) -> PhoneCodeResponse:
    # MVP: dev mode always succeeds
    return PhoneCodeResponse(
        data=PhoneCodeData(sent=True, remaining_seconds=60),
    )


@router.post("/phone-login", response_model=WxLoginResponse)
async def phone_login(
    body: PhoneLoginRequest,
    session: AsyncSession = Depends(db_session),  # noqa: B008  FastAPI Depends
) -> WxLoginResponse:
    svc = UserApplicationService(session)
    try:
        user_id, token, is_new, user_status, expires_in = await svc.phone_login(
            phone=body.phone, code=body.code
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


# suppress unused
_ = SMS_SEND_RATE_LIMIT, ProfileNotFoundError


__all__ = ["router"]
