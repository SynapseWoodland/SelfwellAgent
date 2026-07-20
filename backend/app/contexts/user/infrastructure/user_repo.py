"""User Repository — Infrastructure Layer.

封装 User ORM 查询，从 services/ 迁入。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User as UserOrm

if TYPE_CHECKING:
    pass


class IUserRepository(Protocol):
    """User Repository 接口（DDD Infrastructure 层）。"""

    async def find_by_id(self, user_id: UUID) -> UserOrm | None: ...
    async def find_by_openid_mp(self, openid: str) -> UserOrm | None: ...
    async def find_by_phone(self, phone: str) -> UserOrm | None: ...


class UserRepository:
    """User Repository 实现。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, user_id: UUID) -> UserOrm | None:
        stmt = select(UserOrm).where(UserOrm.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_openid_mp(self, openid: str) -> UserOrm | None:
        stmt = select(UserOrm).where(UserOrm.openid_mp == openid)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_openid_app(self, openid: str) -> UserOrm | None:
        stmt = select(UserOrm).where(UserOrm.openid_app == openid)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_unionid(self, unionid: str) -> UserOrm | None:
        stmt = select(UserOrm).where(UserOrm.unionid == unionid)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_phone(self, phone: str) -> UserOrm | None:
        stmt = select(UserOrm).where(UserOrm.phone == phone)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


__all__ = ["IUserRepository", "UserRepository"]
