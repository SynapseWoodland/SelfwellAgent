"""Checkin ORM（M4 每日打卡）。

真源：``db/init/01-schema.sql`` §1.5 ``checkins`` + ``docs/spec/TDS-M4-checkin-loop.md``。

字段（与 DDL 1:1）：
- id (UUID, PK)
- user_id (UUID, FK -> users.id)
- plan_id (VARCHAR(64), NOT NULL) — 与 plans.id 对齐（兼容历史）
- day (INTEGER, NOT NULL) — 1-21（§5xxx ``E_CHECKIN_DAY_INVALID`` 校验）
- video_id (VARCHAR(64), NOT NULL)
- feeling (TEXT, nullable) — ≤ 50 字（§5xxx ``E_CHECKIN_FEELING_TOO_LONG``）
- audit: created_by / created_time / last_updated_time / last_updated_by
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import INTEGER, TIMESTAMP, VARCHAR, ForeignKey, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


class Checkin(Base):
    """每日打卡（M4）。"""

    __tablename__ = "checkins"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    day: Mapped[int] = mapped_column(INTEGER, nullable=False)
    video_id: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    feeling: Mapped[str | None] = mapped_column(Text, nullable=True)
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
