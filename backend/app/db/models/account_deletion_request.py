"""AccountDeletionRequest ORM（V2 IA · 账号注销 7 天冷静期）。

真源：``plans/v2-unified-parent.md`` §2.2 + IA V2.2 §2A.2.3
+ alembic 0007_add_v2_ia_tables。

GDPR 兼容：用户主动请求注销 → 7 天冷静期 → 用户再次确认 → 执行。

字段：
- id (UUID, PK)
- user_id (UUID, FK -> users.id, CASCADE)
- status (VARCHAR(16), NOT NULL) — 4 枚举：
    pending_cool_down / confirmed / cancelled / executed
- confirm_phrase (VARCHAR(64), NOT NULL) — 反向确认短语（用户必须手输避免误点）
- cool_down_until (TIMESTAMPTZ, NOT NULL) — 冷静期截止时间
- created_at / updated_at / deleted_at
- 审计字段
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import TIMESTAMP, VARCHAR, ForeignKey
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


# 4 状态枚举（IA V2.2 §2A.2.3 + alembic CHECK 约束）
DELETION_STATUSES: frozenset[str] = frozenset(
    {"pending_cool_down", "confirmed", "cancelled", "executed"}
)


class AccountDeletionRequest(Base):
    """账号注销请求（V2 IA · PR-2）。"""

    __tablename__ = "account_deletion_requests"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        VARCHAR(16), nullable=False, default="pending_cool_down"
    )
    confirm_phrase: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    cool_down_until: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
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
    last_updated_by: Mapped[str] = mapped_column(VARCHAR(64), nullable=False, default="")


__all__ = ["DELETION_STATUSES", "AccountDeletionRequest"]
