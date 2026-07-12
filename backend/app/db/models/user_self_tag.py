"""UserSelfTag ORM（V2 IA · 自标签体系）。

真源：``plans/v2-unified-parent.md`` §2.2 + IA V2.2 §2A.2.4
+ alembic 0007_add_v2_ia_tables。

字段：
- id (UUID, PK)
- user_id (UUID, FK -> users.id, CASCADE)
- tag_category (VARCHAR(32), NOT NULL) — 4 枚举：
    body_part / concern / lifestyle / intensity
- tag_value (VARCHAR(64), NOT NULL) — 标签值
- is_selected (BOOL, NOT NULL, DEFAULT TRUE) — 是否在 profile 中显示
- source (VARCHAR(16), NOT NULL, DEFAULT 'manual') — 2 枚举：
    manual / inferred_from_feedback
- 唯一约束：(user_id, tag_category, tag_value)
- 审计字段
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BOOLEAN, TIMESTAMP, VARCHAR, ForeignKey
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


# 4 类标签枚举（IA V2.2 §2A.2.4 + alembic CHECK 约束）
TAG_CATEGORIES: frozenset[str] = frozenset(
    {"body_part", "concern", "lifestyle", "intensity"}
)
# 来源枚举
TAG_SOURCES: frozenset[str] = frozenset({"manual", "inferred_from_feedback"})


class UserSelfTag(Base):
    """用户自标签（V2 IA · PR-2）。"""

    __tablename__ = "user_self_tags"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_category: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    tag_value: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    is_selected: Mapped[bool] = mapped_column(
        BOOLEAN, nullable=False, default=True
    )
    source: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # 审计字段
    created_by: Mapped[str] = mapped_column(VARCHAR(64), nullable=False, default="")
    created_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    last_updated_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    last_updated_by: Mapped[str] = mapped_column(VARCHAR(64), nullable=False, default="")


__all__ = ["TAG_CATEGORIES", "TAG_SOURCES", "UserSelfTag"]
