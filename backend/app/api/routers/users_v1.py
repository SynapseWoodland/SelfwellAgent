"""M1 用户档案路由（``/api/v1/users``）。

真源：``docs/spec/SPEC-M1-wechat-login.md`` §4.3 + §4.4
+ ``docs/api/openapi.yaml`` tag ``users``。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.services.users.profile_service import (
    ProfileEnumError,
    ProfileNotFoundError,
    get_user_profile,
    update_user_profile,
)
from app.services.users.push_token_service import (
    PushTokenError,
    register_push_token,
)

router = APIRouter(prefix="/users", tags=["users"])


# ─────────────────────────────────────────────────────────────────────────────
# §一 Schema
# ─────────────────────────────────────────────────────────────────────────────
class UserProfileResponse(BaseModel):
    code: int = 0
    data: dict[str, object]


class ProfileUpdateRequest(BaseModel):
    """首登补全 / 档案更新（5 字段均可选，但至少 1 个）。"""

    age_range: str | None = Field(default=None)
    focus_parts: list[str] | None = Field(default=None)
    intensity: str | None = Field(default=None)
    preferred_time: str | None = Field(default=None)
    sitting_hours: str | None = Field(default=None)


class PushTokenRequest(BaseModel):
    push_token: str = Field(..., min_length=1, max_length=512)
    push_channel: str = Field(..., description="wx_subscribe | apns | fcm | hms | email")


class SimpleDataResponse(BaseModel):
    code: int = 0
    data: dict[str, object]


# ─────────────────────────────────────────────────────────────────────────────
# §二 路由
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="获取当前用户档案",
)
async def get_me(
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),  # noqa: B008  FastAPI Depends
) -> UserProfileResponse:
    try:
        data = await get_user_profile(session, user_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    return UserProfileResponse(data=data)


@router.post(
    "/profile",
    response_model=UserProfileResponse,
    summary="首登补全 / 档案更新",
)
async def update_profile(
    body: ProfileUpdateRequest,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),  # noqa: B008  FastAPI Depends
) -> UserProfileResponse:
    payload = body.model_dump(exclude_none=True)
    try:
        data = await update_user_profile(session, user_id, payload)
    except (ProfileEnumError, ProfileNotFoundError) as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    return UserProfileResponse(data=data)


@router.post(
    "/push-token",
    response_model=SimpleDataResponse,
    summary="注册 / 更新推送 token",
)
async def update_push_token(
    body: PushTokenRequest,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),  # noqa: B008  FastAPI Depends
) -> SimpleDataResponse:
    try:
        result = await register_push_token(
            session,
            user_id=user_id,
            push_token=body.push_token,
            push_channel=body.push_channel,
        )
    except PushTokenError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    return SimpleDataResponse(data=dict(result))


__all__ = ["router"]
