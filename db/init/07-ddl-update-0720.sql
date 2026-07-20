-- ═══════════════════════════════════════════════════════════════════════
-- Selfwell 数据库迁移脚本
-- 版本: V3.1 存量对齐
-- 日期: 2026-07-20
-- 用途: 将存量 DB 结构对齐 data-architecture.md V3.1
--
-- 执行顺序: 07-ddl-update-0720.sql（接 06-ddl-update-0707.sql）
--
-- 变更清单:
--   [A] users 表: unionid/nickname/avatar 移除 NOT NULL
--   [B] users 表: ADD preferred_time / sitting_hours（ SRS §3.1 新字段）
--   [C] reports 表: 审计字段重命名 updated_at → last_updated_time
--   [D] videos 表: 审计字段重命名 updated_at → last_updated_time
--   [E] plans 表: 审计字段重命名 + days JSON 列存量保留（SDS C-5 过渡）
--   [F] plan_days 表: CREATE（SDS C-5 核心）
--   [G] photos 表: CREATE（诊断照片存储）
--   [H] feedback 表: CREATE（对齐存量表名）
--   [I] ai_messages 表: ADD CHECK (seq >= 1)
--   [J] recall_sessions 表: ADD CHECK (summary/encourage 长度)
--   [K] share_posters 表: CREATE
--   [L] CHECK 约束补充（reports / videos / plans / checkins / feedback）
--
-- 前置条件: db/init/00~06 已执行
-- 依赖: 无外部依赖，可重复执行（IF NOT EXISTS / DROP IF EXISTS）
-- ═══════════════════════════════════════════════════════════════════════

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════
-- [A] users 表: unionid / nickname / avatar 移除 NOT NULL
-- SRS §3.1 要求 nullable（非微信用户可注册）
-- ═══════════════════════════════════════════════════════════════════════

ALTER TABLE users
  ALTER COLUMN unionid DROP NOT NULL,
  ALTER COLUMN nickname DROP NOT NULL,
  ALTER COLUMN avatar DROP NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- [B] users 表: ADD preferred_time / sitting_hours（SRS §3.1 新字段）
-- ═══════════════════════════════════════════════════════════════════════

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS preferred_time VARCHAR(16),
  ADD COLUMN IF NOT EXISTS sitting_hours VARCHAR(16);

-- 新字段 CHECK 约束（已存在则跳过）
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_users_preferred_time'
  ) THEN
    ALTER TABLE users ADD CONSTRAINT chk_users_preferred_time
      CHECK (preferred_time IS NULL OR preferred_time IN ('早','中','晚','不固定'));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_users_sitting_hours'
  ) THEN
    ALTER TABLE users ADD CONSTRAINT chk_users_sitting_hours
      CHECK (sitting_hours IS NULL OR sitting_hours IN ('<4h','4-8h','8-12h','12h+'));
  END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════════════
-- [C] reports 表: 审计字段重命名 updated_at → last_updated_time
--                     updated_by  → last_updated_by
-- 策略: 先加新列 → 迁移数据 → 删除旧列
-- 注意: 如旧列已重命名则跳过
-- ═══════════════════════════════════════════════════════════════════════

-- Step 1: 加新列（如不存在）
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'reports' AND column_name = 'last_updated_time'
  ) THEN
    ALTER TABLE reports ADD COLUMN last_updated_time TIMESTAMPTZ NOT NULL DEFAULT NOW();
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'reports' AND column_name = 'last_updated_by'
  ) THEN
    ALTER TABLE reports ADD COLUMN last_updated_by VARCHAR(64);
  END IF;
END $$;

-- Step 2: 迁移数据（updated_at → last_updated_time, updated_by → last_updated_by）
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'reports' AND column_name = 'updated_at'
  ) THEN
    UPDATE reports SET last_updated_time = updated_at WHERE last_updated_time IS NULL;
    ALTER TABLE reports DROP COLUMN IF EXISTS updated_at;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'reports' AND column_name = 'updated_by'
  ) THEN
    UPDATE reports SET last_updated_by = updated_by WHERE last_updated_by IS NULL AND updated_by IS NOT NULL;
    ALTER TABLE reports DROP COLUMN IF EXISTS updated_by;
  END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════════════
-- [D] videos 表: 审计字段重命名 updated_at → last_updated_time
-- ═══════════════════════════════════════════════════════════════════════

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'videos' AND column_name = 'last_updated_time'
  ) THEN
    ALTER TABLE videos ADD COLUMN last_updated_time TIMESTAMPTZ NOT NULL DEFAULT NOW();
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'videos' AND column_name = 'updated_at'
  ) THEN
    UPDATE videos SET last_updated_time = updated_at WHERE last_updated_time IS NULL;
    ALTER TABLE videos DROP COLUMN IF EXISTS updated_at;
  END IF;
END $$;

-- videos.source / difficulty / status CHECK 约束
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_videos_source') THEN
    ALTER TABLE videos ADD CONSTRAINT chk_videos_source
      CHECK (source IN ('bilibili','xiaohongshu','douyin','youtube','self_hosted'));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_videos_difficulty') THEN
    ALTER TABLE videos ADD CONSTRAINT chk_videos_difficulty
      CHECK (difficulty BETWEEN 1 AND 5);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_videos_status') THEN
    ALTER TABLE videos ADD CONSTRAINT chk_videos_status
      CHECK (status IN ('active','inactive'));
  END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════════════
-- [E] plans 表: 审计字段重命名 + days JSON 列存量保留（SDS C-5 过渡）
-- 注意: plans.updated_at 在 06-ddl-update-0707.sql 中已存在
--       迁移时保留已有数据
-- ═══════════════════════════════════════════════════════════════════════

-- Step 1: 加新列（仅当不存在时）
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'plans' AND column_name = 'last_updated_time'
  ) THEN
    ALTER TABLE plans ADD COLUMN last_updated_time TIMESTAMPTZ NOT NULL DEFAULT NOW();
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'plans' AND column_name = 'last_updated_by'
  ) THEN
    ALTER TABLE plans ADD COLUMN last_updated_by VARCHAR(64);
  END IF;
END $$;

-- Step 2: 迁移已有 updated_at / updated_by 数据
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'plans' AND column_name = 'updated_at'
  ) THEN
    UPDATE plans SET last_updated_time = updated_at WHERE last_updated_time IS NULL;
    ALTER TABLE plans DROP COLUMN IF EXISTS updated_at;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'plans' AND column_name = 'updated_by'
  ) THEN
    UPDATE plans SET last_updated_by = updated_by WHERE last_updated_by IS NULL AND updated_by IS NOT NULL;
    ALTER TABLE plans DROP COLUMN IF EXISTS updated_by;
  END IF;
END $$;

-- Step 3: days JSON 列存量保留（SDS C-5 过渡字段，不删除，待 MVP 后迁移）
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'plans' AND column_name = 'days'
  ) THEN
    ALTER TABLE plans ADD COLUMN days JSONB NOT NULL DEFAULT '[]';
  END IF;
END $$;

-- Step 4: plans CHECK 约束
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_plans_status') THEN
    ALTER TABLE plans ADD CONSTRAINT chk_plans_status
      CHECK (status IN ('active','completed','abandoned'));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_plans_dates') THEN
    ALTER TABLE plans ADD CONSTRAINT chk_plans_dates
      CHECK (started_at IS NULL OR completed_at IS NULL OR completed_at::date >= started_at);
  END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════════════
-- [F] plan_days 表: CREATE（SDS C-5 核心，已锁）
-- 方案每日任务子表
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS plan_days (
    id               UUID         PRIMARY KEY DEFAULT uuidv7(),
    plan_id          UUID         NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    day_index        SMALLINT     NOT NULL,
    phase            SMALLINT     NOT NULL,
    duration_minutes SMALLINT,
    title            VARCHAR(128) NOT NULL,
    source           VARCHAR(32)  NOT NULL DEFAULT 'video_pool',
    status           VARCHAR(20)  NOT NULL DEFAULT 'pending',
    video_id         UUID         REFERENCES videos(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_updated_time TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_plan_days_index CHECK (day_index BETWEEN 1 AND 21),
    CONSTRAINT chk_plan_days_phase CHECK (phase IN (1,2,3)),
    CONSTRAINT chk_plan_days_status CHECK (status IN ('pending','done','locked'))
);

-- plan_days 索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_plan_days_plan_day ON plan_days(plan_id, day_index);
CREATE INDEX IF NOT EXISTS idx_plan_days_video ON plan_days(video_id) WHERE video_id IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- [G] photos 表: CREATE（诊断照片存储）
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS photos (
    id           UUID         PRIMARY KEY DEFAULT uuidv7(),
    report_id    UUID         NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    url          VARCHAR(500),
    object_key   VARCHAR(255),
    body_part    VARCHAR(32)  NOT NULL,
    format       VARCHAR(10)  NOT NULL DEFAULT 'jpg',
    size_bytes   BIGINT        NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at   TIMESTAMPTZ,
    CONSTRAINT chk_photos_body_part CHECK (body_part IN ('face','head','shoulder_neck'))
);

CREATE INDEX IF NOT EXISTS idx_photos_report ON photos(report_id);

-- ═══════════════════════════════════════════════════════════════════════
-- [H] feedback 表: CREATE（对齐存量 DB 表名，单数）
-- 存量 DB 已存在此表，本语句仅确保定义完整
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS feedback (
    id                UUID         PRIMARY KEY DEFAULT uuidv7(),
    user_id           UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    feedback_type     VARCHAR(32)  NOT NULL,
    text_content      VARCHAR(2000),
    photo_url         VARCHAR(500),
    body_part         VARCHAR(32),
    client_created_at TIMESTAMPTZ,
    ai_ack_text       VARCHAR(100),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_updated_time TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at        TIMESTAMPTZ,
    CONSTRAINT chk_feedback_type CHECK (feedback_type IN ('mood_text','mood_photo','period_photo','plan_compare_photo')),
    CONSTRAINT chk_feedback_body_part CHECK (body_part IS NULL OR body_part IN ('face','head','shoulder_neck','waist','leg','overall_look'))
);

CREATE INDEX IF NOT EXISTS idx_feedback_user_time ON feedback(user_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_feedback_user_type ON feedback(user_id, feedback_type, created_at DESC) WHERE deleted_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- [I] ai_messages 表: ADD CHECK seq >= 1
-- ═══════════════════════════════════════════════════════════════════════

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_ai_messages_seq') THEN
    ALTER TABLE ai_messages ADD CONSTRAINT chk_ai_messages_seq CHECK (seq >= 1);
  END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════════════
-- [J] recall_sessions 表: ADD CHECK (summary/encourage 长度)
-- ═══════════════════════════════════════════════════════════════════════

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_recall_summary_len') THEN
    ALTER TABLE recall_sessions ADD CONSTRAINT chk_recall_summary_len
      CHECK (summary IS NULL OR length(summary) <= 200);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_recall_encourage_len') THEN
    ALTER TABLE recall_sessions ADD CONSTRAINT chk_recall_encourage_len
      CHECK (encourage IS NULL OR length(encourage) <= 80);
  END IF;
END $$;

-- recall_sessions CHECK trigger（已在 03-checks.sql 定义，这里仅补遗漏）
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_recall_trigger') THEN
    ALTER TABLE recall_sessions ADD CONSTRAINT chk_recall_trigger
      CHECK (trigger IN ('user_query','auto_day7','auto_day14','auto_day21'));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_recall_days_offset') THEN
    ALTER TABLE recall_sessions ADD CONSTRAINT chk_recall_days_offset
      CHECK (days_offset BETWEEN 1 AND 365);
  END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════════════
-- [K] share_posters 表: CREATE
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS share_posters (
    id           UUID         PRIMARY KEY DEFAULT uuidv7(),
    user_id      UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id      UUID         NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    day          SMALLINT     NOT NULL,
    template     VARCHAR(32)  NOT NULL DEFAULT 'hug_card',
    poster_url   VARCHAR(500),
    expires_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    deleted_at   TIMESTAMPTZ,
    CONSTRAINT chk_share_posters_day CHECK (day IN (7,14,21)),
    CONSTRAINT chk_share_posters_template CHECK (template IN ('hug_card','progress','achievement'))
);

CREATE INDEX IF NOT EXISTS idx_share_posters_user ON share_posters(user_id);
CREATE INDEX IF NOT EXISTS idx_share_posters_expires ON share_posters(expires_at) WHERE expires_at IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- [L] reports 表: ADD CHECK status（存量表可能缺少）
-- ═══════════════════════════════════════════════════════════════════════

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_reports_status') THEN
    ALTER TABLE reports ADD CONSTRAINT chk_reports_status
      CHECK (status IN ('queued','processing','ready','failed'));
  END IF;
END $$;

-- checkins 表: ADD CHECK day_index（存量表可能缺少）
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_checkins_day') THEN
    ALTER TABLE checkins ADD CONSTRAINT chk_checkins_day CHECK (day_index BETWEEN 1 AND 21);
  END IF;
END $$;

COMMIT;

-- ═══════════════════════════════════════════════════════════════════════
-- 验证查询（执行后确认结果）
-- ═══════════════════════════════════════════════════════════════════════

-- V1: users 字段 nullable 验证
SELECT column_name, is_nullable
FROM information_schema.columns
WHERE table_name = 'users' AND column_name IN ('unionid','nickname','avatar','preferred_time','sitting_hours');

-- V2: reports 审计字段重命名
SELECT column_name FROM information_schema.columns
WHERE table_name = 'reports' AND column_name IN ('updated_at','updated_by','last_updated_time','last_updated_by');

-- V3: videos 审计字段重命名
SELECT column_name FROM information_schema.columns
WHERE table_name = 'videos' AND column_name IN ('updated_at','last_updated_time');

-- V4: plans days 过渡列存在
SELECT column_name FROM information_schema.columns
WHERE table_name = 'plans' AND column_name = 'days';

-- V5: 新建表存在
SELECT tablename FROM pg_tables WHERE schemaname = 'public'
  AND tablename IN ('photos','plan_days','share_posters');

-- V6: CHECK 约束数量
SELECT conname FROM pg_constraint WHERE contype = 'c'
  AND conrelid::regclass::text IN ('reports','videos','plans','plan_days','checkins','feedback','share_posters');
