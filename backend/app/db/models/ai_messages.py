"""AIMessage ORM（M5 会话内单条消息）。

真源：``db/init/01-schema.sql`` §1.11 ``ai_messages`` + ``docs/spec/SPEC-M5-persona-chat.md``。

字段（与 DDL 1:1）：
- id (UUID, PK)
- session_id (UUID, FK -> ai_sessions.id)
- seq (INTEGER, NOT NULL) — 会话内序号
- role (VARCHAR(16), NOT NULL) — 枚举 ``user / assistant / system``
- content (TEXT, NOT NULL)
- context_photos (JSONB, nullable)
- referenced_feedback_ids (UUID[], DEFAULT '{}') — PostgreSQL 原生数组
- referenced_video_ids (UUID[], DEFAULT '{}') — 同上
- trigger (VARCHAR(32), nullable) — 触发来源，如 ``P03a / P08 / cron``
- intent (VARCHAR(32), nullable)
- llm_cost (DECIMAL(10,4), nullable)
- llm_model (VARCHAR(64), nullable)
- llm_latency_ms (INTEGER, nullable)
- safety_passed (BOOLEAN, nullable)
- safety_violations (JSONB, nullable)
- token_count (INTEGER, NOT NULL, DEFAULT 0)
- audit: created_by / created_time / last_updated_time / last_updated_by
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BOOLEAN,
    CHAR,
    DECIMAL,
    INTEGER,
    TIMESTAMP,
    VARCHAR,
    ForeignKey,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


class AIMessage(Base):
    """AI 会话内单条消息（M5）。"""

    __tablename__ = "ai_messages"

    id: Mapped[UUID] = mapped_column(CHAR(36), primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        CHAR(36), ForeignKey("ai_sessions.id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(INTEGER, nullable=False)
    role: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    context_photos: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    referenced_feedback_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(CHAR(36)), nullable=False, default=list
    )
    referenced_video_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(CHAR(36)), nullable=False, default=list
    )
    trigger: Mapped[str | None] = mapped_column(VARCHAR(32), nullable=True)
    intent: Mapped[str | None] = mapped_column(VARCHAR(32), nullable=True)
    llm_cost: Mapped[Decimal | None] = mapped_column(DECIMAL(precision=10, scale=4), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    llm_latency_ms: Mapped[int | None] = mapped_column(INTEGER, nullable=True)
    safety_passed: Mapped[bool | None] = mapped_column(BOOLEAN, nullable=True)
    safety_violations: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    token_count: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    # 审计字段
    created_by: Mapped[str] = mapped_column(VARCHAR(64), nullable=False, default="")
    created_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    last_updated_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    last_updated_by: Mapped[str] = mapped_column(VARCHAR(64), nullable=False, default="")
