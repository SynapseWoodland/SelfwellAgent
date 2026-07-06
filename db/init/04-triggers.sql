-- =============================================================================
-- 04-triggers.sql · 3 个触发器（附录 E 取消 audit 触发器，审计下沉业务表 4 字段）
--   依据：docs/data/data-dictionary.md 附录 D + 附录 I §I.4
--
--   ① trg_users_set_cache_expires      users BEFORE INSERT/UPDATE report_cache
--   ② trg_reports_init_user_cache      reports AFTER INSERT
--   ③ trg_users_soft_delete_cascade    users AFTER UPDATE deleted_at
--   ❌ 不写 ④~⑩ audit 触发器（附录 E 取消）
--   ③ 联级范围 5 张：reports / plans / checkins / posts / ai_sessions
--      不联级 videos（公共）/ agent_sessions（DEPRECATED）
-- =============================================================================

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════
-- 触发器 ①：users.report_cache_expires_at 自动维护
-- ═══════════════════════════════════════════════════════════════════════
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

-- ═══════════════════════════════════════════════════════════════════════
-- 触发器 ②：reports 插入时自动写入 users.report_cache
-- ═══════════════════════════════════════════════════════════════════════
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
  -- 触发器 ① 会自动给 report_cache_expires_at 赋值
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_reports_init_user_cache ON reports;
CREATE TRIGGER trg_reports_init_user_cache
  AFTER INSERT ON reports
  FOR EACH ROW
  EXECUTE FUNCTION fn_reports_init_user_cache();

-- ═══════════════════════════════════════════════════════════════════════
-- 触发器 ③：users 软删除联级（5 张）
--   集合：reports / plans / checkins / posts / ai_sessions
--   理由：
--     - videos 是全网共有视频库，A 注销不应波及 B 的视频引用
--     - agent_sessions 已 DEPRECATED，冻结不再触发
--     - ai_sessions 是 V1.3 替代 agent_sessions 的新表，必须覆盖 GDPR
-- ═══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION fn_users_soft_delete_cascade()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN
    UPDATE reports     SET deleted_at = NEW.deleted_at WHERE user_id = NEW.id AND deleted_at IS NULL;
    UPDATE plans       SET deleted_at = NEW.deleted_at WHERE user_id = NEW.id AND deleted_at IS NULL;
    UPDATE checkins    SET deleted_at = NEW.deleted_at WHERE user_id = NEW.id AND deleted_at IS NULL;
    UPDATE posts       SET deleted_at = NEW.deleted_at WHERE user_id = NEW.id AND deleted_at IS NULL;
    UPDATE ai_sessions SET deleted_at = NEW.deleted_at WHERE user_id = NEW.id AND deleted_at IS NULL;
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