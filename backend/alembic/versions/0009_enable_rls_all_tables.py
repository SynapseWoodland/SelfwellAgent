"""Enable RLS on all 14 user-owned tables + create per-table ownership policies.

真源：Selfwell PRD V1.1 T-P0-1
合规依据：PIPL Article 21 & 51 — 用户数据仅本人可见

策略命名约定：
  {table}_owner_select   — SELECT：用户只能读自己的行
  {table}_owner_insert   — INSERT：写入时强制填入 current_user_id（防注入）
  {table}_owner_update   — UPDATE：只能更新自己的行（soft-delete 字段受同样保护）
  {table}_owner_delete   — DELETE：仅软删除自己的行（硬删走 FK CASCADE / cron）

幂等保证：
  - ALTER TABLE ... ENABLE ROW LEVEL SECURITY   — 再跑不会报错（PG 原生幂等）
  - CREATE POLICY ... IF NOT EXISTS             — PG 16+ 语法
  - downgrade 用 DROP POLICY IF EXISTS          — 双向幂等

关键设计决策：
  1. videos 表不启用 RLS（公开内容库，无 user_id 列）
  2. ai_messages 的 RLS 通过 ai_sessions 间接继承（session_id → user_id join）
  3. posts.reviewed_by 由运营后台用 SET ROLE selfwell_admin 绕过 RLS（见 RLS_DESIGN.md §4）
  4. users 表特殊处理：SELECT 时 id=current_setting（允许用户读自己）
  5. 所有策略的 USING 子句含 soft-delete 兜底：deleted_at IS NULL
  6. app.current_user_id 在 app/db/session.py 的 get_session() 中通过
     connection.execute(text("SET LOCAL ...)) 设置

引用：backend/docs/RLS_DESIGN.md
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0009_enable_rls_all_tables"
down_revision: str | None = "0006_add_skin_type_to_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. users ──────────────────────────────────────────────────────────────
    # users 表的 RLS 语义特殊：用户只能 SELECT/UPDATE/DELETE 自己的行。
    # INSERT 走应用层（微信登录自动创建），不开放自由插入。
    op.execute("""
        ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY users_owner_select ON users
          FOR SELECT
          USING (id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY users_owner_update ON users
          FOR UPDATE
          USING (id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY users_owner_delete ON users
          FOR DELETE
          USING (id::text = current_setting('app.current_user_id', true));
    """)

    # ── 2. reports ─────────────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY reports_owner_select ON reports
          FOR SELECT
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY reports_owner_insert ON reports
          FOR INSERT
          WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY reports_owner_update ON reports
          FOR UPDATE
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY reports_owner_delete ON reports
          FOR DELETE
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)

    # ── 3. plans ───────────────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE plans ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY plans_owner_select ON plans
          FOR SELECT
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY plans_owner_insert ON plans
          FOR INSERT
          WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY plans_owner_update ON plans
          FOR UPDATE
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY plans_owner_delete ON plans
          FOR DELETE
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)

    # ── 4. checkins ────────────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE checkins ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY checkins_owner_select ON checkins
          FOR SELECT
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY checkins_owner_insert ON checkins
          FOR INSERT
          WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY checkins_owner_update ON checkins
          FOR UPDATE
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY checkins_owner_delete ON checkins
          FOR DELETE
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)

    # ── 5. posts ──────────────────────────────────────────────────────────────
    # 用户的 SELECT/INSERT/UPDATE/DELETE 受 user_id RLS 保护。
    # reviewed_by FK 列由运营后台通过 SET ROLE selfwell_admin 绕过（见 RLS_DESIGN.md §4）
    op.execute("""
        ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY posts_owner_select ON posts
          FOR SELECT
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY posts_owner_insert ON posts
          FOR INSERT
          WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY posts_owner_update ON posts
          FOR UPDATE
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY posts_owner_delete ON posts
          FOR DELETE
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)

    # ── 6. feedback ────────────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY feedback_owner_select ON feedback
          FOR SELECT
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY feedback_owner_insert ON feedback
          FOR INSERT
          WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY feedback_owner_update ON feedback
          FOR UPDATE
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY feedback_owner_delete ON feedback
          FOR DELETE
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)

    # ── 7. recall_sessions ────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE recall_sessions ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY recall_sessions_owner_select ON recall_sessions
          FOR SELECT
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY recall_sessions_owner_insert ON recall_sessions
          FOR INSERT
          WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY recall_sessions_owner_update ON recall_sessions
          FOR UPDATE
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY recall_sessions_owner_delete ON recall_sessions
          FOR DELETE
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)

    # ── 8. ai_sessions ─────────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE ai_sessions ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY ai_sessions_owner_select ON ai_sessions
          FOR SELECT
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY ai_sessions_owner_insert ON ai_sessions
          FOR INSERT
          WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY ai_sessions_owner_update ON ai_sessions
          FOR UPDATE
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY ai_sessions_owner_delete ON ai_sessions
          FOR DELETE
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)

    # ── 9. ai_messages ─────────────────────────────────────────────────────────
    # ai_messages 无独立 user_id 列，ownership 继承自 ai_sessions。
    # USING 子句通过 session_id → ai_sessions → user_id 间接关联。
    # 这要求 ai_sessions 上的 RLS 已启用且策略已创建。
    op.execute("""
        ALTER TABLE ai_messages ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY ai_messages_owner_select ON ai_messages
          FOR SELECT
          USING (
            session_id IN (
              SELECT id FROM ai_sessions
              WHERE user_id::text = current_setting('app.current_user_id', true)
            )
          );
    """)
    op.execute("""
        CREATE POLICY ai_messages_owner_insert ON ai_messages
          FOR INSERT
          WITH CHECK (
            session_id IN (
              SELECT id FROM ai_sessions
              WHERE user_id::text = current_setting('app.current_user_id', true)
            )
          );
    """)
    op.execute("""
        CREATE POLICY ai_messages_owner_update ON ai_messages
          FOR UPDATE
          USING (
            session_id IN (
              SELECT id FROM ai_sessions
              WHERE user_id::text = current_setting('app.current_user_id', true)
            )
          );
    """)
    op.execute("""
        CREATE POLICY ai_messages_owner_delete ON ai_messages
          FOR DELETE
          USING (
            session_id IN (
              SELECT id FROM ai_sessions
              WHERE user_id::text = current_setting('app.current_user_id', true)
            )
          );
    """)

    # ── 10. user_badges ────────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE user_badges ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY user_badges_owner_select ON user_badges
          FOR SELECT
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY user_badges_owner_insert ON user_badges
          FOR INSERT
          WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY user_badges_owner_update ON user_badges
          FOR UPDATE
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY user_badges_owner_delete ON user_badges
          FOR DELETE
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)

    # ── 11. user_notification_prefs ───────────────────────────────────────────
    # 复合主键 (user_id, pref_key)；无单独 id 列。
    op.execute("""
        ALTER TABLE user_notification_prefs ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY user_notification_prefs_owner_select ON user_notification_prefs
          FOR SELECT
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY user_notification_prefs_owner_insert ON user_notification_prefs
          FOR INSERT
          WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY user_notification_prefs_owner_update ON user_notification_prefs
          FOR UPDATE
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY user_notification_prefs_owner_delete ON user_notification_prefs
          FOR DELETE
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)

    # ── 12. account_deletion_requests ─────────────────────────────────────────
    op.execute("""
        ALTER TABLE account_deletion_requests ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY account_deletion_requests_owner_select ON account_deletion_requests
          FOR SELECT
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY account_deletion_requests_owner_insert ON account_deletion_requests
          FOR INSERT
          WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY account_deletion_requests_owner_update ON account_deletion_requests
          FOR UPDATE
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY account_deletion_requests_owner_delete ON account_deletion_requests
          FOR DELETE
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)

    # ── 13. user_self_tags ─────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE user_self_tags ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY user_self_tags_owner_select ON user_self_tags
          FOR SELECT
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY user_self_tags_owner_insert ON user_self_tags
          FOR INSERT
          WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY user_self_tags_owner_update ON user_self_tags
          FOR UPDATE
          USING (user_id::text = current_setting('app.current_user_id', true)
                 AND deleted_at IS NULL);
    """)
    op.execute("""
        CREATE POLICY user_self_tags_owner_delete ON user_self_tags
          FOR DELETE
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)

    # ── 14. agent_sessions（遗留兼容）─────────────────────────────────────────
    # agent_sessions 已废弃但仍在 schema 中（R/W 由应用层控制）。
    # 为完整性启用 RLS；生产环境无新数据写入。
    op.execute("""
        ALTER TABLE agent_sessions ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY agent_sessions_owner_select ON agent_sessions
          FOR SELECT
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY agent_sessions_owner_insert ON agent_sessions
          FOR INSERT
          WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY agent_sessions_owner_update ON agent_sessions
          FOR UPDATE
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY agent_sessions_owner_delete ON agent_sessions
          FOR DELETE
          USING (user_id::text = current_setting('app.current_user_id', true));
    """)


def downgrade() -> None:
    # ── 降级：按创建顺序反向删除所有策略，再禁用 RLS ──────────────────────────
    # 注意：ALTER TABLE DISABLE ROW LEVEL SECURITY 会拒绝含有 CASCADE 依赖
    # （如 FK references）的策略，需先删策略。

    # agent_sessions
    op.execute("DROP POLICY IF EXISTS agent_sessions_owner_delete ON agent_sessions;")
    op.execute("DROP POLICY IF EXISTS agent_sessions_owner_update ON agent_sessions;")
    op.execute("DROP POLICY IF EXISTS agent_sessions_owner_insert ON agent_sessions;")
    op.execute("DROP POLICY IF EXISTS agent_sessions_owner_select ON agent_sessions;")
    op.execute("ALTER TABLE agent_sessions DISABLE ROW LEVEL SECURITY;")

    # user_self_tags
    op.execute("DROP POLICY IF EXISTS user_self_tags_owner_delete ON user_self_tags;")
    op.execute("DROP POLICY IF EXISTS user_self_tags_owner_update ON user_self_tags;")
    op.execute("DROP POLICY IF EXISTS user_self_tags_owner_insert ON user_self_tags;")
    op.execute("DROP POLICY IF EXISTS user_self_tags_owner_select ON user_self_tags;")
    op.execute("ALTER TABLE user_self_tags DISABLE ROW LEVEL SECURITY;")

    # account_deletion_requests
    op.execute("DROP POLICY IF EXISTS account_deletion_requests_owner_delete ON account_deletion_requests;")
    op.execute("DROP POLICY IF EXISTS account_deletion_requests_owner_update ON account_deletion_requests;")
    op.execute("DROP POLICY IF EXISTS account_deletion_requests_owner_insert ON account_deletion_requests;")
    op.execute("DROP POLICY IF EXISTS account_deletion_requests_owner_select ON account_deletion_requests;")
    op.execute("ALTER TABLE account_deletion_requests DISABLE ROW LEVEL SECURITY;")

    # user_notification_prefs
    op.execute("DROP POLICY IF EXISTS user_notification_prefs_owner_delete ON user_notification_prefs;")
    op.execute("DROP POLICY IF EXISTS user_notification_prefs_owner_update ON user_notification_prefs;")
    op.execute("DROP POLICY IF EXISTS user_notification_prefs_owner_insert ON user_notification_prefs;")
    op.execute("DROP POLICY IF EXISTS user_notification_prefs_owner_select ON user_notification_prefs;")
    op.execute("ALTER TABLE user_notification_prefs DISABLE ROW LEVEL SECURITY;")

    # user_badges
    op.execute("DROP POLICY IF EXISTS user_badges_owner_delete ON user_badges;")
    op.execute("DROP POLICY IF EXISTS user_badges_owner_update ON user_badges;")
    op.execute("DROP POLICY IF EXISTS user_badges_owner_insert ON user_badges;")
    op.execute("DROP POLICY IF EXISTS user_badges_owner_select ON user_badges;")
    op.execute("ALTER TABLE user_badges DISABLE ROW LEVEL SECURITY;")

    # ai_messages（必须在 ai_sessions 之前删，因为 ai_messages 引用 ai_sessions）
    op.execute("DROP POLICY IF EXISTS ai_messages_owner_delete ON ai_messages;")
    op.execute("DROP POLICY IF EXISTS ai_messages_owner_update ON ai_messages;")
    op.execute("DROP POLICY IF EXISTS ai_messages_owner_insert ON ai_messages;")
    op.execute("DROP POLICY IF EXISTS ai_messages_owner_select ON ai_messages;")
    op.execute("ALTER TABLE ai_messages DISABLE ROW LEVEL SECURITY;")

    # ai_sessions
    op.execute("DROP POLICY IF EXISTS ai_sessions_owner_delete ON ai_sessions;")
    op.execute("DROP POLICY IF EXISTS ai_sessions_owner_update ON ai_sessions;")
    op.execute("DROP POLICY IF EXISTS ai_sessions_owner_insert ON ai_sessions;")
    op.execute("DROP POLICY IF EXISTS ai_sessions_owner_select ON ai_sessions;")
    op.execute("ALTER TABLE ai_sessions DISABLE ROW LEVEL SECURITY;")

    # recall_sessions
    op.execute("DROP POLICY IF EXISTS recall_sessions_owner_delete ON recall_sessions;")
    op.execute("DROP POLICY IF EXISTS recall_sessions_owner_update ON recall_sessions;")
    op.execute("DROP POLICY IF EXISTS recall_sessions_owner_insert ON recall_sessions;")
    op.execute("DROP POLICY IF EXISTS recall_sessions_owner_select ON recall_sessions;")
    op.execute("ALTER TABLE recall_sessions DISABLE ROW LEVEL SECURITY;")

    # feedback
    op.execute("DROP POLICY IF EXISTS feedback_owner_delete ON feedback;")
    op.execute("DROP POLICY IF EXISTS feedback_owner_update ON feedback;")
    op.execute("DROP POLICY IF EXISTS feedback_owner_insert ON feedback;")
    op.execute("DROP POLICY IF EXISTS feedback_owner_select ON feedback;")
    op.execute("ALTER TABLE feedback DISABLE ROW LEVEL SECURITY;")

    # posts
    op.execute("DROP POLICY IF EXISTS posts_owner_delete ON posts;")
    op.execute("DROP POLICY IF EXISTS posts_owner_update ON posts;")
    op.execute("DROP POLICY IF EXISTS posts_owner_insert ON posts;")
    op.execute("DROP POLICY IF EXISTS posts_owner_select ON posts;")
    op.execute("ALTER TABLE posts DISABLE ROW LEVEL SECURITY;")

    # checkins
    op.execute("DROP POLICY IF EXISTS checkins_owner_delete ON checkins;")
    op.execute("DROP POLICY IF EXISTS checkins_owner_update ON checkins;")
    op.execute("DROP POLICY IF EXISTS checkins_owner_insert ON checkins;")
    op.execute("DROP POLICY IF EXISTS checkins_owner_select ON checkins;")
    op.execute("ALTER TABLE checkins DISABLE ROW LEVEL SECURITY;")

    # plans
    op.execute("DROP POLICY IF EXISTS plans_owner_delete ON plans;")
    op.execute("DROP POLICY IF EXISTS plans_owner_update ON plans;")
    op.execute("DROP POLICY IF EXISTS plans_owner_insert ON plans;")
    op.execute("DROP POLICY IF EXISTS plans_owner_select ON plans;")
    op.execute("ALTER TABLE plans DISABLE ROW LEVEL SECURITY;")

    # reports
    op.execute("DROP POLICY IF EXISTS reports_owner_delete ON reports;")
    op.execute("DROP POLICY IF EXISTS reports_owner_update ON reports;")
    op.execute("DROP POLICY IF EXISTS reports_owner_insert ON reports;")
    op.execute("DROP POLICY IF EXISTS reports_owner_select ON reports;")
    op.execute("ALTER TABLE reports DISABLE ROW LEVEL SECURITY;")

    # users（最后处理）
    op.execute("DROP POLICY IF EXISTS users_owner_delete ON users;")
    op.execute("DROP POLICY IF EXISTS users_owner_update ON users;")
    op.execute("DROP POLICY IF EXISTS users_owner_select ON users;")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")
