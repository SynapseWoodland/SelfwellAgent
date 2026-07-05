-- Migration 0006: CHECK 约束补全 + 触发器设计
-- 对应文档: docs/data/data-dictionary.md 附录 C + 附录 D
-- 设计依据: PRD V2.0 / facts-anchor.md / SPEC-M3 / SPEC-M4
--
-- ⚠️ 重要执行说明：
--   1. 本脚本必须在已应用 0001-0005 迁移的数据库上执行
--   2. 触发器 ③ 依赖 plans / checkins / posts 表有 deleted_at 字段
--      （0005 已为 users 加 deleted_at，但其他三表待补；本脚本会先补字段）
--   3. 全程在事务中执行，单条失败自动回滚
--   4. 触发器 DROP IF EXISTS 保证幂等（可重复执行）
--   5. 建议在低峰期执行；首次执行会扫描全表做 CHECK，10w 行预计 < 1s

BEGIN;

-- ════════════════════════════════════════════════════════════════════
-- 第一部分：补充 deleted_at 字段（触发器 ③ 的前置依赖）
-- ════════════════════════════════════════════════════════════════════

ALTER TABLE plans    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE checkins ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE posts    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_plans_deleted_at
  ON plans(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_checkins_deleted_at
  ON checkins(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_deleted_at
  ON posts(deleted_at) WHERE deleted_at IS NOT NULL;

-- ════════════════════════════════════════════════════════════════════
-- 第二部分：CHECK 约束（共 18 个）
--   设计原则：
--   ✅ 加：业务枚举固定且高频使用
--   ✅ 加：业务逻辑强制（如 reviewed_by/时间一致性）
--   ❌ 不加：永远 ≥ 0 的数值 / 正则 / 未来扩展的开放枚举
-- ════════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────
-- C.1 users 表（6 个）
-- ────────────────────────────────────────────────────
ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_platform;
ALTER TABLE users ADD CONSTRAINT chk_users_platform
  CHECK (platform IN ('wx_mp','ios','android','harmony'));

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_intensity;
ALTER TABLE users ADD CONSTRAINT chk_users_intensity
  CHECK (intensity IS NULL OR intensity IN ('温和','舒适','进阶'));

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_age_range;
ALTER TABLE users ADD CONSTRAINT chk_users_age_range
  CHECK (age_range IS NULL OR age_range IN ('18-22','23-28','29-35','36-45','45+'));

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_sitting_hours;
ALTER TABLE users ADD CONSTRAINT chk_users_sitting_hours
  CHECK (sitting_hours IS NULL OR sitting_hours IN ('<4h','4-8h','8-12h','12h+'));

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_preferred_time;
ALTER TABLE users ADD CONSTRAINT chk_users_preferred_time
  CHECK (preferred_time IS NULL OR preferred_time IN ('早','中','晚','不固定'));

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_push_channel;
ALTER TABLE users ADD CONSTRAINT chk_users_push_channel
  CHECK (push_channel IS NULL OR push_channel IN ('wx_subscribe','apns','fcm','hms','email'));

-- ────────────────────────────────────────────────────
-- C.2 reports 表（1 个）
-- ────────────────────────────────────────────────────
ALTER TABLE reports DROP CONSTRAINT IF EXISTS chk_reports_cost;
ALTER TABLE reports ADD CONSTRAINT chk_reports_cost
  CHECK (llm_cost >= 0 AND llm_cost <= 9999.9999);

-- ────────────────────────────────────────────────────
-- C.3 videos 表（3 个 · 注意：不约束 source，全网聚合）
-- ────────────────────────────────────────────────────
ALTER TABLE videos DROP CONSTRAINT IF EXISTS chk_videos_difficulty;
ALTER TABLE videos ADD CONSTRAINT chk_videos_difficulty
  CHECK (difficulty BETWEEN 1 AND 5);

ALTER TABLE videos DROP CONSTRAINT IF EXISTS chk_videos_duration;
ALTER TABLE videos ADD CONSTRAINT chk_videos_duration
  CHECK (duration_sec > 0 AND duration_sec <= 3600);

ALTER TABLE videos DROP CONSTRAINT IF EXISTS chk_videos_status;
ALTER TABLE videos ADD CONSTRAINT chk_videos_status
  CHECK (status IN ('active','inactive'));

-- ────────────────────────────────────────────────────
-- C.4 plans 表（2 个）
-- ────────────────────────────────────────────────────
ALTER TABLE plans DROP CONSTRAINT IF EXISTS chk_plans_status;
ALTER TABLE plans ADD CONSTRAINT chk_plans_status
  CHECK (status IN ('active','completed','abandoned'));

ALTER TABLE plans DROP CONSTRAINT IF EXISTS chk_plans_dates;
ALTER TABLE plans ADD CONSTRAINT chk_plans_dates
  CHECK (started_at IS NULL OR completed_at IS NULL OR completed_at >= started_at);

-- ────────────────────────────────────────────────────
-- C.5 checkins 表（1 个 · MVP 21 天方案）
-- ────────────────────────────────────────────────────
ALTER TABLE checkins DROP CONSTRAINT IF EXISTS chk_checkins_day;
ALTER TABLE checkins ADD CONSTRAINT chk_checkins_day
  CHECK (day BETWEEN 1 AND 21);

-- ────────────────────────────────────────────────────
-- C.6 posts 表（3 个）
-- ────────────────────────────────────────────────────
ALTER TABLE posts DROP CONSTRAINT IF EXISTS chk_posts_status;
ALTER TABLE posts ADD CONSTRAINT chk_posts_status
  CHECK (status IN ('pending','approved','rejected'));

ALTER TABLE posts DROP CONSTRAINT IF EXISTS chk_posts_images_count;
ALTER TABLE posts ADD CONSTRAINT chk_posts_images_count
  CHECK (jsonb_array_length(images) <= 9);

ALTER TABLE posts DROP CONSTRAINT IF EXISTS chk_posts_reviewed_consistency;
ALTER TABLE posts ADD CONSTRAINT chk_posts_reviewed_consistency
  CHECK ((reviewed_by IS NULL AND reviewed_at IS NULL)
      OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL));

-- ────────────────────────────────────────────────────
-- C.7 agent_sessions 表（1 个）
-- ────────────────────────────────────────────────────
ALTER TABLE agent_sessions DROP CONSTRAINT IF EXISTS chk_sessions_expires_after_created;
ALTER TABLE agent_sessions ADD CONSTRAINT chk_sessions_expires_after_created
  CHECK (expires_at IS NULL OR expires_at > created_at);

-- ════════════════════════════════════════════════════════════════════
-- 第三部分：触发器（共 3 个）
--   设计原则：
--   ✅ 多表联动的字段（cache 自动填）
--   ✅ 易遗忘的派生字段（expires_at / deleted_at 联级）
--   ❌ 不滥用：业务逻辑能用应用层实现的别用触发器
-- ════════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────
-- 触发器 ①：users.report_cache_expires_at 自动维护
-- ────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION fn_users_set_cache_expires()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.report_cache IS NOT NULL
     AND NEW.report_cache != '{}'::jsonb THEN
    NEW.report_cache_expires_at := NOW() + INTERVAL '7 days';
  ELSE
    NEW.report_cache_expires_at := NULL;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_set_cache_expires ON users;
CREATE TRIGGER trg_users_set_cache_expires
  BEFORE INSERT OR UPDATE OF report_cache ON users
  FOR EACH ROW
  EXECUTE FUNCTION fn_users_set_cache_expires();

-- ────────────────────────────────────────────────────
-- 触发器 ②：reports 插入时自动写入 users.report_cache
-- ────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION fn_reports_init_user_cache()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE users
  SET report_cache = jsonb_build_object(
        'report_id',  NEW.id,
        'directions', NEW.directions,
        'tags',       NEW.tags,
        'summary',    NEW.summary,
        'created_at', NEW.created_at
      )
  WHERE id = NEW.user_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_reports_init_user_cache ON reports;
CREATE TRIGGER trg_reports_init_user_cache
  AFTER INSERT ON reports
  FOR EACH ROW
  EXECUTE FUNCTION fn_reports_init_user_cache();

-- ────────────────────────────────────────────────────
-- 触发器 ③：users 软删除联级
-- ────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION fn_users_soft_delete_cascade()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN
    UPDATE reports  SET deleted_at = NEW.deleted_at WHERE user_id = NEW.id AND deleted_at IS NULL;
    UPDATE plans    SET deleted_at = NEW.deleted_at WHERE user_id = NEW.id AND deleted_at IS NULL;
    UPDATE checkins SET deleted_at = NEW.deleted_at WHERE user_id = NEW.id AND deleted_at IS NULL;
    UPDATE posts    SET deleted_at = NEW.deleted_at WHERE user_id = NEW.id AND deleted_at IS NULL;
    DELETE FROM agent_sessions WHERE user_id = NEW.id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_soft_delete_cascade ON users;
CREATE TRIGGER trg_users_soft_delete_cascade
  AFTER UPDATE OF deleted_at ON users
  FOR EACH ROW
  EXECUTE FUNCTION fn_users_soft_delete_cascade();

COMMIT;

-- ════════════════════════════════════════════════════════════════════
-- 第四部分：验证脚本（执行后跑这些 SELECT 确认生效）
-- ════════════════════════════════════════════════════════════════════

-- 验证 1：所有 CHECK 约束已创建
-- SELECT conname, contype, pg_get_constraintdef(oid)
-- FROM pg_constraint
-- WHERE conrelid::regclass::text IN (
--   'users','reports','videos','plans','checkins','posts','agent_sessions'
-- )
-- AND contype = 'c'
-- ORDER BY conrelid::regclass::text, conname;

-- 验证 2：所有触发器已创建
-- SELECT tgname, tgrelid::regclass, pg_get_triggerdef(oid)
-- FROM pg_trigger
-- WHERE tgname LIKE 'trg_%'
-- ORDER BY tgrelid::regclass, tgname;

-- 验证 3：CHECK 约束生效测试（应当全部报错）
-- INSERT INTO checkins (user_id, plan_id, day, video_id) VALUES (..., 22, ...);
--   → ERROR: violates check constraint "chk_checkins_day"
-- INSERT INTO videos (difficulty) VALUES (10);
--   → ERROR: violates check constraint "chk_videos_difficulty"
-- INSERT INTO posts (status) VALUES ('draft');
--   → ERROR: violates check constraint "chk_posts_status"

-- 验证 4：触发器 ① 生效测试
-- UPDATE users SET report_cache = '{"foo":"bar"}'::jsonb WHERE id = '...';
-- SELECT report_cache_expires_at FROM users WHERE id = '...';
--   → 应该返回 NOW() + 7 days

-- 验证 5：触发器 ② 生效测试（需要有现成 user_id）
-- INSERT INTO reports (id, user_id, photos, directions, tags)
-- VALUES ('rpt_test', '...', '[...]', '[...]', '[...]');
-- SELECT report_cache->>'report_id' FROM users WHERE id = '...';
--   → 应该返回 'rpt_test'