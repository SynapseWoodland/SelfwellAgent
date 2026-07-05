"""异步 SQLAlchemy 引擎 + Session 工厂 + get_session DI（Sprint 0 骨架）。

真源：``backend/db/init/01-schema.sql`` + ``.env`` POSTGRES_* / DATABASE_URL。

约定：
- 异步驱动：``asyncpg``（主）+ ``psycopg``（Alembic 同步迁移）
- **不要**在业务代码里直接 ``async with engine.begin()`` —— 必须走 ``Depends(get_session)``
  （与 FastAPI DI 集成；测试时覆盖为 ``test_engine``）
- ``get_session()`` 是 generator-yield DI 友好的 FastAPI dependency；返回 ``AsyncSession``
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.conf.app_config import app_config

if TYPE_CHECKING:
    pass

# ─────────────────────────────────────────────────────────────────────────────
# §一 引擎与 Session 工厂（延迟初始化，避免 import 时强制读 .env）
# ─────────────────────────────────────────────────────────────────────────────
_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _build_dsn() -> str:
    """从 ``app_config`` 拼 async DSN；空 DSN 时回落 ``sqlite+aiosqlite``。"""
    urls = app_config.db_urls
    if urls.url:
        return urls.url
    pg = app_config.postgres
    return f"postgresql+asyncpg://{pg.user}:{pg.password}@{pg.host}:{pg.port}/{pg.db}"


def get_engine() -> AsyncEngine:
    """获取全局 ``AsyncEngine`` 单例。"""
    global _engine
    if _engine is None:
        dsn = _build_dsn()
        _engine = create_async_engine(
            dsn,
            pool_size=app_config.postgres.pool_size,
            pool_recycle=app_config.postgres.pool_recycle,
            future=True,
            echo=False,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """获取全局 ``async_sessionmaker`` 单例。"""
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
            class_=AsyncSession,
        )
    return _sessionmaker


# ─────────────────────────────────────────────────────────────────────────────
# §二 FastAPI Dependency（generator-yield 风格）
# ─────────────────────────────────────────────────────────────────────────────
async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI DI 入口：每个请求一个 session，结束后自动关闭。

    Example:
        >>> from fastapi import Depends
        >>> async def handler(session: AsyncSession = Depends(get_session)):
        ...     result = await session.execute(...)

    """
    sm = get_sessionmaker()
    async with sm() as session:
        try:
            yield session
        finally:
            await session.close()


# ─────────────────────────────────────────────────────────────────────────────
# §三 测试 / 关闭辅助
# ─────────────────────────────────────────────────────────────────────────────
async def dispose_engine() -> None:
    """在测试 teardown / 应用 shutdown 时关闭 engine 释放连接池。"""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None


def set_engine_for_test(engine: AsyncEngine | None) -> None:
    """测试用：覆盖默认 engine（inject test_engine）。"""
    global _engine, _sessionmaker
    _engine = engine
    if engine is not None:
        _sessionmaker = async_sessionmaker(
            bind=engine, expire_on_commit=False, autoflush=False, class_=AsyncSession
        )
    else:
        _sessionmaker = None


__all__ = [
    "dispose_engine",
    "get_engine",
    "get_session",
    "get_sessionmaker",
    "set_engine_for_test",
]
