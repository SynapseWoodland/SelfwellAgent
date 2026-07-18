"""RecallSession ORM（M8 主动回忆业务事件）。

真源：``db/init/01-schema.sql`` §1.9 ``recall_sessions`` +
``docs/spec/TDS-M8-recall.md`` + ADR-0017 Recall Safety。

字段（与 DDL 1:1）：
- id (UUID, PK)
- user_id (UUID, FK -> users.id)
- plan_id (UUID, FK -> plans.id, nullable)
- trigger (VARCHAR(32), NOT NULL) — 枚举 ``auto_day7 / auto_day14 / auto_day21 / user_manual``
- ai_summary (TEXT, nullable)
- ai_encourage (TEXT, nullable)
- referenced_feedbacks (JSONB, DEFAULT '[]') — 对象数组，存 {id, body_part, snippet, created_at}
- referenced_photos (JSONB, DEFAULT '[]') — 对象数组，存 {url, caption, created_at}
- llm_cost (DECIMAL(10,4), NOT NULL, DEFAULT 0)
- safety_passed (BOOLEAN, NOT NULL, DEFAULT FALSE) — Recall Safety 3 层防线命中结果
- ai_session_id (UUID, FK -> ai_sessions.id, nullable) — 延迟 FK
- audit: created_by / created_time / last_updated_time / last_updated_by

安全过滤：``docs/data/recall-forbidden-words.yaml`` 100+ 词（ADR-0017 §3.3）。
输出兜底：同 YAML ``safe_fallback_summary`` / ``safe_fallback_encourage``。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    BOOLEAN,
    DECIMAL,
    TIMESTAMP,
    VARCHAR,
    ForeignKey,
    Text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


class RecallSession(Base):
    """主动回忆业务事件（M8）。"""

    __tablename__ = "recall_sessions"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    trigger: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_encourage: Mapped[str | None] = mapped_column(Text, nullable=True)
    referenced_feedbacks: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    referenced_photos: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    llm_cost: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=10, scale=4), nullable=False, default=Decimal("0.0000")
    )
    safety_passed: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, default=False)
    ai_session_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("ai_sessions.id", ondelete="SET NULL"),
        nullable=True,
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
