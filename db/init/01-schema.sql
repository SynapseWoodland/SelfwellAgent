-- =============================================================================
-- 01-schema.sql · 11 张业务表 + DEFAULT uuidv7()
--   职责：建表 DDL；表内 CHECK 集中放 03-checks.sql
--   依据：docs/data/data-dictionary.md 附录 I §I.1
--   表清单（11 张）：
--     旧 7 张：users / reports / videos / plans / checkins / posts / agent_sessions(DEPRECATED)
--     新 4 张：feedback / recall_sessions / ai_sessions / ai_messages
-- =============================================================================

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════
-- 1.1 users（M1 主档）
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS users (
  id                       UUID         PRIMARY KEY DEFAULT uuidv7(),
  unionid                  VARCHAR(128) NOT NULL,
  openid_mp                VARCHAR(128),
  openid_app               VARCHAR(128),
  phone                    VARCHAR(20),
  platform                 VARCHAR(20)  NOT NULL,
  device_id                VARCHAR(128),
  nickname                 VARCHAR(64)  NOT NULL,
  avatar                   VARCHAR(512) NOT NULL,
  age_range                VARCHAR(10),
  sitting_hours            VARCHAR(10),
  focus_parts              JSONB,
  intensity                VARCHAR(10),
  preferred_time           VARCHAR(10),
  push_token               VARCHAR(512),
  push_channel             VARCHAR(20),
  email                    VARCHAR(254),
  created_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  last_active_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  report_cache             JSONB        DEFAULT '{}'::jsonb,
  report_cache_expires_at  TIMESTAMPTZ,
  version                  INTEGER      NOT NULL DEFAULT 0,
  deleted_at               TIMESTAMPTZ,
  -- V1.1.2 附录 E 审计字段下沉
  created_by               VARCHAR(64)  NOT NULL DEFAULT '',
  created_time             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  last_updated_time        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  last_updated_by          VARCHAR(64)  NOT NULL DEFAULT ''
);

-- ═══════════════════════════════════════════════════════════════════════
-- 1.2 reports（M2 AI 诊断报告）
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS reports (
  id                UUID           PRIMARY KEY DEFAULT uuidv7(),
  user_id           UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  photos            JSONB          NOT NULL,
  directions        JSONB          NOT NULL,
  tags              JSONB          NOT NULL,
  summary           TEXT,
  llm_model         VARCHAR(50),
  llm_cost          DECIMAL(10,4)  NOT NULL DEFAULT 0.0000,
  created_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  deleted_at        TIMESTAMPTZ,
  created_by        VARCHAR(64)    NOT NULL DEFAULT '',
  created_time      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_time TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_by   VARCHAR(64)    NOT NULL DEFAULT ''
);

-- ═══════════════════════════════════════════════════════════════════════
-- 1.3 videos（M2 全网视频库 · 公共数据）
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS videos (
  id                UUID           PRIMARY KEY DEFAULT uuidv7(),
  title             VARCHAR(256)   NOT NULL,
  source            VARCHAR(20)    NOT NULL,
  video_id          VARCHAR(128)   NOT NULL,
  url               VARCHAR(1024)  NOT NULL,
  duration_sec      INTEGER        NOT NULL,
  difficulty        INTEGER        NOT NULL,
  tags              JSONB          NOT NULL,
  thumbnail         VARCHAR(512)   NOT NULL,
  status            VARCHAR(20)    NOT NULL DEFAULT 'active',
  created_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  deleted_at        TIMESTAMPTZ,
  created_by        VARCHAR(64)    NOT NULL DEFAULT '',
  created_time      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_time TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_by   VARCHAR(64)    NOT NULL DEFAULT ''
);

-- ═══════════════════════════════════════════════════════════════════════
-- 1.4 plans（M3 21 天方案）
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS plans (
  id                UUID           PRIMARY KEY DEFAULT uuidv7(),
  user_id           UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  report_id         VARCHAR(64)    NOT NULL,  -- 兼容历史雪花 ID；V1.2 起与 reports.id 对齐
  days              JSONB          NOT NULL,
  status            VARCHAR(20)    NOT NULL DEFAULT 'active',
  started_at        DATE,
  completed_at      DATE,
  created_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  deleted_at        TIMESTAMPTZ,
  created_by        VARCHAR(64)    NOT NULL DEFAULT '',
  created_time      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_time TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_by   VARCHAR(64)    NOT NULL DEFAULT ''
);

-- ═══════════════════════════════════════════════════════════════════════
-- 1.5 checkins（M4 每日打卡）
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS checkins (
  id                UUID           PRIMARY KEY DEFAULT uuidv7(),
  user_id           UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  plan_id           VARCHAR(64)    NOT NULL,
  day               INTEGER        NOT NULL,
  video_id          VARCHAR(64)    NOT NULL,
  feeling           TEXT,
  created_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  deleted_at        TIMESTAMPTZ,
  created_by        VARCHAR(64)    NOT NULL DEFAULT '',
  created_time      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_time TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_by   VARCHAR(64)    NOT NULL DEFAULT ''
);

-- ═══════════════════════════════════════════════════════════════════════
-- 1.6 posts（M6 社区动态）
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS posts (
  id                UUID           PRIMARY KEY DEFAULT uuidv7(),
  user_id           UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  content           TEXT           NOT NULL,
  images            JSONB          DEFAULT '[]'::jsonb,
  status            VARCHAR(20)    NOT NULL DEFAULT 'pending',
  ai_comment        TEXT,
  official_comment  TEXT,
  like_count        INTEGER        NOT NULL DEFAULT 0,
  comment_count     INTEGER        NOT NULL DEFAULT 0,
  reviewed_by       UUID           REFERENCES users(id) ON DELETE SET NULL,
  reviewed_at       TIMESTAMPTZ,
  created_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  deleted_at        TIMESTAMPTZ,
  created_by        VARCHAR(64)    NOT NULL DEFAULT '',
  created_time      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_time TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_by   VARCHAR(64)    NOT NULL DEFAULT ''
);

-- ═══════════════════════════════════════════════════════════════════════
-- 1.7 agent_sessions（DEPRECATED · 读兼容到 W8）
--   注：与 ai_sessions 字段大量重叠，迁移路径详见附录 H
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS agent_sessions (
  id           UUID           PRIMARY KEY DEFAULT uuidv7(),
  user_id      UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_id   VARCHAR(128)   NOT NULL,
  messages     JSONB          NOT NULL DEFAULT '[]'::jsonb,
  context      JSONB          NOT NULL DEFAULT '{}'::jsonb,
  expires_at   TIMESTAMPTZ,
  created_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  deleted_at   TIMESTAMPTZ
);

-- ═══════════════════════════════════════════════════════════════════════
-- 1.8 feedback（V1.3 新增 · M7a/M7b/M9/M8 数据源）
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS feedback (
  id                  UUID           PRIMARY KEY DEFAULT uuidv7(),
  user_id             UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  feedback_type       VARCHAR(32)    NOT NULL,
  text_content        TEXT,
  photo_url           VARCHAR(512),
  body_part           VARCHAR(32),
  ai_ack_id           UUID,  -- 延迟 FK（ai_messages 在 §1.11 创建后由本文件末尾 ALTER TABLE 补 FK）
  deleted_at          TIMESTAMPTZ,
  created_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  created_by          VARCHAR(64)    NOT NULL DEFAULT '',
  created_time        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_time   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_by     VARCHAR(64)    NOT NULL DEFAULT ''
);

-- ═══════════════════════════════════════════════════════════════════════
-- 1.9 recall_sessions（V1.3 新增 · M8 主动回忆业务事件）
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS recall_sessions (
  id                    UUID           PRIMARY KEY DEFAULT uuidv7(),
  user_id               UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  plan_id               UUID           REFERENCES plans(id) ON DELETE SET NULL,
  trigger               VARCHAR(32)    NOT NULL,
  ai_summary            TEXT,
  ai_encourage          TEXT,
  referenced_feedbacks  JSONB          NOT NULL DEFAULT '[]'::jsonb,
  referenced_photos     JSONB          NOT NULL DEFAULT '[]'::jsonb,
  llm_cost              DECIMAL(10,4)  NOT NULL DEFAULT 0,
  safety_passed         BOOLEAN        NOT NULL DEFAULT FALSE,
  ai_session_id         UUID,  -- 延迟 FK（ai_sessions 在 §1.10 创建后由本文件末尾 ALTER TABLE 补 FK）
  created_at            TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  deleted_at            TIMESTAMPTZ,
  created_by            VARCHAR(64)    NOT NULL DEFAULT '',
  created_time          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_time     TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_by       VARCHAR(64)    NOT NULL DEFAULT ''
);

-- ═══════════════════════════════════════════════════════════════════════
-- 1.10 ai_sessions（V1.3 新增 · P03a 会话层）
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS ai_sessions (
  id                    UUID           PRIMARY KEY DEFAULT uuidv7(),
  user_id               UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  entry_card            VARCHAR(32),
  primary_intent        VARCHAR(32)    NOT NULL,
  persona_state_start   VARCHAR(32)    NOT NULL DEFAULT 'warm',
  persona_state_end     VARCHAR(32),
  plan_id               UUID           REFERENCES plans(id) ON DELETE SET NULL,
  feedback_id           UUID,  -- 延迟 FK（feedback 在 §1.8 创建后由本文件末尾 ALTER TABLE 补 FK）
  recall_session_id     UUID,  -- 延迟 FK（recall_sessions 在 §1.9 创建后由本文件末尾 ALTER TABLE 补 FK）
  message_count         INTEGER        NOT NULL DEFAULT 0,
  total_llm_cost        DECIMAL(10,4)  NOT NULL DEFAULT 0,
  user_active           BOOLEAN        NOT NULL DEFAULT TRUE,
  started_at            TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_active_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  closed_at             TIMESTAMPTZ,
  created_at            TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  created_by            VARCHAR(64)    NOT NULL DEFAULT '',
  created_time          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_time     TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_by       VARCHAR(64)    NOT NULL DEFAULT ''
);

-- ═══════════════════════════════════════════════════════════════════════
-- 1.11 ai_messages（V1.3 新增 · 会话内逐条消息）
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS ai_messages (
  id                       UUID           PRIMARY KEY DEFAULT uuidv7(),
  session_id               UUID           NOT NULL REFERENCES ai_sessions(id) ON DELETE CASCADE,
  seq                      INTEGER        NOT NULL,
  role                     VARCHAR(16)    NOT NULL,
  content                  TEXT           NOT NULL,
  context_photos           JSONB,
  referenced_feedback_ids  UUID[]         NOT NULL DEFAULT '{}',
  referenced_video_ids     UUID[]         NOT NULL DEFAULT '{}',
  trigger                  VARCHAR(32),
  intent                   VARCHAR(32),
  llm_cost                 DECIMAL(10,4),
  llm_model                VARCHAR(64),
  llm_latency_ms           INTEGER,
  safety_passed            BOOLEAN,
  safety_violations        JSONB,
  token_count              INTEGER        NOT NULL DEFAULT 0,
  created_at               TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  created_by               VARCHAR(64)    NOT NULL DEFAULT '',
  created_time             TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_time        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_by          VARCHAR(64)    NOT NULL DEFAULT ''
);

-- 现在补回 §1.8 / §1.9 / §1.10 暂未加的 FK（所有表已存在，FK 引用合法）
ALTER TABLE feedback
  DROP CONSTRAINT IF EXISTS fk_feedback_ai_ack;
ALTER TABLE feedback
  ADD  CONSTRAINT fk_feedback_ai_ack
    FOREIGN KEY (ai_ack_id) REFERENCES ai_messages(id) ON DELETE SET NULL;

ALTER TABLE recall_sessions
  DROP CONSTRAINT IF EXISTS fk_recall_ai_session;
ALTER TABLE recall_sessions
  ADD  CONSTRAINT fk_recall_ai_session
    FOREIGN KEY (ai_session_id) REFERENCES ai_sessions(id) ON DELETE SET NULL;

ALTER TABLE ai_sessions
  DROP CONSTRAINT IF EXISTS fk_ai_session_feedback;
ALTER TABLE ai_sessions
  ADD  CONSTRAINT fk_ai_session_feedback
    FOREIGN KEY (feedback_id) REFERENCES feedback(id) ON DELETE SET NULL;

ALTER TABLE ai_sessions
  DROP CONSTRAINT IF EXISTS fk_ai_session_recall;
ALTER TABLE ai_sessions
  ADD  CONSTRAINT fk_ai_session_recall
    FOREIGN KEY (recall_session_id) REFERENCES recall_sessions(id) ON DELETE SET NULL;

COMMIT;