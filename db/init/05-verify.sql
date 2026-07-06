-- =============================================================================
-- 05-verify.sql · 初始化完成后必跑的自检脚本（开发环境/启动后验证）
--   依据：docs/data/data-dictionary.md 附录 I §I.5
--   用途：CI/CD pipeline / 工程师本地 docker compose up 后必跑
--         跑完 4 项 expect 全部命中 → DB 初始化成功
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────
-- 验证 1：11 张表全部存在
-- ─────────────────────────────────────────────────────────────────────
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
    'users','reports','videos','plans','checkins','posts','agent_sessions',
    'feedback','recall_sessions','ai_sessions','ai_messages'
  )
ORDER BY tablename;
-- 期望返回 11 行

-- ─────────────────────────────────────────────────────────────────────
-- 验证 2：CHECK 约束数量（理论值 = 32，见附录 I §I.5 注释）
--   users 6 + reports 1 + videos 3 + plans 2 + posts 3
--   + feedback 5 + recall 3 + ai_session 5 + ai_msg 4 = 32
-- ─────────────────────────────────────────────────────────────────────
SELECT count(*) AS chk_count
FROM pg_constraint
WHERE contype = 'c'
  AND conrelid::regclass::text IN (
    'users','reports','videos','plans','checkins','posts','agent_sessions',
    'feedback','recall_sessions','ai_sessions','ai_messages'
  );

-- ─────────────────────────────────────────────────────────────────────
-- 验证 3：触发器总数（应 = 3）
-- ─────────────────────────────────────────────────────────────────────
SELECT count(*) AS trg_count
FROM pg_trigger
WHERE tgname IN (
  'trg_users_set_cache_expires',
  'trg_reports_init_user_cache',
  'trg_users_soft_delete_cascade'
);

-- ─────────────────────────────────────────────────────────────────────
-- 验证 4：索引数量（理论值）
--   users 14 + reports 6 + videos 8 + plans 5 + checkins 9 + posts 7
--   + agent_sessions 6 + feedback 3 + recall_sessions 5
--   + ai_sessions 4 + ai_messages 5 = 72（含 PK 二级索引）
-- ─────────────────────────────────────────────────────────────────────
SELECT count(*) AS idx_count
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN (
    'users','reports','videos','plans','checkins','posts','agent_sessions',
    'feedback','recall_sessions','ai_sessions','ai_messages'
  );

-- ─────────────────────────────────────────────────────────────────────
-- 验证 5：CHECK 生效负向测试（应当全部报错）
-- ─────────────────────────────────────────────────────────────────────
-- INSERT INTO videos (title, source, video_id, url, duration_sec, difficulty, tags, thumbnail)
--   VALUES ('t','bilibili','v1','http://x',60, 10, '[]'::jsonb, 'http://x');
--   → ERROR: violates check constraint "chk_videos_difficulty"
-- INSERT INTO posts (user_id, content, status)
--   VALUES (..., 'hello', 'draft');
--   → ERROR: violates check constraint "chk_posts_status"
-- INSERT INTO feedback (user_id, feedback_type, text_content, photo_url)
--   VALUES (..., 'mood_text', NULL, 'http://x');
--   → ERROR: violates check constraint "chk_feedback_text_presence"

-- ─────────────────────────────────────────────────────────────────────
-- 验证 6：触发器 ① 生效测试
-- ─────────────────────────────────────────────────────────────────────
-- UPDATE users SET report_cache = '{"foo":"bar"}'::jsonb WHERE id = '...';
-- SELECT report_cache_expires_at FROM users WHERE id = '...';
--   → 应该返回 NOW() + 7 days

-- ─────────────────────────────────────────────────────────────────────
-- 验证 7：触发器 ② 生效测试
-- ─────────────────────────────────────────────────────────────────────
-- INSERT INTO reports (user_id, photos, directions, tags)
--   VALUES ('...', '[]'::jsonb, '[]'::jsonb, '[]'::jsonb);
-- SELECT report_cache->>'report_id' FROM users WHERE id = '...';
--   → 应该返回新插入的 report.id

-- ─────────────────────────────────────────────────────────────────────
-- 验证 8：触发器 ③ 联级软删除测试
-- ─────────────────────────────────────────────────────────────────────
-- UPDATE users SET deleted_at = NOW() WHERE id = '...';
-- SELECT
--   (SELECT count(*) FROM reports     WHERE user_id = '...' AND deleted_at IS NOT NULL) AS reports_deleted,
--   (SELECT count(*) FROM plans       WHERE user_id = '...' AND deleted_at IS NOT NULL) AS plans_deleted,
--   (SELECT count(*) FROM checkins    WHERE user_id = '...' AND deleted_at IS NOT NULL) AS checkins_deleted,
--   (SELECT count(*) FROM posts       WHERE user_id = '...' AND deleted_at IS NOT NULL) AS posts_deleted,
--   (SELECT count(*) FROM ai_sessions WHERE user_id = '...' AND deleted_at IS NOT NULL) AS ai_sessions_deleted,
--   (SELECT count(*) FROM videos      WHERE id = 'vid_xxx') AS videos_unchanged,
--   (SELECT count(*) FROM agent_sessions WHERE user_id = '...') AS agent_sessions_unchanged;
--   → 5 张业务表 deleted_at 被填充；videos / agent_sessions 不受影响