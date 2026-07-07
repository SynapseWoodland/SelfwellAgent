-- ═══════════════════════════════════════════════════════════════════════
-- 诊断 1：看 users 表当前列
-- ═══════════════════════════════════════════════════════════════════════
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'users'
ORDER BY ordinal_position;

-- ═══════════════════════════════════════════════════════════════════════
-- 修复 1：给 users 表加 status 列
-- ═══════════════════════════════════════════════════════════════════════
BEGIN;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'active';

-- ═══════════════════════════════════════════════════════════════════════
-- 修复 2：CHECK 约束（draft / active / churned）
-- ═══════════════════════════════════════════════════════════════════════
ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_status;
ALTER TABLE users ADD  CONSTRAINT chk_users_status
  CHECK (status IN ('draft','active','churned'));

-- ═══════════════════════════════════════════════════════════════════════
-- 修复 3：状态字段部分索引（cron 按 status 扫未软删用户）
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS ix_users_status ON users(status)
  WHERE deleted_at IS NULL;

COMMIT;

-- ═══════════════════════════════════════════════════════════════════════
-- 验证 1：status 列到位
-- ═══════════════════════════════════════════════════════════════════════
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'users'
  AND column_name = 'status';

-- ═══════════════════════════════════════════════════════════════════════
-- 验证 2：CHECK 约束到位
-- ═══════════════════════════════════════════════════════════════════════
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'public.users'::regclass AND contype = 'c'
  AND conname = 'chk_users_status';

-- ═══════════════════════════════════════════════════════════════════════
-- 验证 3：索引到位
-- ═══════════════════════════════════════════════════════════════════════
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'users' AND indexname = 'ix_users_status';