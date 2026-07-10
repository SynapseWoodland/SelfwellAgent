"""FastAPI Depends 工厂。

真源：``docs/spec/SPEC-M1-wechat-login.md`` §4.3
+ ``docs/api/openapi.yaml`` ``#/components/securitySchemes/bearerAuth``。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from fastapi import Depends, Header, HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import JWTError, JWTExpiredError
from app.conf.app_config import app_config
from app.core.errors import UserInputError
from app.db.session import get_session
from app.errors.codes import E_USER_NOT_FOUND
from app.services.auth.jwt_service import verify_token

if TYPE_CHECKING:
    pass

# ─────────────────────────────────────────────────────────────────────────────
# §一 DB Session
# ─────────────────────────────────────────────────────────────────────────────


async def db_session() -> AsyncIterator[AsyncSession]:
    """DB session 依赖（re-export 自 ``app.db.session.get_session``）。"""
    async for s in get_session():
        yield s


# ─────────────────────────────────────────────────────────────────────────────
# §二 Redis Client（per-request connection）
# ─────────────────────────────────────────────────────────────────────────────
_redis_pool: Redis | None = None


async def get_redis() -> AsyncIterator[Redis]:
    """Redis 连接池依赖（lazy init；连接失败时返回 RedisError 透传到路由层）。

    幂等：首次调用后 `_redis_pool` 持有单例连接池；重复调用 yield 同一实例。
    """
    global _redis_pool
    if _redis_pool is None:
        cfg = app_config.redis
        url = cfg.url or f"redis://{cfg.host}:{cfg.port}/{cfg.db}"
        password = cfg.password or None
        _redis_pool = Redis.from_url(
            url,
            password=password,
            decode_responses=False,
        )
    try:
        yield _redis_pool
    except RedisError:
        # Redis 不可用时：路由层决定降级策略（当前 assistant_v1.py 透传异常）
        raise


# ─────────────────────────────────────────────────────────────────────────────
# §三 Auth
# ─────────────────────────────────────────────────────────────────────────────


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
    "get_redis",
    "get_request_id",
    "require_user_exists",
]
