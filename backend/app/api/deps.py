"""FastAPI Depends 工厂。

真源：``docs/spec/SPEC-M1-wechat-login.md`` §4.3
+ ``docs/api/openapi.yaml`` ``#/components/securitySchemes/bearerAuth``。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import JWTError, JWTExpiredError
from app.core.errors import UserInputError
from app.db.session import get_session
from app.errors.codes import E_USER_NOT_FOUND
from app.services.auth.jwt_service import verify_token

if TYPE_CHECKING:
    pass


async def db_session() -> AsyncIterator[AsyncSession]:
    """DB session 依赖（re-export 自 ``app.db.session.get_session``）。"""
    async for s in get_session():
        yield s


async def current_user_id(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> str:
    """从 ``Authorization: Bearer <jwt>`` 解析当前 user_id。

    Raises:
        HTTPException 401: token 缺失 / 过期 / 非法。

    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "E_GENERAL_UNAUTHORIZED", "message_zh": "未登录"},
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "E_GENERAL_UNAUTHORIZED", "message_zh": "Token 缺失"},
        )
    try:
        payload = verify_token(token)
    except JWTExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "E_AUTH_TOKEN_EXPIRED", "message_zh": "登录已过期"},
        ) from None
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "E_AUTH_TOKEN_INVALID", "message_zh": "Token 无效"},
        ) from None

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "E_AUTH_TOKEN_INVALID", "message_zh": "Token 缺少 sub claim"},
        )
    return user_id


async def require_user_exists(
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),  # noqa: B008  FastAPI Depends
) -> str:
    """依赖：要求 user_id 对应的 user 存在。"""
    from sqlalchemy import select

    from app.db.models.user import User

    stmt = select(User.id).where(User.id == user_id).limit(1)
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": E_USER_NOT_FOUND, "message_zh": "用户不存在"},
        )
    return user_id


def get_request_id(
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> str | None:
    """读取 X-Request-ID header（可空；中间件层有兜底）。"""
    if x_request_id and len(x_request_id) > 128:
        raise UserInputError("X-Request-ID 过长", field="X-Request-ID")
    return x_request_id


__all__ = [
    "current_user_id",
    "db_session",
    "get_request_id",
    "require_user_exists",
]
