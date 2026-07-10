"""User ORM（M1 主档）。

真源：``db/init/01-schema.sql`` §1.1 ``users`` + ``docs/data/data-dictionary.md`` §1。

字段清单（与 DDL 1:1）：
- id (UUID, PK)
- unionid (VARCHAR(128), UNIQUE, NOT NULL)
- openid_mp / openid_app (VARCHAR(128), nullable)
- phone (VARCHAR(20), nullable)
- platform (VARCHAR(20), NOT NULL) — 枚举 ``wx_mp / ios / android / harmony``
- device_id (VARCHAR(128), nullable, INDEX)
- nickname (VARCHAR(64), NOT NULL)
- avatar (VARCHAR(512), NOT NULL)
- age_range (VARCHAR(10), nullable) — 枚举见 data-dictionary §1.2
- sitting_hours (VARCHAR(10), nullable) — 枚举见 data-dictionary §1.2
- focus_parts (JSONB, nullable) — 多选枚举见 ``docs/data/body-parts.yaml``
- intensity (VARCHAR(10), nullable) — 枚举 ``轻柔 / 适中 / 进阶``
- preferred_time (VARCHAR(10), nullable) — 枚举 ``早 / 中 / 晚 / 不固定``
- skin_type (VARCHAR(10), nullable) — V5.2.1-PR2 T15 新增字段；枚举待 PR5 前端档案页落档后回填（默认 NULL）
- push_token (VARCHAR(512), nullable)
- push_channel (VARCHAR(20), nullable) — 枚举见 data-dictionary §1.2
- email (VARCHAR(254), nullable, RFC 5321)
- created_at / last_active_at (TIMESTAMPTZ, NOT NULL, DEFAULT NOW())
- report_cache (JSONB, nullable, DEFAULT '{}')
- report_cache_expires_at (TIMESTAMPTZ, nullable)
- version (INTEGER, NOT NULL, DEFAULT 0) — 乐观锁
- deleted_at (TIMESTAMPTZ, nullable) — 软删除
- audit: created_by / created_time / last_updated_time / last_updated_by
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import INTEGER, TIMESTAMP, VARCHAR
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.feedback import Feedback


class User(Base):
    """用户主档（M1）。

    字段命名 / 类型与 SQL DDL ``users`` 表 1:1。
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    unionid: Mapped[str] = mapped_column(VARCHAR(128), nullable=False, unique=True)
    openid_mp: Mapped[str | None] = mapped_column(VARCHAR(128), nullable=True)
    openid_app: Mapped[str | None] = mapped_column(VARCHAR(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(VARCHAR(20), nullable=True)
    platform: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    device_id: Mapped[str | None] = mapped_column(VARCHAR(128), nullable=True)
    nickname: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    avatar: Mapped[str] = mapped_column(VARCHAR(512), nullable=False)
    age_range: Mapped[str | None] = mapped_column(VARCHAR(10), nullable=True)
    sitting_hours: Mapped[str | None] = mapped_column(VARCHAR(10), nullable=True)
    focus_parts: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    intensity: Mapped[str | None] = mapped_column(VARCHAR(10), nullable=True)
    preferred_time: Mapped[str | None] = mapped_column(VARCHAR(10), nullable=True)
    # V5.2.1-PR2 T15：profile 6 字段含 skin_type，对应 users.skin_type 列
    skin_type: Mapped[str | None] = mapped_column(VARCHAR(10), nullable=True)
    push_token: Mapped[str | None] = mapped_column(VARCHAR(512), nullable=True)
    push_channel: Mapped[str | None] = mapped_column(VARCHAR(20), nullable=True)
    email: Mapped[str | None] = mapped_column(VARCHAR(254), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    # 用户生命周期：draft（草稿 24h 内）/ active（正式）/ churned（流失）
    status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default="draft")
    report_cache: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    report_cache_expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # 审计字段（与 DDL §V1.1.2 附录 E 一致）
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

    # relationships（与 Feedback ORM 配对）
    feedbacks: Mapped[list[Feedback]] = relationship(
        "Feedback", back_populates="user", lazy="raise"
    )
