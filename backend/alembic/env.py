"""Alembic env（Sprint 0 骨架）。

真源：``db/init/01-schema.sql`` + ``.env`` POSTGRES_*/DATABASE_URL_SYNC。

约束：
- 从 ``app.conf.app_config`` 读 DSN（同步 psycopg 驱动）
- target_metadata 取 ``app.db.Base.metadata``（ORM 一致性兜底）
- 离线模式 / 在线模式同入口
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.conf.app_config import app_config
from app.db.base import Base

# Alembic Config object
config = context.config

# 注入 DSN（同步驱动）
_sync_dsn = app_config.db_urls.sync_url or (
    f"postgresql+psycopg://{app_config.postgres.user}:{app_config.postgres.password}"
    f"@{app_config.postgres.host}:{app_config.postgres.port}/{app_config.postgres.db}"
)
config.set_main_option("sqlalchemy.url", _sync_dsn)

# 解析 alembic.ini 的 [loggers]
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ORM 元数据
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：emit SQL 到脚本（无 DB 连接）。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：直接连 DB 执行迁移。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
