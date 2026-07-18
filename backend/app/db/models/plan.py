"""Plan ORM（M3 21 天方案）。

真源：``db/init/01-schema.sql`` §1.4 ``plans`` + ``docs/spec/TDS-M3-21day-plan.md``。

字段（与 DDL 1:1）：
- id (UUID, PK)
- user_id (UUID, FK -> users.id)
- report_id (VARCHAR(64), NOT NULL) — 与 reports.id 对齐（兼容历史雪花 ID）
- days (JSONB, NOT NULL) — 21 天逐日内容
- status (VARCHAR(20), NOT NULL, DEFAULT 'active') — active / paused / completed / abandoned
- started_at / completed_at (DATE, nullable)
- audit: created_by / created_time / last_updated_time / last_updated_by
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DATE, TIMESTAMP, VARCHAR, ForeignKey
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


class Plan(Base):
    """21 天方案（M3）。"""

    __tablename__ = "plans"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_id: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    days: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, default="active")
    started_at: Mapped[date | None] = mapped_column(DATE, nullable=True)
    completed_at: Mapped[date | None] = mapped_column(DATE, nullable=True)
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
