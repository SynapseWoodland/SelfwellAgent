"""UserBadge ORM（V2 IA · 勋章体系）。

真源：``plans/v2-unified-parent.md`` §2.2 + IA V2.2 §2A.2.1
+ alembic 0007_add_v2_ia_tables。

6 类枚举（与 IA V2.2 一致）：
- first_checkin / streak_7 / streak_14 / streak_21
- first_feedback / first_album_photo

字段：
- id (UUID, PK)
- user_id (UUID, FK -> users.id, CASCADE)
- code (VARCHAR(64), NOT NULL) — 枚举见上
- progress (INTEGER, NOT NULL, DEFAULT 0) — 当前进度 0..target
- target (INTEGER, NOT NULL, DEFAULT 0) — 达标阈值
- unlocked_at (TIMESTAMPTZ, nullable) — 解锁时间；NULL = 未解锁
- 唯一约束：(user_id, code)
- 审计字段
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import INTEGER, TIMESTAMP, VARCHAR, ForeignKey
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


# 6 类勋章枚举（IA V2.2 §2A.2.1）
BADGE_CODES: frozenset[str] = frozenset(
    {
        "first_checkin",
        "streak_7",
        "streak_14",
        "streak_21",
        "first_feedback",
        "first_album_photo",
    }
)


class UserBadge(Base):
    """用户勋章（V2 IA · PR-2）。"""

    __tablename__ = "user_badges"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    progress: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    target: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    unlocked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
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


__all__ = ["BADGE_CODES", "UserBadge"]
