"""Post ORM（M6 蜕变广场动态）。

真源：``db/init/01-schema.sql`` §1.6 ``posts`` + ``docs/spec/TDS-M6-plaza-community.md``。

字段（与 DDL 1:1）：
- id (UUID, PK)
- user_id (UUID, FK -> users.id)
- content (TEXT, NOT NULL) — ≤ 200 字（§6xxx ``E_COMMUNITY_CONTENT_TOO_LONG``）
- images (JSONB, DEFAULT '[]') — ≤ 9 张（§6xxx ``E_COMMUNITY_IMAGES_TOO_MANY``）
- status (VARCHAR(20), NOT NULL, DEFAULT 'pending') — pending / approved / rejected
- ai_comment (TEXT, nullable)
- official_comment (TEXT, nullable)
- like_count / comment_count (INTEGER, NOT NULL, DEFAULT 0)
- reviewed_by (UUID, FK -> users.id, nullable)
- reviewed_at (TIMESTAMPTZ, nullable)
- audit: created_by / created_time / last_updated_time / last_updated_by
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import INTEGER, TIMESTAMP, VARCHAR, ForeignKey, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


class Post(Base):
    """蜕变广场动态（M6）。"""

    __tablename__ = "posts"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    images: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, default="pending")
    ai_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    like_count: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    comment_count: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    reviewed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
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
    last_updated_by: Mapped[str] = mapped_column(
        VARCHAR(64), nullable=False, default=""
    )
