"""Initial V1.3 locked schema · Sprint 0 迁移。

依据：``db/init/01-schema.sql``（11 张业务表全量 DDL）。

约定：
- 本迁移**只用于 alembic 版本控制起点**，并不替代 ``db/init/01-schema.sql``。
  生产部署仍走 ``db/init/*.sql``（docker-entrypoint-initdb.d）。
- alembic 与 SQL DDL 必须 1:1（hash diff 应为 0）。
- 未来 V1.3+ 增量字段（如 v1.4 新增字段）只能走 alembic 增量迁移；禁止再改 SQL。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by alembic.
revision: str = "0001_initial_v13_locked"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ═══════════════════════════════════════════════════════════════════════
    # §1 uuid-ossp 扩展（PG 15 需要；PG 18 内置 uuidv7）
    # ═══════════════════════════════════════════════════════════════════════
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # ═══════════════════════════════════════════════════════════════════════
    # §2 users（M1 主档）
    # ═══════════════════════════════════════════════════════════════════════
    op.create_table(
        "users",
        sa.Column("id", sa.CHAR(36), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("unionid", sa.VARCHAR(128), nullable=False, unique=True),
        sa.Column("openid_mp", sa.VARCHAR(128), nullable=True),
        sa.Column("openid_app", sa.VARCHAR(128), nullable=True),
        sa.Column("phone", sa.VARCHAR(20), nullable=True),
        sa.Column("platform", sa.VARCHAR(20), nullable=False),
        sa.Column("device_id", sa.VARCHAR(128), nullable=True),
        sa.Column("nickname", sa.VARCHAR(64), nullable=False),
        sa.Column("avatar", sa.VARCHAR(512), nullable=False),
        sa.Column("age_range", sa.VARCHAR(10), nullable=True),
        sa.Column("sitting_hours", sa.VARCHAR(10), nullable=True),
        sa.Column("focus_parts", postgresql.JSONB, nullable=True),
        sa.Column("intensity", sa.VARCHAR(10), nullable=True),
        sa.Column("preferred_time", sa.VARCHAR(10), nullable=True),
        sa.Column("push_token", sa.VARCHAR(512), nullable=True),
        sa.Column("push_channel", sa.VARCHAR(20), nullable=True),
        sa.Column("email", sa.VARCHAR(254), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_active_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "report_cache",
            postgresql.JSONB,
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("report_cache_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("version", sa.INTEGER, nullable=False, server_default=sa.text("0")),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.VARCHAR(64), nullable=False, server_default=""),
        sa.Column(
            "created_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_updated_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_updated_by", sa.VARCHAR(64), nullable=False, server_default=""),
    )

    # ═══════════════════════════════════════════════════════════════════════
    # §3 reports（M2 AI 诊断报告）
    # ═══════════════════════════════════════════════════════════════════════
    op.create_table(
        "reports",
        sa.Column("id", sa.CHAR(36), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column(
            "user_id",
            sa.CHAR(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("photos", postgresql.JSONB, nullable=False),
        sa.Column("directions", postgresql.JSONB, nullable=False),
        sa.Column("tags", postgresql.JSONB, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("llm_model", sa.VARCHAR(50), nullable=True),
        sa.Column(
            "llm_cost",
            sa.DECIMAL(precision=10, scale=4),
            nullable=False,
            server_default=sa.text("0.0000"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.VARCHAR(64), nullable=False, server_default=""),
        sa.Column(
            "created_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_updated_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_updated_by", sa.VARCHAR(64), nullable=False, server_default=""),
    )

    # ═══════════════════════════════════════════════════════════════════════
    # §4 videos（M3 视频库）
    # ═══════════════════════════════════════════════════════════════════════
    op.create_table(
        "videos",
        sa.Column("id", sa.CHAR(36), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("title", sa.VARCHAR(256), nullable=False),
        sa.Column("source", sa.VARCHAR(20), nullable=False),
        sa.Column("video_id", sa.VARCHAR(128), nullable=False),
        sa.Column("url", sa.VARCHAR(1024), nullable=False),
        sa.Column("duration_sec", sa.INTEGER, nullable=False),
        sa.Column("difficulty", sa.INTEGER, nullable=False),
        sa.Column("tags", postgresql.JSONB, nullable=False),
        sa.Column("thumbnail", sa.VARCHAR(512), nullable=False),
        sa.Column("status", sa.VARCHAR(20), nullable=False, server_default=sa.text("'active'")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.VARCHAR(64), nullable=False, server_default=""),
        sa.Column(
            "created_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_updated_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_updated_by", sa.VARCHAR(64), nullable=False, server_default=""),
    )

    # ═══════════════════════════════════════════════════════════════════════
    # §5 plans（M3 21 天方案）
    # ═══════════════════════════════════════════════════════════════════════
    op.create_table(
        "plans",
        sa.Column("id", sa.CHAR(36), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column(
            "user_id",
            sa.CHAR(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("report_id", sa.VARCHAR(64), nullable=False),
        sa.Column("days", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.VARCHAR(20), nullable=False, server_default=sa.text("'active'")),
        sa.Column("started_at", sa.DATE, nullable=True),
        sa.Column("completed_at", sa.DATE, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.VARCHAR(64), nullable=False, server_default=""),
        sa.Column(
            "created_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_updated_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_updated_by", sa.VARCHAR(64), nullable=False, server_default=""),
    )

    # ═══════════════════════════════════════════════════════════════════════
    # §6 checkins（M4 每日打卡）
    # ═══════════════════════════════════════════════════════════════════════
    op.create_table(
        "checkins",
        sa.Column("id", sa.CHAR(36), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column(
            "user_id",
            sa.CHAR(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan_id", sa.VARCHAR(64), nullable=False),
        sa.Column("day", sa.INTEGER, nullable=False),
        sa.Column("video_id", sa.VARCHAR(64), nullable=False),
        sa.Column("feeling", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.VARCHAR(64), nullable=False, server_default=""),
        sa.Column(
            "created_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_updated_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_updated_by", sa.VARCHAR(64), nullable=False, server_default=""),
    )

    # ═══════════════════════════════════════════════════════════════════════
    # §7 posts（M6 社区动态）
    # ═══════════════════════════════════════════════════════════════════════
    op.create_table(
        "posts",
        sa.Column("id", sa.CHAR(36), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column(
            "user_id",
            sa.CHAR(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("images", postgresql.JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "status",
            sa.VARCHAR(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("ai_comment", sa.Text, nullable=True),
        sa.Column("official_comment", sa.Text, nullable=True),
        sa.Column("like_count", sa.INTEGER, nullable=False, server_default=sa.text("0")),
        sa.Column("comment_count", sa.INTEGER, nullable=False, server_default=sa.text("0")),
        sa.Column(
            "reviewed_by",
            sa.CHAR(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.VARCHAR(64), nullable=False, server_default=""),
        sa.Column(
            "created_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_updated_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_updated_by", sa.VARCHAR(64), nullable=False, server_default=""),
    )

    # ═══════════════════════════════════════════════════════════════════════
    # §8 feedback（M7 · V1.3 新增） + recall_sessions（M8）+ ai_sessions（M5）+
    #   ai_messages（M5） —— 按 SQL §1.8 ~ §1.11 + §末尾 ALTER TABLE 顺序
    # ═══════════════════════════════════════════════════════════════════════
    op.create_table(
        "feedback",
        sa.Column("id", sa.CHAR(36), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column(
            "user_id",
            sa.CHAR(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("feedback_type", sa.VARCHAR(32), nullable=False),
        sa.Column("text_content", sa.Text, nullable=True),
        sa.Column("photo_url", sa.VARCHAR(512), nullable=True),
        sa.Column("body_part", sa.VARCHAR(32), nullable=True),
        sa.Column("ai_ack_id", sa.CHAR(36), nullable=True),  # 延迟 FK
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("created_by", sa.VARCHAR(64), nullable=False, server_default=""),
        sa.Column(
            "created_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_updated_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_updated_by", sa.VARCHAR(64), nullable=False, server_default=""),
    )

    op.create_table(
        "recall_sessions",
        sa.Column("id", sa.CHAR(36), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column(
            "user_id",
            sa.CHAR(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            sa.CHAR(36),
            sa.ForeignKey("plans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("trigger", sa.VARCHAR(32), nullable=False),
        sa.Column("ai_summary", sa.Text, nullable=True),
        sa.Column("ai_encourage", sa.Text, nullable=True),
        sa.Column(
            "referenced_feedbacks",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "referenced_photos",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "llm_cost",
            sa.DECIMAL(precision=10, scale=4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "safety_passed",
            sa.BOOLEAN,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column("ai_session_id", sa.CHAR(36), nullable=True),  # 延迟 FK
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.VARCHAR(64), nullable=False, server_default=""),
        sa.Column(
            "created_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_updated_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_updated_by", sa.VARCHAR(64), nullable=False, server_default=""),
    )

    op.create_table(
        "ai_sessions",
        sa.Column("id", sa.CHAR(36), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column(
            "user_id",
            sa.CHAR(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entry_card", sa.VARCHAR(32), nullable=True),
        sa.Column("primary_intent", sa.VARCHAR(32), nullable=False),
        sa.Column(
            "persona_state_start",
            sa.VARCHAR(32),
            nullable=False,
            server_default=sa.text("'warm'"),
        ),
        sa.Column("persona_state_end", sa.VARCHAR(32), nullable=True),
        sa.Column(
            "plan_id",
            sa.CHAR(36),
            sa.ForeignKey("plans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("feedback_id", sa.CHAR(36), nullable=True),  # 延迟 FK
        sa.Column("recall_session_id", sa.CHAR(36), nullable=True),  # 延迟 FK
        sa.Column(
            "message_count",
            sa.INTEGER,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_llm_cost",
            sa.DECIMAL(precision=10, scale=4),
            nullable=False,
            server_default=sa.text("0.0000"),
        ),
        sa.Column("user_active", sa.BOOLEAN, nullable=False, server_default=sa.text("TRUE")),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_active_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("created_by", sa.VARCHAR(64), nullable=False, server_default=""),
        sa.Column(
            "created_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_updated_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_updated_by", sa.VARCHAR(64), nullable=False, server_default=""),
    )

    op.create_table(
        "ai_messages",
        sa.Column("id", sa.CHAR(36), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column(
            "session_id",
            sa.CHAR(36),
            sa.ForeignKey("ai_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.INTEGER, nullable=False),
        sa.Column("role", sa.VARCHAR(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("context_photos", postgresql.JSONB, nullable=True),
        sa.Column(
            "referenced_feedback_ids",
            postgresql.ARRAY(sa.CHAR(36)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "referenced_video_ids",
            postgresql.ARRAY(sa.CHAR(36)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("trigger", sa.VARCHAR(32), nullable=True),
        sa.Column("intent", sa.VARCHAR(32), nullable=True),
        sa.Column("llm_cost", sa.DECIMAL(precision=10, scale=4), nullable=True),
        sa.Column("llm_model", sa.VARCHAR(64), nullable=True),
        sa.Column("llm_latency_ms", sa.INTEGER, nullable=True),
        sa.Column("safety_passed", sa.BOOLEAN, nullable=True),
        sa.Column("safety_violations", postgresql.JSONB, nullable=True),
        sa.Column("token_count", sa.INTEGER, nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("created_by", sa.VARCHAR(64), nullable=False, server_default=""),
        sa.Column(
            "created_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_updated_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_updated_by", sa.VARCHAR(64), nullable=False, server_default=""),
    )

    # ═══════════════════════════════════════════════════════════════════════
    # §9 补回延迟 FK（feedback / recall_sessions / ai_sessions 三处的延迟 FK）
    # ═══════════════════════════════════════════════════════════════════════
    op.create_foreign_key(
        "fk_feedback_ai_ack",
        "feedback",
        "ai_messages",
        ["ai_ack_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_recall_ai_session",
        "recall_sessions",
        "ai_sessions",
        ["ai_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_ai_session_feedback",
        "ai_sessions",
        "feedback",
        ["feedback_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_ai_session_recall",
        "ai_sessions",
        "recall_sessions",
        ["recall_session_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # 按 §逆向顺序 drop（FK 反向 + 表）
    op.drop_constraint("fk_ai_session_recall", "ai_sessions", type_="foreignkey")
    op.drop_constraint("fk_ai_session_feedback", "ai_sessions", type_="foreignkey")
    op.drop_constraint("fk_recall_ai_session", "recall_sessions", type_="foreignkey")
    op.drop_constraint("fk_feedback_ai_ack", "feedback", type_="foreignkey")
    op.drop_table("ai_messages")
    op.drop_table("ai_sessions")
    op.drop_table("recall_sessions")
    op.drop_table("feedback")
    op.drop_table("posts")
    op.drop_table("checkins")
    op.drop_table("plans")
    op.drop_table("videos")
    op.drop_table("reports")
    op.drop_table("users")
