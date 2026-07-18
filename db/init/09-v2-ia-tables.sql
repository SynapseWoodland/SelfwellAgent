-- =============================================================================
-- 09-v2-ia-tables.sql · V2 IA PR-2 4 张新表（UUID + CHECK + FK CASCADE + 注释）
--   职责：补齐 V2 IA 后端骨架 4 张业务表：
--     ① user_badges                  · 勋章体系（6 类枚举）
--     ② user_notification_prefs      · 通知偏好（key→value JSONB map，复合 PK）
--     ③ account_deletion_requests    · 账号注销（7 天冷静期状态机）
--     ④ user_self_tags               · 自标签（4 类枚举）
--   依据：plans/v2-unified-parent.md §2.2 + IA V2.2 §2A.2 + plans/v2-IA-pr-internal.md §PR-2
--   真源对照：app/db/models/{user_badge,user_notification_pref,account_deletion_request,user_self_tag}.py
--   执行：alembic 与 docker-entrypoint-initdb.d 各一份，1:1 DDL
--
--   设计原则（与 db/init/00-08 保持 100% 一致）：
--     - PK / FK 全部使用 UUID + uuidv7()（PG 18 原生；PG 15 走 00-extensions.sql）
--     - 字段长度与 ORM + data-dictionary 一致（VARCHAR(32/64) / DECIMAL(10,4)）
--     - NOT NULL 字段配 DEFAULT；枚举值用 CHECK 锁（与 03-checks.sql 风格对齐）
--     - FK ON DELETE CASCADE（软删除走 deleted_at；硬删触发器在 04-triggers.sql）
--     - 全部二级索引在文件末尾集中声明（不嵌入 CREATE TABLE 内）
--     - 全部字段注释（与 07-table-comments.sql 风格对齐；中文 COMMENT）
--
--   注意：本脚本幂等性（CREATE TABLE IF NOT EXISTS + DROP CONSTRAINT IF EXISTS）
--     适合 docker-entrypoint-initdb.d 一次部署；alembic 等价脚本 0007_add_v2_ia_tables.py
-- =============================================================================

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════
-- 1.1 user_badges（V2 IA · 勋章体系 · §2A.2.1）
--   6 类枚举：first_checkin / streak_7 / streak_14 / streak_21 /
--             first_feedback / first_album_photo
--   唯一约束：(user_id, code) 一人一码一行
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS user_badges (
  id                  UUID           PRIMARY KEY DEFAULT uuidv7(),
  user_id             UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  code                VARCHAR(64)    NOT NULL,
  progress            INTEGER        NOT NULL DEFAULT 0,
  target              INTEGER        NOT NULL DEFAULT 0,
  unlocked_at         TIMESTAMPTZ,
  created_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  deleted_at          TIMESTAMPTZ,
  created_by          VARCHAR(64)    NOT NULL DEFAULT '',
  created_time        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_time   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_by     VARCHAR(64)    NOT NULL DEFAULT ''
);

ALTER TABLE user_badges DROP CONSTRAINT IF EXISTS chk_user_badges_code;
ALTER TABLE user_badges ADD  CONSTRAINT chk_user_badges_code
  CHECK (code IN ('first_checkin','streak_7','streak_14','streak_21','first_feedback','first_album_photo'));

ALTER TABLE user_badges DROP CONSTRAINT IF EXISTS chk_user_badges_progress;
ALTER TABLE user_badges ADD  CONSTRAINT chk_user_badges_progress
  CHECK (progress >= 0 AND progress <= target);

ALTER TABLE user_badges DROP CONSTRAINT IF EXISTS chk_user_badges_target;
ALTER TABLE user_badges ADD  CONSTRAINT chk_user_badges_target
  CHECK (target >= 0);

ALTER TABLE user_badges DROP CONSTRAINT IF EXISTS chk_user_badges_unlocked_consistency;
ALTER TABLE user_badges ADD  CONSTRAINT chk_user_badges_unlocked_consistency
  CHECK (
    (unlocked_at IS NULL AND progress < target)
    OR (unlocked_at IS NOT NULL AND progress >= target)
  );

ALTER TABLE user_badges DROP CONSTRAINT IF EXISTS uq_user_badges_user_code;
ALTER TABLE user_badges ADD  CONSTRAINT uq_user_badges_user_code UNIQUE (user_id, code);

-- ═══════════════════════════════════════════════════════════════════════
-- 1.2 user_notification_prefs（V2 IA · 通知偏好 key→value map · §2A.2.2）
--   6 类 pref_key：daily_checkin / weekly_recall / feedback_ack /
--                  plan_milestone / album_unlock / hug_card_ready
--   复合主键：(user_id, pref_key) 一人一个偏好 key 只存一行
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS user_notification_prefs (
  user_id             UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  pref_key            VARCHAR(64)    NOT NULL,
  pref_value          JSONB          NOT NULL,
  updated_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  created_by          VARCHAR(64)    NOT NULL DEFAULT '',
  created_time        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_time   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_by     VARCHAR(64)    NOT NULL DEFAULT '',
  PRIMARY KEY (user_id, pref_key)
);

ALTER TABLE user_notification_prefs DROP CONSTRAINT IF EXISTS chk_user_notif_pref_key;
ALTER TABLE user_notification_prefs ADD  CONSTRAINT chk_user_notif_pref_key
  CHECK (pref_key IN (
    'daily_checkin','weekly_recall','feedback_ack',
    'plan_milestone','album_unlock','hug_card_ready'
  ));

ALTER TABLE user_notification_prefs DROP CONSTRAINT IF EXISTS chk_user_notif_pref_value_object;
ALTER TABLE user_notification_prefs ADD  CONSTRAINT chk_user_notif_pref_value_object
  CHECK (jsonb_typeof(pref_value) = 'object');

-- ═══════════════════════════════════════════════════════════════════════
-- 1.3 account_deletion_requests（V2 IA · 账号注销 · 7 天冷静期状态机 · §2A.2.3）
--   4 状态：pending_cool_down / confirmed / cancelled / executed
--   反向确认短语 confirm_phrase（6 字符 hex），用户必须手输避免误点
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS account_deletion_requests (
  id                  UUID           PRIMARY KEY DEFAULT uuidv7(),
  user_id             UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status              VARCHAR(16)    NOT NULL DEFAULT 'pending_cool_down',
  confirm_phrase      VARCHAR(64)    NOT NULL,
  cool_down_until     TIMESTAMPTZ    NOT NULL,
  created_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  deleted_at          TIMESTAMPTZ,
  created_by          VARCHAR(64)    NOT NULL DEFAULT '',
  created_time        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_time   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_by     VARCHAR(64)    NOT NULL DEFAULT ''
);

ALTER TABLE account_deletion_requests DROP CONSTRAINT IF EXISTS chk_account_deletion_status;
ALTER TABLE account_deletion_requests ADD  CONSTRAINT chk_account_deletion_status
  CHECK (status IN ('pending_cool_down','confirmed','cancelled','executed'));

ALTER TABLE account_deletion_requests DROP CONSTRAINT IF EXISTS chk_account_deletion_confirm_phrase_len;
ALTER TABLE account_deletion_requests ADD  CONSTRAINT chk_account_deletion_confirm_phrase_len
  CHECK (length(confirm_phrase) BETWEEN 4 AND 32);

ALTER TABLE account_deletion_requests DROP CONSTRAINT IF EXISTS chk_account_deletion_cool_down_future;
ALTER TABLE account_deletion_requests ADD  CONSTRAINT chk_account_deletion_cool_down_future
  CHECK (cool_down_until > created_at);

ALTER TABLE account_deletion_requests DROP CONSTRAINT IF EXISTS chk_account_deletion_state_consistency;
ALTER TABLE account_deletion_requests ADD  CONSTRAINT chk_account_deletion_state_consistency
  CHECK (
    (status IN ('pending_cool_down','confirmed') AND deleted_at IS NULL)
    OR (status IN ('cancelled','executed'))
  );

-- ═══════════════════════════════════════════════════════════════════════
-- 1.4 user_self_tags（V2 IA · 自标签 · §2A.2.4）
--   4 类枚举：body_part / concern / lifestyle / intensity
--   2 来源枚举：manual / inferred_from_feedback
--   唯一约束：(user_id, tag_category, tag_value) 一人同类同值只一行
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS user_self_tags (
  id                  UUID           PRIMARY KEY DEFAULT uuidv7(),
  user_id             UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tag_category        VARCHAR(32)    NOT NULL,
  tag_value           VARCHAR(64)    NOT NULL,
  is_selected         BOOLEAN        NOT NULL DEFAULT TRUE,
  source              VARCHAR(16)    NOT NULL DEFAULT 'manual',
  created_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  deleted_at          TIMESTAMPTZ,
  created_by          VARCHAR(64)    NOT NULL DEFAULT '',
  created_time        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_time   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_updated_by     VARCHAR(64)    NOT NULL DEFAULT ''
);

ALTER TABLE user_self_tags DROP CONSTRAINT IF EXISTS chk_user_self_tags_category;
ALTER TABLE user_self_tags ADD  CONSTRAINT chk_user_self_tags_category
  CHECK (tag_category IN ('body_part','concern','lifestyle','intensity'));

ALTER TABLE user_self_tags DROP CONSTRAINT IF EXISTS chk_user_self_tags_source;
ALTER TABLE user_self_tags ADD  CONSTRAINT chk_user_self_tags_source
  CHECK (source IN ('manual','inferred_from_feedback'));

ALTER TABLE user_self_tags DROP CONSTRAINT IF EXISTS uq_user_self_tags_user_category_value;
ALTER TABLE user_self_tags ADD  CONSTRAINT uq_user_self_tags_user_category_value
  UNIQUE (user_id, tag_category, tag_value);

COMMIT;


-- =============================================================================
-- 索引段（与 02-indexes.sql 风格一致：CREATE INDEX IF NOT EXISTS）
-- =============================================================================
BEGIN;

-- ═══════════════════════════════════════════════════════════════════════
-- 2.1 user_badges
--   PRIMARY 命中：UNIQUE(user_id, code) 同时承担 user_id 单列查询
--   代码枚举查询：code（运营后台/统计）
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_user_badges_user_id
  ON user_badges(user_id);
CREATE INDEX IF NOT EXISTS idx_user_badges_code
  ON user_badges(code);
CREATE INDEX IF NOT EXISTS idx_user_badges_user_unlocked
  ON user_badges(user_id, unlocked_at DESC) WHERE deleted_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- 2.2 user_notification_prefs
--   复合 PK (user_id, pref_key) 已覆盖热查询；用户维度不冗余建索引
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_user_notification_prefs_user_id
  ON user_notification_prefs(user_id);

-- ═══════════════════════════════════════════════════════════════════════
-- 2.3 account_deletion_requests
--   状态机扫表：cron job 找 pending_cool_down / confirmed 中 cool_down_until 已过的行
--   复合索引 (status, cool_down_until) 让 cron 一次命中
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_account_deletion_status_cool_down_until
  ON account_deletion_requests(status, cool_down_until)
  WHERE status IN ('pending_cool_down','confirmed');
CREATE INDEX IF NOT EXISTS idx_account_deletion_user_id
  ON account_deletion_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_account_deletion_deleted_at
  ON account_deletion_requests(deleted_at) WHERE deleted_at IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- 2.4 user_self_tags
--   档案页高频：user_id + category + is_selected=TRUE 拉取
--   部分索引跳过未选中标签，减少 50%+ 索引体积
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_user_self_tags_user_id
  ON user_self_tags(user_id);
CREATE INDEX IF NOT EXISTS idx_user_self_tags_user_selected
  ON user_self_tags(user_id, is_selected)
  WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_user_self_tags_user_category
  ON user_self_tags(user_id, tag_category)
  WHERE deleted_at IS NULL;
-- tag_value 是受 CHECK 约束的有限枚举字符串，热查询为按值等值 / IN 反查
-- 典型 SQL：WHERE tag_value = 'xxx' / WHERE tag_value = ANY($1::varchar[])
-- 这种场景 B-tree 索引足够；GIN 缺少 varchar 默认 opclass（pg 默认只支持
-- text/bytea/jsonb/array），且当前没有模糊匹配 / 相似度查询需求，
-- 故不建 GIN；后续若引入 ILIKE / 相似度排序，再单独加
--   CREATE EXTENSION pg_trgm;
--   CREATE INDEX ... USING GIN (tag_value gin_trgm_ops) ...
CREATE INDEX IF NOT EXISTS idx_user_self_tags_value
  ON user_self_tags(tag_value)
  WHERE deleted_at IS NULL;

COMMIT;


-- =============================================================================
-- 字段注释段（与 07-table-comments.sql 风格一致：COMMENT ON TABLE + COMMENT ON COLUMN）
-- =============================================================================
BEGIN;

-- ═══════════════════════════════════════════════════════════════════════
-- 1. user_badges · IA V2.2 §2A.2.1
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE user_badges IS '用户勋章（V2 IA · PR-2）；6 类枚举：first_checkin / streak_7 / streak_14 / streak_21 / first_feedback / first_album_photo';

COMMENT ON COLUMN user_badges.id                  IS '主键（PG 18 原生 uuidv7()；PG 15 需 uuid-ossp 扩展）';
COMMENT ON COLUMN user_badges.user_id             IS '关联 users.id（FK ON DELETE CASCADE；CASCADE 走硬删）';
COMMENT ON COLUMN user_badges.code                IS '6 类枚举：first_checkin / streak_7 / streak_14 / streak_21 / first_feedback / first_album_photo（CHECK 约束；UNIQUE 与 user_id 联合）';
COMMENT ON COLUMN user_badges.progress            IS '当前进度 0..target（CHECK 约束；自动解锁时 progress >= target）';
COMMENT ON COLUMN user_badges.target              IS '达标阈值（CHECK：>= 0；first create 时必填）';
COMMENT ON COLUMN user_badges.unlocked_at         IS '解锁时间（NULL = 未解锁；CHECK 与 progress 一致性锁：unlocked_at IS NULL 时 progress < target）';
COMMENT ON COLUMN user_badges.created_at          IS '创建时间';
COMMENT ON COLUMN user_badges.deleted_at          IS '软删除时间（NULL = 未删除；查询永远过滤 NULL）';
COMMENT ON COLUMN user_badges.created_by          IS '创建人';
COMMENT ON COLUMN user_badges.created_time        IS '创建时间（与 created_at 语义合并）';
COMMENT ON COLUMN user_badges.last_updated_time   IS '最后更新时间';
COMMENT ON COLUMN user_badges.last_updated_by     IS '最后更新人';

-- ═══════════════════════════════════════════════════════════════════════
-- 2. user_notification_prefs · IA V2.2 §2A.2.2
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE user_notification_prefs IS '用户通知偏好（V2 IA · PR-2）；6 类 pref_key + JSONB value；复合主键 (user_id, pref_key)';

COMMENT ON COLUMN user_notification_prefs.user_id             IS '关联 users.id（FK ON DELETE CASCADE；PK 之一）';
COMMENT ON COLUMN user_notification_prefs.pref_key            IS '6 类偏好 key：daily_checkin / weekly_recall / feedback_ack / plan_milestone / album_unlock / hug_card_ready（CHECK 约束；PK 之一）';
COMMENT ON COLUMN user_notification_prefs.pref_value          IS '偏好值（JSONB object；CHECK：jsonb_typeof=object；典型形如 {"enabled": true, "time": "08:00"}）';
COMMENT ON COLUMN user_notification_prefs.updated_at          IS '偏好最后更新时间';
COMMENT ON COLUMN user_notification_prefs.created_by          IS '创建人';
COMMENT ON COLUMN user_notification_prefs.created_time        IS '创建时间（与 created_at 语义合并）';
COMMENT ON COLUMN user_notification_prefs.last_updated_time   IS '最后更新时间';
COMMENT ON COLUMN user_notification_prefs.last_updated_by     IS '最后更新人';

-- ═══════════════════════════════════════════════════════════════════════
-- 3. account_deletion_requests · IA V2.2 §2A.2.3
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE account_deletion_requests IS '账号注销请求（V2 IA · PR-2）；4 状态机：pending_cool_down / confirmed / cancelled / executed；7 天冷静期（COOL_DOWN_DAYS=7）';

COMMENT ON COLUMN account_deletion_requests.id                  IS '主键（PG 18 原生 uuidv7()；PG 15 需 uuid-ossp 扩展）';
COMMENT ON COLUMN account_deletion_requests.user_id             IS '关联 users.id（FK ON DELETE CASCADE）';
COMMENT ON COLUMN account_deletion_requests.status              IS '4 状态枚举：pending_cool_down / confirmed / cancelled / executed（CHECK 约束；默认 pending_cool_down）';
COMMENT ON COLUMN account_deletion_requests.confirm_phrase      IS '反向确认短语（6 字符 hex；CHECK：长度 4~32；用户必须在前端手输才能 confirm，避免误点）';
COMMENT ON COLUMN account_deletion_requests.cool_down_until     IS '冷静期截止时间（CHECK：> created_at；V2 默认 7 天，cron job 到点执行）';
COMMENT ON COLUMN account_deletion_requests.created_at          IS '请求创建时间';
COMMENT ON COLUMN account_deletion_requests.updated_at          IS '最后更新时间（confirm/cancel/execute 时回写）';
COMMENT ON COLUMN account_deletion_requests.deleted_at          IS '软删除时间（NULL = 未删除；cancelled/executed 后允许保留审计）';
COMMENT ON COLUMN account_deletion_requests.created_by          IS '创建人';
COMMENT ON COLUMN account_deletion_requests.created_time        IS '创建时间（与 created_at 语义合并）';
COMMENT ON COLUMN account_deletion_requests.last_updated_time   IS '最后更新时间';
COMMENT ON COLUMN account_deletion_requests.last_updated_by     IS '最后更新人';

-- ═══════════════════════════════════════════════════════════════════════
-- 4. user_self_tags · IA V2.2 §2A.2.4
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE user_self_tags IS '用户自标签（V2 IA · PR-2）；4 类枚举：body_part / concern / lifestyle / intensity；唯一约束 (user_id, tag_category, tag_value)';

COMMENT ON COLUMN user_self_tags.id                  IS '主键（PG 18 原生 uuidv7()；PG 15 需 uuid-ossp 扩展）';
COMMENT ON COLUMN user_self_tags.user_id             IS '关联 users.id（FK ON DELETE CASCADE）';
COMMENT ON COLUMN user_self_tags.tag_category        IS '4 类枚举：body_part / concern / lifestyle / intensity（CHECK 约束）';
COMMENT ON COLUMN user_self_tags.tag_value           IS '标签值（VARCHAR(64)）；具体值待 TDS-M 拍板；GIN 索引加速值搜索';
COMMENT ON COLUMN user_self_tags.is_selected         IS '是否在 profile 页面显示（boolean，默认 TRUE；profile 渲染时 WHERE is_selected=TRUE 走部分索引）';
COMMENT ON COLUMN user_self_tags.source              IS '标签来源：manual（用户主动加）/ inferred_from_feedback（AI 从 feedback 推断）（CHECK 约束；默认 manual）';
COMMENT ON COLUMN user_self_tags.created_at          IS '创建时间';
COMMENT ON COLUMN user_self_tags.deleted_at          IS '软删除时间（NULL = 未删除）';
COMMENT ON COLUMN user_self_tags.created_by          IS '创建人';
COMMENT ON COLUMN user_self_tags.created_time        IS '创建时间（与 created_at 语义合并）';
COMMENT ON COLUMN user_self_tags.last_updated_time   IS '最后更新时间';
COMMENT ON COLUMN user_self_tags.last_updated_by     IS '最后更新人';

COMMIT;


-- =============================================================================
-- 验证段（执行完后可手动跑一遍）
-- =============================================================================

-- 验证 1：4 张新表全部存在
--   SELECT tablename FROM pg_tables
--   WHERE schemaname='public' AND tablename IN
--     ('user_badges','user_notification_prefs','account_deletion_requests','user_self_tags')
--   ORDER BY tablename;
--   → 应返回 4 行

-- 验证 2：CHECK 约束数量（应 = 11）
--   user_badges              5 (code/progress/target/unlocked_consistency/uq)
--   user_notification_prefs  2 (pref_key/pref_value_object)
--   account_deletion_reqs    5 (status/confirm_phrase_len/cool_down_future/state_consistency)
--   user_self_tags           4 (category/source/uq/include PK)
--   实际：CHECK + UNIQUE 合计 11（uq_* 计入）

-- 验证 3：FK 完整性（应 = 4 条 user_id → users.id CASCADE）
--   SELECT count(*) FROM pg_constraint
--   WHERE contype='f' AND conrelid IN (
--     'user_badges'::regclass,'user_notification_prefs'::regclass,
--     'account_deletion_requests'::regclass,'user_self_tags'::regclass
--   );

-- 验证 4：COMMENT 覆盖率（应 = 100%）
--   SELECT count(*) AS commented_cols FROM (
--     SELECT c.table_name, c.column_name
--     FROM information_schema.columns c
--     WHERE table_schema='public' AND c.table_name IN
--       ('user_badges','user_notification_prefs','account_deletion_requests','user_self_tags')
--       AND col_description((c.table_name)::regclass, c.ordinal_position) IS NOT NULL
--   ) t;
