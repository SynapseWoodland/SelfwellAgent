"""Report ORM（M2 AI 诊断报告）。

真源：``db/init/01-schema.sql`` §1.2 ``reports``。

字段（与 DDL 1:1）：
- id (UUID, PK)
- user_id (UUID, FK -> users.id)
- photos / directions / tags (JSONB, NOT NULL)
- summary (TEXT, nullable)
- llm_model (VARCHAR(50), nullable)
- llm_cost (DECIMAL(10,4), NOT NULL, DEFAULT 0)
- created_at / deleted_at (TIMESTAMPTZ)
- audit: created_by / created_time / last_updated_time / last_updated_by
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DECIMAL, TIMESTAMP, VARCHAR, ForeignKey, String, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


class Report(Base):
    """AI 诊断报告（M2）。"""

    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    photos: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    directions: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    tags: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_model: Mapped[str | None] = mapped_column(VARCHAR(50), nullable=True)
    llm_cost: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=10, scale=4), nullable=False, default=Decimal("0.0000")
    )
    # Async pipeline 状态（PR-A1 引入）：
    # - 同步 LLM 路径不写此列，保持 NULL（向后兼容现有 78 个测试）
    # - async 路径写入 queued → running → ready / failed（与 JobStateStore 对齐）
    status: Mapped[str | None] = mapped_column(String(16), nullable=True, default=None)
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
