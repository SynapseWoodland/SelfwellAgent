"""Add ``assistant_profile`` JSONB column to ``ai_sessions``.

真源：Sprint 2026-07-09 M5 智能管家扩展
- 新增 ``ai_sessions.assistant_profile`` JSONB 字段（nullable，默认 NULL）。
- 存储 AI 管家侧的角色/配置信息（persona、greeting、capabilities 等）。
- 添加 CHECK 约束 ``ck_ai_sessions_assistant_profile_type`` 确保值为 JSON object。

幂等：PostgreSQL ``ADD COLUMN`` 不支持 ``IF NOT EXISTS``；alembic 版本表会阻止
二次执行，本迁移默认一次性。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by alembic.
revision: str = "0005_add_assistant_profile_to_ai_sessions"
down_revision: str | None = "0004_report_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """加 ``ai_sessions.assistant_profile`` JSONB 列（nullable，默认 NULL）。

    同时添加 CHECK 约束：``assistant_profile`` 必须是 JSON object（``jsonb_typeof
    = 'object'``）或 NULL。
    """
    op.add_column(
        "ai_sessions",
        sa.Column("assistant_profile", postgresql.JSONB, nullable=True),
    )
    op.create_check_constraint(
        "ck_ai_sessions_assistant_profile_type",
        "ai_sessions",
        sa.text(
            "assistant_profile IS NULL OR jsonb_typeof(assistant_profile) = 'object'"
        ),
    )


def downgrade() -> None:
    """回滚：删 ``assistant_profile`` 列及其 CHECK 约束。"""
    op.drop_constraint(
        "ck_ai_sessions_assistant_profile_type",
        "ai_sessions",
        type_="check",
    )
    op.drop_column("ai_sessions", "assistant_profile")


__all__: list[str] = ["down_revision", "downgrade", "revision", "upgrade"]
