"""Feedback ORM（M7a/M7b · 心情日记 / 多部位反馈）。

真源：``db/init/01-schema.sql`` §1.8 + ``docs/spec/facts-anchor.md`` §2.7 + ADR-0016。

字段（与 DDL 1:1）：
- id (UUID, PK)
- user_id (UUID, FK -> users.id)
- feedback_type (VARCHAR(32), NOT NULL) — 4 枚举
- text_content (TEXT, nullable) — ≤ 500 字（§11xxx E_FEEDBACK_TEXT_TOO_LONG）
- photo_url (VARCHAR(512), nullable)
- body_part (VARCHAR(32), nullable) — 6 部位枚举见 docs/data/body-parts.yaml
- ai_ack_id (UUID, FK -> ai_messages.id, nullable) — 延迟 FK
- audit: created_by / created_time / last_updated_time / last_updated_by
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import TIMESTAMP, VARCHAR, ForeignKey, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.ai_messages import AIMessage
    from app.db.models.user import User


class Feedback(Base):
    """心情日记 / 多部位反馈（M7）。

    真源 DDL: ``db/init/01-schema.sql`` §1.8
    """

    __tablename__ = "feedback"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feedback_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(VARCHAR(512), nullable=True)
    body_part: Mapped[str | None] = mapped_column(VARCHAR(32), nullable=True)
    ai_ack_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("ai_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # audit
    created_by: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    created_time: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_updated_by: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    last_updated_time: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # relationships
    user: Mapped[User] = relationship("User", back_populates="feedbacks", lazy="raise")
    ai_ack: Mapped[AIMessage | None] = relationship(
        "AIMessage", back_populates="feedbacks", lazy="raise"
    )


__all__ = ["Feedback"]
