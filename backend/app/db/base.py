"""SQLAlchemy 2.0 DeclarativeBase 根。

真源：``docs/spec/facts-anchor.md`` §2 + ``db/init/01-schema.sql``（11 张业务表）
+ ``docs/data/data-dictionary.md``（字段级数据字典）

约定（与 SKILL.md §一/§五 对齐）：
- 表名与字段名与 SQL DDL 1:1（snake_case / VARCHAR(N) / JSONB / TIMESTAMPTZ）
- ``__tablename__`` **强制显式声明**（不依赖默认 lowercase；防止类名拼写差异引入隐 bug）
- 主键统一 ``UUID`` 类型（PostgreSQL 18 原生 ``uuidv7()``；SQLAlchemy 侧用 Python 端
  生成 UUIDv4 fallback；业务依赖 DB 默认 ``uuidv7()`` 时由 Alembic 迁移注入）
- 软删除统一 ``deleted_at: TIMESTAMPTZ | None``
- 审计字段保留原 DDL 风格：``created_time`` / ``last_updated_time`` /
  ``created_by`` / ``last_updated_by``（业务写入，其余交由 middleware 兜底）
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM Model 的根。

    SQLAlchemy 2.0 风格 ``Mapped[...]`` 类型注解；不混入 dataclass 自动生成
    （业务主键在 Python 端可控生成，便于 repo 层显式构造）。
    """
