-- =============================================================================
-- 02-indexes.sql · 11 张业务表全部二级索引
--   职责：二级索引（PK 在 §1 CREATE TABLE 时声明）；部分索引只覆盖热数据
--   依据：docs/data/data-dictionary.md 附录 I §I.2
--   注意：CREATE INDEX CONCURRENTLY 不能在事务内执行；
--         本脚本是 init-only（首次部署），不使用 CONCURRENTLY 以保证原子性
--         生产环境增量索引请用 0021_add_concurrent_index.sql 等单独脚本
-- =============================================================================

-- ═══════════════════════════════════════════════════════════════════════
-- 2.1 users（§1.3 + §1.4 + §1.5）
-- ═══════════════════════════════════════════════════════════════════════
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_unionid
  ON users(unionid);
CREATE INDEX IF NOT EXISTS idx_users_platform
  ON users(platform);
CREATE INDEX IF NOT EXISTS idx_users_last_active_at
  ON users(last_active_at);

-- 复合索引
CREATE INDEX IF NOT EXISTS idx_users_unionid_platform
  ON users(unionid, platform);
CREATE INDEX IF NOT EXISTS idx_users_active_platform
  ON users(platform, last_active_at DESC);

-- 索引补丁（M2/M3 上线前必加）
CREATE INDEX IF NOT EXISTS idx_users_created
  ON users(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_email
  ON users(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_openid_mp
  ON users(openid_mp) WHERE openid_mp IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_openid_app
  ON users(openid_app) WHERE openid_app IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_deleted
  ON users(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_cache_expires
  ON users(report_cache_expires_at) WHERE report_cache_expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_device
  ON users(device_id) WHERE device_id IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- 2.2 reports
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_reports_user_id
  ON reports(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_created_at
  ON reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_user_created
  ON reports(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_tags_gin
  ON reports USING GIN(tags);

-- 索引补丁
CREATE INDEX IF NOT EXISTS idx_reports_deleted_at
  ON reports(deleted_at) WHERE deleted_at IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- 2.3 videos（公共数据，不建 deleted_at 索引）
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_videos_source
  ON videos(source);
CREATE INDEX IF NOT EXISTS idx_videos_status
  ON videos(status);
CREATE INDEX IF NOT EXISTS idx_videos_difficulty
  ON videos(difficulty);
CREATE INDEX IF NOT EXISTS idx_videos_duration
  ON videos(duration_sec);
CREATE INDEX IF NOT EXISTS idx_videos_created_at
  ON videos(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_videos_tags_gin
  ON videos USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_videos_active_difficulty
  ON videos(status, difficulty, duration_sec);

-- 索引补丁
CREATE INDEX IF NOT EXISTS idx_videos_active_created
  ON videos(created_at DESC) WHERE status = 'active';

-- ═══════════════════════════════════════════════════════════════════════
-- 2.4 plans
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_plans_user_id
  ON plans(user_id);
CREATE INDEX IF NOT EXISTS idx_plans_report_id
  ON plans(report_id);
CREATE INDEX IF NOT EXISTS idx_plans_user_created
  ON plans(user_id, created_at DESC);

-- 索引补丁
CREATE INDEX IF NOT EXISTS idx_plans_user_status
  ON plans(user_id, created_at DESC) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_plans_deleted_at
  ON plans(deleted_at) WHERE deleted_at IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- 2.5 checkins
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_checkins_user_id
  ON checkins(user_id);
CREATE INDEX IF NOT EXISTS idx_checkins_plan_id
  ON checkins(plan_id);
CREATE INDEX IF NOT EXISTS idx_checkins_created_at
  ON checkins(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_checkins_user_plan_day
  ON checkins(user_id, plan_id, day);
CREATE INDEX IF NOT EXISTS idx_checkins_user_day
  ON checkins(user_id, day);

-- 索引补丁
CREATE INDEX IF NOT EXISTS idx_checkins_plan_day
  ON checkins(plan_id, day);
CREATE INDEX IF NOT EXISTS idx_checkins_video_id
  ON checkins(video_id);
CREATE INDEX IF NOT EXISTS idx_checkins_user_created
  ON checkins(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_checkins_deleted_at
  ON checkins(deleted_at) WHERE deleted_at IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- 2.6 posts
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_posts_user_id
  ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_status
  ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_created_at
  ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_approved
  ON posts(status, created_at DESC) WHERE status = 'approved';
CREATE INDEX IF NOT EXISTS idx_posts_user_status
  ON posts(user_id, status);

-- 索引补丁
CREATE INDEX IF NOT EXISTS idx_posts_user_created
  ON posts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_deleted_at
  ON posts(deleted_at) WHERE deleted_at IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- 2.7 agent_sessions（DEPRECATED · 保留读路径）
-- ═══════════════════════════════════════════════════════════════════════
CREATE UNIQUE INDEX IF NOT EXISTS uq_sessions_user_session
  ON agent_sessions(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id
  ON agent_sessions(user_id);

-- 索引补丁
CREATE INDEX IF NOT EXISTS idx_sessions_user_updated
  ON agent_sessions(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_updated
  ON agent_sessions(updated_at);
CREATE INDEX IF NOT EXISTS idx_sessions_expires
  ON agent_sessions(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_deleted_at
  ON agent_sessions(deleted_at) WHERE deleted_at IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- 2.8 feedback（V1.3 新增）
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_feedback_user_time
  ON feedback(user_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_feedback_user_type
  ON feedback(user_id, feedback_type, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_feedback_plan_compare
  ON feedback(user_id, created_at DESC)
  WHERE feedback_type = 'plan_compare_photo' AND deleted_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- 2.9 recall_sessions（V1.3 新增）
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_recall_user_time
  ON recall_sessions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recall_user_trigger
  ON recall_sessions(user_id, trigger, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recall_user_today_auto
  ON recall_sessions(user_id, trigger, created_at)
  WHERE trigger IN ('auto_day7', 'auto_day14', 'auto_day21');
CREATE INDEX IF NOT EXISTS idx_recall_ai_session
  ON recall_sessions(ai_session_id) WHERE ai_session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_recall_deleted_at
  ON recall_sessions(deleted_at) WHERE deleted_at IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- 2.10 ai_sessions（V1.3 新增）
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_ai_session_user_time
  ON ai_sessions(user_id, last_active_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_session_user_entry
  ON ai_sessions(user_id, entry_card, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_session_user_intent
  ON ai_sessions(user_id, primary_intent, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_session_user_open
  ON ai_sessions(user_id, last_active_at DESC) WHERE closed_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- 2.11 ai_messages（V1.3 新增）
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_ai_msg_session_seq
  ON ai_messages(session_id, seq);
CREATE INDEX IF NOT EXISTS idx_ai_msg_session_time
  ON ai_messages(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_msg_safety_fail
  ON ai_messages(safety_passed, created_at DESC) WHERE safety_passed = FALSE;
CREATE INDEX IF NOT EXISTS idx_ai_msg_feedback_ids
  ON ai_messages USING GIN (referenced_feedback_ids)
  WHERE referenced_feedback_ids <> '{}';
CREATE INDEX IF NOT EXISTS idx_ai_msg_video_ids
  ON ai_messages USING GIN (referenced_video_ids)
  WHERE referenced_video_ids <> '{}';