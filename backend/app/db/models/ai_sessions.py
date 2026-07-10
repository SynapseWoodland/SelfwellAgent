"""AISession ORM（M5 智能管家会话生命周期）。

真源：``db/init/01-schema.sql`` §1.10 ``ai_sessions`` + ``docs/spec/SPEC-M5-persona-chat.md``。

字段（与 DDL 1:1）：
- id (UUID, PK)
- user_id (UUID, FK -> users.id)
- entry_card (VARCHAR(32), nullable) — 入口卡 id，见 ``docs/spec/SPEC-M5``
- primary_intent (VARCHAR(32), NOT NULL)
- persona_state_start (VARCHAR(32), NOT NULL, DEFAULT 'warm')
- persona_state_end (VARCHAR(32), nullable)
- plan_id (UUID, FK -> plans.id, nullable)
- feedback_id / recall_session_id (UUID, FK, nullable) — 延迟 FK
- message_count (INTEGER, NOT NULL, DEFAULT 0)
- total_llm_cost (DECIMAL(10,4), NOT NULL, DEFAULT 0)
- user_active (BOOLEAN, NOT NULL, DEFAULT TRUE)
- assistant_profile (JSONB, nullable) — smart_analyze directions/tags/summary，追问 chat 注入
- started_at / last_active_at / closed_at (TIMESTAMPTZ)
- audit: created_by / created_time / last_updated_time / last_updated_by

Persona 4 态枚举：``warm / neutral / slight_hug / medical_guarded``（facts-anchor §4 / ADR-0015）
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BOOLEAN,
    DECIMAL,
    INTEGER,
    TIMESTAMP,
    VARCHAR,
    ForeignKey,
)
from sqlalchemy.dialects import postgresql

# JSONB 是 PostgreSQL dialect 类型，通过 dialect 导入
assistant_profile_type = postgresql.JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


class AISession(Base):
    """智能管家会话生命周期（M5）。"""

    __tablename__ = "ai_sessions"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    entry_card: Mapped[str | None] = mapped_column(VARCHAR(32), nullable=True)
    primary_intent: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    persona_state_start: Mapped[str] = mapped_column(
        VARCHAR(32), nullable=False, default="warm"
    )
    persona_state_end: Mapped[str | None] = mapped_column(VARCHAR(32), nullable=True)
    plan_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    feedback_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("feedback.id", ondelete="SET NULL"),
        nullable=True,
    )
    recall_session_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("recall_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    message_count: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    total_llm_cost: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=10, scale=4), nullable=False, default=Decimal("0.0000")
    )
    user_active: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, default=True)
    # PR-F.1 Step 1.4：存储 smart_analyze 生成的 directions/tags/summary，
    # 供后续追问 chat 注入 system prompt 使用。
    assistant_profile: Mapped[dict | None] = mapped_column(assistant_profile_type, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
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
