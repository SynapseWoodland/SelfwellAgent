"""Video ORM（M3 视频库主表）。

真源：``db/init/01-schema.sql`` §1.3 ``videos`` + ``docs/spec/facts-anchor.md`` §5
视频匹配算法权重（0.5*标签匹配度 + 0.3*时长适配度 + 0.2*难度适配度）。

字段（与 DDL 1:1）：
- id (UUID, PK)
- title (VARCHAR(256), NOT NULL)
- source (VARCHAR(20), NOT NULL) — 枚举见 ADR-0012 §内容来源
- video_id (VARCHAR(128), NOT NULL) — 第三方平台原 ID
- url (VARCHAR(1024), NOT NULL)
- duration_sec (INTEGER, NOT NULL)
- difficulty (INTEGER, NOT NULL) — 1-5，see §7xxx ``E_VIDEO_DIFFICULTY_INVALID``
- tags (JSONB, NOT NULL) — 标签集合
- thumbnail (VARCHAR(512), NOT NULL)
- status (VARCHAR(20), NOT NULL, DEFAULT 'active') — 枚举 ``active/inactive``
- audit: created_by / created_time / last_updated_time / last_updated_by
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import INTEGER, TIMESTAMP, VARCHAR
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


class Video(Base):
    """视频库主表（M3）。"""

    __tablename__ = "videos"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(VARCHAR(256), nullable=False)
    source: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    video_id: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    url: Mapped[str] = mapped_column(VARCHAR(1024), nullable=False)
    duration_sec: Mapped[int] = mapped_column(INTEGER, nullable=False)
    difficulty: Mapped[int] = mapped_column(INTEGER, nullable=False)
    tags: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    thumbnail: Mapped[str] = mapped_column(VARCHAR(512), nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
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
