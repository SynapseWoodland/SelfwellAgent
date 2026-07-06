-- =============================================================================
-- 03-checks.sql · 业务枚举 + 一致性 CHECK 约束
--   职责：表级 CHECK（业务枚举固定且高频 + 业务逻辑强制）
--   依据：docs/data/data-dictionary.md 附录 C + 附录 D + 附录 I §I.3
--   设计原则：
--     ✅ 加：业务枚举固定且高频（platform / intensity / status ...）
--     ✅ 加：业务逻辑强制（reviewed_by ↔ reviewed_at 一致性）
--     ❌ 不加：永远 ≥ 0 的数值（version / like_count）
--     ❌ 不加：正则校验（email / phone）
--     ❌ 不加：未来扩展的开放枚举（videos.source 全网聚合）
-- =============================================================================

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════
-- 3.1 users（6 个 · §1.2 + 附录 C.1）
-- ═══════════════════════════════════════════════════════════════════════
ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_platform;
ALTER TABLE users ADD  CONSTRAINT chk_users_platform
  CHECK (platform IN ('wx_mp','ios','android','harmony'));

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_intensity;
ALTER TABLE users ADD  CONSTRAINT chk_users_intensity
  CHECK (intensity IS NULL OR intensity IN ('轻柔','适中','进阶'));

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_age_range;
ALTER TABLE users ADD  CONSTRAINT chk_users_age_range
  CHECK (age_range IS NULL OR age_range IN ('18-22','23-28','29-35','36-45','45+'));

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_sitting_hours;
ALTER TABLE users ADD  CONSTRAINT chk_users_sitting_hours
  CHECK (sitting_hours IS NULL OR sitting_hours IN ('<4h','4-8h','8-12h','12h+'));

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_preferred_time;
ALTER TABLE users ADD  CONSTRAINT chk_users_preferred_time
  CHECK (preferred_time IS NULL OR preferred_time IN ('早','中','晚','不固定'));

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_push_channel;
ALTER TABLE users ADD  CONSTRAINT chk_users_push_channel
  CHECK (push_channel IS NULL OR push_channel IN ('wx_subscribe','apns','fcm','hms','email'));

-- ═══════════════════════════════════════════════════════════════════════
-- 3.2 reports（1 个 · 附录 C.2 + F P1-1）
-- ═══════════════════════════════════════════════════════════════════════
ALTER TABLE reports DROP CONSTRAINT IF EXISTS chk_reports_cost;
ALTER TABLE reports ADD  CONSTRAINT chk_reports_cost
  CHECK (llm_cost >= 0 AND llm_cost <= 999999.9999);

-- ═══════════════════════════════════════════════════════════════════════
-- 3.3 videos（3 个 · 附录 C.3；❌ 不加 chk_videos_source）
-- ═══════════════════════════════════════════════════════════════════════
ALTER TABLE videos DROP CONSTRAINT IF EXISTS chk_videos_difficulty;
ALTER TABLE videos ADD  CONSTRAINT chk_videos_difficulty
  CHECK (difficulty BETWEEN 1 AND 5);

ALTER TABLE videos DROP CONSTRAINT IF EXISTS chk_videos_duration;
ALTER TABLE videos ADD  CONSTRAINT chk_videos_duration
  CHECK (duration_sec > 0 AND duration_sec <= 3600);

ALTER TABLE videos DROP CONSTRAINT IF EXISTS chk_videos_status;
ALTER TABLE videos ADD  CONSTRAINT chk_videos_status
  CHECK (status IN ('active','inactive'));

-- ═══════════════════════════════════════════════════════════════════════
-- 3.4 plans（2 个 · 附录 C.4）
-- ═══════════════════════════════════════════════════════════════════════
ALTER TABLE plans DROP CONSTRAINT IF EXISTS chk_plans_status;
ALTER TABLE plans ADD  CONSTRAINT chk_plans_status
  CHECK (status IN ('active','completed','abandoned'));

ALTER TABLE plans DROP CONSTRAINT IF EXISTS chk_plans_dates;
ALTER TABLE plans ADD  CONSTRAINT chk_plans_dates
  CHECK (started_at IS NULL OR completed_at IS NULL OR completed_at >= started_at);

-- ═══════════════════════════════════════════════════════════════════════
-- 3.5 checkins（❌ 不加 chk_checkins_day · 附录 C.5）
-- ═══════════════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════════════════
-- 3.6 posts（3 个 · 附录 C.6）
-- ═══════════════════════════════════════════════════════════════════════
ALTER TABLE posts DROP CONSTRAINT IF EXISTS chk_posts_status;
ALTER TABLE posts ADD  CONSTRAINT chk_posts_status
  CHECK (status IN ('pending','approved','rejected'));

ALTER TABLE posts DROP CONSTRAINT IF EXISTS chk_posts_images_count;
ALTER TABLE posts ADD  CONSTRAINT chk_posts_images_count
  CHECK (images IS NULL OR jsonb_array_length(images) <= 9);

ALTER TABLE posts DROP CONSTRAINT IF EXISTS chk_posts_reviewed_consistency;
ALTER TABLE posts ADD  CONSTRAINT chk_posts_reviewed_consistency
  CHECK ((reviewed_by IS NULL AND reviewed_at IS NULL)
      OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL));

-- ═══════════════════════════════════════════════════════════════════════
-- 3.7 agent_sessions（DEPRECATED · ❌ 不加 expires_at CHECK · 附录 H）
-- ═══════════════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════════════════
-- 3.8 feedback（5 个 · 附录 D.1.2）
-- ═══════════════════════════════════════════════════════════════════════
ALTER TABLE feedback DROP CONSTRAINT IF EXISTS chk_feedback_type;
ALTER TABLE feedback ADD  CONSTRAINT chk_feedback_type
  CHECK (feedback_type IN ('mood_text','mood_photo','period_photo','plan_compare_photo'));

ALTER TABLE feedback DROP CONSTRAINT IF EXISTS chk_feedback_text_len;
ALTER TABLE feedback ADD  CONSTRAINT chk_feedback_text_len
  CHECK (text_content IS NULL OR length(text_content) <= 500);

ALTER TABLE feedback DROP CONSTRAINT IF EXISTS chk_feedback_body_part;
ALTER TABLE feedback ADD  CONSTRAINT chk_feedback_body_part
  CHECK (body_part IS NULL OR body_part IN
    ('face','head','shoulder_neck','waist','leg','overall_look'));

-- 核心防脏数据：feedback_type 与 payload 一致性
ALTER TABLE feedback DROP CONSTRAINT IF EXISTS chk_feedback_text_presence;
ALTER TABLE feedback ADD  CONSTRAINT chk_feedback_text_presence
  CHECK (
    (feedback_type = 'mood_text' AND text_content IS NOT NULL AND photo_url IS NULL)
    OR (feedback_type = 'mood_photo' AND photo_url IS NOT NULL AND text_content IS NULL)
    OR (feedback_type IN ('period_photo', 'plan_compare_photo') AND photo_url IS NOT NULL)
  );

ALTER TABLE feedback DROP CONSTRAINT IF EXISTS chk_feedback_body_part_required;
ALTER TABLE feedback ADD  CONSTRAINT chk_feedback_body_part_required
  CHECK (body_part IS NOT NULL OR feedback_type NOT IN ('period_photo', 'plan_compare_photo'));

-- ═══════════════════════════════════════════════════════════════════════
-- 3.9 recall_sessions（3 个 · 附录 D.2.2）
-- ═══════════════════════════════════════════════════════════════════════
ALTER TABLE recall_sessions DROP CONSTRAINT IF EXISTS chk_recall_trigger;
ALTER TABLE recall_sessions ADD  CONSTRAINT chk_recall_trigger
  CHECK (trigger IN ('user_query','auto_day7','auto_day14','auto_day21'));

ALTER TABLE recall_sessions DROP CONSTRAINT IF EXISTS chk_recall_summary_len;
ALTER TABLE recall_sessions ADD  CONSTRAINT chk_recall_summary_len
  CHECK (ai_summary IS NULL OR length(ai_summary) <= 200);

ALTER TABLE recall_sessions DROP CONSTRAINT IF EXISTS chk_recall_encourage_len;
ALTER TABLE recall_sessions ADD  CONSTRAINT chk_recall_encourage_len
  CHECK (ai_encourage IS NULL OR length(ai_encourage) <= 80);

-- ═══════════════════════════════════════════════════════════════════════
-- 3.10 ai_sessions（5 个 · 附录 D.3.2）
-- ═══════════════════════════════════════════════════════════════════════
ALTER TABLE ai_sessions DROP CONSTRAINT IF EXISTS chk_ai_session_entry;
ALTER TABLE ai_sessions ADD  CONSTRAINT chk_ai_session_entry
  CHECK (entry_card IS NULL OR entry_card IN
    ('smart_analyze','mood_diary','recall_self','direct_input'));

ALTER TABLE ai_sessions DROP CONSTRAINT IF EXISTS chk_ai_session_intent;
ALTER TABLE ai_sessions ADD  CONSTRAINT chk_ai_session_intent
  CHECK (primary_intent IN (
    'module_redirect','read_query','recall','recall_ack',
    'feedback_ack','feedback_create','medical_reject','unknown'
  ));

ALTER TABLE ai_sessions DROP CONSTRAINT IF EXISTS chk_ai_session_persona_start;
ALTER TABLE ai_sessions ADD  CONSTRAINT chk_ai_session_persona_start
  CHECK (persona_state_start IN ('warm','neutral','slight_hug','medical_guarded'));

ALTER TABLE ai_sessions DROP CONSTRAINT IF EXISTS chk_ai_session_persona_end;
ALTER TABLE ai_sessions ADD  CONSTRAINT chk_ai_session_persona_end
  CHECK (persona_state_end IS NULL OR persona_state_end IN
    ('warm','neutral','slight_hug','medical_guarded'));

ALTER TABLE ai_sessions DROP CONSTRAINT IF EXISTS chk_ai_session_close;
ALTER TABLE ai_sessions ADD  CONSTRAINT chk_ai_session_close
  CHECK (
    (closed_at IS NULL AND last_active_at IS NOT NULL)
    OR (closed_at IS NOT NULL AND closed_at >= started_at)
  );

-- ═══════════════════════════════════════════════════════════════════════
-- 3.11 ai_messages（4 个 CHECK + 1 个 UNIQUE · 附录 D.4.2 + F P0-3）
-- ═══════════════════════════════════════════════════════════════════════
ALTER TABLE ai_messages DROP CONSTRAINT IF EXISTS chk_ai_msg_role;
ALTER TABLE ai_messages ADD  CONSTRAINT chk_ai_msg_role
  CHECK (role IN ('user','assistant','system'));

-- content 上限 65535 字（防御恶意，附录 F P0-3 修订）
ALTER TABLE ai_messages DROP CONSTRAINT IF EXISTS chk_ai_msg_content_len;
ALTER TABLE ai_messages ADD  CONSTRAINT chk_ai_msg_content_len
  CHECK (length(content) <= 65535);

ALTER TABLE ai_messages DROP CONSTRAINT IF EXISTS chk_ai_msg_seq_positive;
ALTER TABLE ai_messages ADD  CONSTRAINT chk_ai_msg_seq_positive
  CHECK (seq >= 1);

ALTER TABLE ai_messages DROP CONSTRAINT IF EXISTS chk_ai_msg_trigger;
ALTER TABLE ai_messages ADD  CONSTRAINT chk_ai_msg_trigger
  CHECK (trigger IS NULL OR trigger IN (
    'user_input','smart_router','module_dispatch','persona_ack',
    'auto_recall_bubble','safety_fallback','medical_reject','unknown_fallback'
  ));

-- 同 session 内 seq 唯一
ALTER TABLE ai_messages DROP CONSTRAINT IF EXISTS uq_ai_msg_session_seq;
ALTER TABLE ai_messages ADD  CONSTRAINT uq_ai_msg_session_seq UNIQUE (session_id, seq);

-- ═══════════════════════════════════════════════════════════════════════
-- 3.12 故意不加的（5 个 · 防止过度约束 · 附录 C.8）
--   ❌ users.version     应用层永远写 ≥ 0
--   ❌ users.email 格式   正则维护成本高，Pydantic 校验
--   ❌ videos.source     全网聚合未来扩展
--   ❌ posts.like_count  应用层加 1 永远 ≥ 0
--   ❌ posts.comment_count 同上
-- ═══════════════════════════════════════════════════════════════════════

COMMIT;