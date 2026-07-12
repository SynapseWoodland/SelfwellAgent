"""Add V2 IA tables: user_badges / user_notification_prefs / account_deletion_requests / user_self_tags.

PR-2 of the V2 unified 8-PR plan (per ``plans/v2-unified-parent.md`` §2.2 + IA V2.2 §2A.2).
Four new tables supporting:

- ``user_badges``: 勋章体系（V2 新增 ~6 类：first_checkin / streak_7 / streak_14 / streak_21 /
  first_feedback / first_album_photo），PK (user_id, code)
- ``user_notification_prefs``: 通知偏好（key→value JSONB map），PK (user_id, pref_key)
- ``account_deletion_requests``: 账号注销请求（7 天冷静期，状态机
  pending_cool_down / confirmed / cancelled / executed），与 GDPR 兼容
- ``user_self_tags``: 自标签（body_part / concern / lifestyle / intensity），来源 manual /
  inferred_from_feedback，唯一约束 (user_id, tag_category, tag_value)

幂等：依赖 alembic 版本表，单次执行。

字段类型 / 约束：
- 主键用 CHAR(36) + server_default ``uuidv7()``（与 0001 一致；PG 15+ 需要 uuid-ossp 扩展）
- 审计字段 created_by / created_time / last_updated_time / last_updated_by 与 0001 §1 对齐
- 软删除字段 deleted_at（与 0001 §1 一致）
- NOT NULL 字段均为业务必填；NULL 字段允许软迁移期回填
- FK → users(id) ON DELETE CASCADE（与现有 users FK 一致）

向下兼容：
- 新增表，不修改任何已有表 schema
- downgrade() 严格按反向顺序 drop
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by alembic.
revision: str = "0007_add_v2_ia_tables"
down_revision: str | None = "0006_add_skin_type_to_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create 4 V2 IA tables."""

    # ════════════════════════════════════════════════════════════════════════
    # §1 user_badges · 勋章体系
    # ════════════════════════════════════════════════════════════════════════
    op.create_table(
        "user_badges",
        sa.Column("id", sa.CHAR(36), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column(
            "user_id",
            sa.CHAR(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # 6 类枚举：first_checkin / streak_7 / streak_14 / streak_21 /
        # first_feedback / first_album_photo
        sa.Column("code", sa.VARCHAR(64), nullable=False),
        sa.Column("progress", sa.INTEGER, nullable=False, server_default=sa.text("0")),
        sa.Column("target", sa.INTEGER, nullable=False, server_default=sa.text("0")),
        sa.Column("unlocked_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        # 业务唯一约束：(user_id, code) 一人一码一行（IA V2.2 §2A.2.1）
        sa.UniqueConstraint("user_id", "code", name="uq_user_badges_user_code"),
    )
    op.create_index("ix_user_badges_user_id", "user_badges", ["user_id"])
    op.create_index("ix_user_badges_code", "user_badges", ["code"])

    # ════════════════════════════════════════════════════════════════════════
    # §2 user_notification_prefs · 通知偏好（key→value JSONB map）
    # ════════════════════════════════════════════════════════════════════════
    op.create_table(
        "user_notification_prefs",
        sa.Column(
            "user_id",
            sa.CHAR(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # pref_key 枚举：daily_checkin / weekly_recall / feedback_ack / plan_milestone /
        # album_unlock / hug_card_ready
        sa.Column("pref_key", sa.VARCHAR(64), nullable=False),
        # 值形如 {"enabled": true, "time": "08:00"} —— 全 JSONB 由调用方控制
        sa.Column("pref_value", postgresql.JSONB, nullable=False),
        sa.Column(
            "updated_at",
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
        # 复合主键：(user_id, pref_key) 一人一个偏好 key 只存一行
        sa.PrimaryKeyConstraint("user_id", "pref_key", name="pk_user_notification_prefs"),
    )
    op.create_index(
        "ix_user_notification_prefs_user_id",
        "user_notification_prefs",
        ["user_id"],
    )

    # ════════════════════════════════════════════════════════════════════════
    # §3 account_deletion_requests · 账号注销请求（7 天冷静期）
    # ════════════════════════════════════════════════════════════════════════
    op.create_table(
        "account_deletion_requests",
        sa.Column("id", sa.CHAR(36), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column(
            "user_id",
            sa.CHAR(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # 4 状态：pending_cool_down / confirmed / cancelled / executed
        sa.Column("status", sa.VARCHAR(16), nullable=False, server_default=sa.text("'pending_cool_down'")),
        # 反向确认短语（用户必须手输），避免误点
        sa.Column("confirm_phrase", sa.VARCHAR(64), nullable=False),
        # 冷静期截止时间（V2 默认 7 天；PR-2 hardcode，PR-5 前端允许用户提前 cancel）
        sa.Column("cool_down_until", sa.TIMESTAMP(timezone=True), nullable=False),
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
        sa.CheckConstraint(
            "status IN ('pending_cool_down', 'confirmed', 'cancelled', 'executed')",
            name="ck_account_deletion_status",
        ),
    )
    op.create_index(
        "ix_account_deletion_user_id",
        "account_deletion_requests",
        ["user_id"],
    )
    op.create_index(
        "ix_account_deletion_status",
        "account_deletion_requests",
        ["status"],
    )

    # ════════════════════════════════════════════════════════════════════════
    # §4 user_self_tags · 自标签（profile / concern / lifestyle / intensity）
    # ════════════════════════════════════════════════════════════════════════
    op.create_table(
        "user_self_tags",
        sa.Column("id", sa.CHAR(36), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column(
            "user_id",
            sa.CHAR(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # 4 类：body_part / concern / lifestyle / intensity
        sa.Column("tag_category", sa.VARCHAR(32), nullable=False),
        sa.Column("tag_value", sa.VARCHAR(64), nullable=False),
        sa.Column(
            "is_selected",
            sa.BOOLEAN,
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        # 来源：manual（用户主动加）/ inferred_from_feedback（AI 从反馈推断）
        sa.Column(
            "source",
            sa.VARCHAR(16),
            nullable=False,
            server_default=sa.text("'manual'"),
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
        # 唯一约束：一人一类一标签一行（IA V2.2 §2A.2.4）
        sa.UniqueConstraint(
            "user_id",
            "tag_category",
            "tag_value",
            name="uq_user_self_tags_user_category_value",
        ),
        sa.CheckConstraint(
            "tag_category IN ('body_part', 'concern', 'lifestyle', 'intensity')",
            name="ck_user_self_tags_category",
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'inferred_from_feedback')",
            name="ck_user_self_tags_source",
        ),
    )
    op.create_index("ix_user_self_tags_user_id", "user_self_tags", ["user_id"])
    op.create_index(
        "ix_user_self_tags_user_selected",
        "user_self_tags",
        ["user_id", "is_selected"],
    )


def downgrade() -> None:
    """Drop 4 V2 IA tables（严格反向顺序，与 upgrade 顺序相反）。"""
    op.drop_index("ix_user_self_tags_user_selected", table_name="user_self_tags")
    op.drop_index("ix_user_self_tags_user_id", table_name="user_self_tags")
    op.drop_table("user_self_tags")

    op.drop_index("ix_account_deletion_status", table_name="account_deletion_requests")
    op.drop_index("ix_account_deletion_user_id", table_name="account_deletion_requests")
    op.drop_table("account_deletion_requests")

    op.drop_index(
        "ix_user_notification_prefs_user_id",
        table_name="user_notification_prefs",
    )
    op.drop_table("user_notification_prefs")

    op.drop_index("ix_user_badges_code", table_name="user_badges")
    op.drop_index("ix_user_badges_user_id", table_name="user_badges")
    op.drop_table("user_badges")


__all__: list[str] = ["down_revision", "downgrade", "revision", "upgrade"]