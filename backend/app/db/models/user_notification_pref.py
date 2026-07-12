"""UserNotificationPref ORM（V2 IA · 通知偏好 key→value map）。

真源：``plans/v2-unified-parent.md`` §2.2 + IA V2.2 §2A.2.2
+ alembic 0007_add_v2_ia_tables。

复合主键 (user_id, pref_key)。
枚举 pref_key：
- daily_checkin / weekly_recall / feedback_ack
- plan_milestone / album_unlock / hug_card_ready

字段：
- user_id (UUID, FK -> users.id, CASCADE) — PK 部分
- pref_key (VARCHAR(64), NOT NULL) — PK 部分
- pref_value (JSONB, NOT NULL) — 形如 {"enabled": true, "time": "08:00"}
- updated_at (TIMESTAMPTZ, NOT NULL)
- 审计字段
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import TIMESTAMP, VARCHAR, ForeignKey
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


# 通知偏好 key 枚举（IA V2.2 §2A.2.2）
PREF_KEYS: frozenset[str] = frozenset(
    {
        "daily_checkin",
        "weekly_recall",
        "feedback_ack",
        "plan_milestone",
        "album_unlock",
        "hug_card_ready",
    }
)


class UserNotificationPref(Base):
    """用户通知偏好（V2 IA · PR-2）。"""

    __tablename__ = "user_notification_prefs"

    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    pref_key: Mapped[str] = mapped_column(VARCHAR(64), primary_key=True)
    pref_value: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
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
    last_updated_by: Mapped[str] = mapped_column(VARCHAR(64), nullable=False, default="")


__all__ = ["PREF_KEYS", "UserNotificationPref"]
