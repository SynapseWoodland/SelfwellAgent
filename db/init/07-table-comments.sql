-- =============================================================================
-- 07-table-comments.sql · 11 张业务表 + 字段注释
--   职责：给 11 张业务表的每一列补充 COMMENT ON COLUMN；
--         字段口径 100% 对齐 docs/data/data-dictionary.md。
--   依据：data-dictionary.md §1-§8 + 附录 D（V1.3 4 张新表）+ §6.1 audit_logs(已废)
--   表清单（11 张）：
--     旧 7 张：users / reports / videos / plans / checkins / posts / agent_sessions(DEPRECATED)
--     新 4 张：feedback / recall_sessions / ai_sessions / ai_messages
--   幂等性：COMMENT ON COLUMN 会覆盖原值，可重复执行。
--   注意：06-ddl-update-0707.sql 给 users 加了 status 字段，本脚本一并补注释。
-- =============================================================================

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════
-- 1. users（M1 主档）· data-dictionary.md §1.2
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE users IS '用户主档，存储用户身份、档案、推送配置（M1 起）';

COMMENT ON COLUMN users.id                       IS '主键（PG 18 原生 uuidv7()；PG 15 需 uuid-ossp 扩展）；时序有序，避免 B-tree fragmentation';
COMMENT ON COLUMN users.unionid                  IS '微信开放平台唯一标识（隐私级别：高；UNIQUE）';
COMMENT ON COLUMN users.openid_mp                IS '小程序 openid（仅小程序端；隐私级别：高；部分索引）';
COMMENT ON COLUMN users.openid_app               IS 'APP openid（仅 APP 端；隐私级别：高；部分索引）';
COMMENT ON COLUMN users.phone                    IS '手机号（可选；隐私级别：高）';
COMMENT ON COLUMN users.platform                 IS '登录平台（枚举：wx_mp / ios / android / harmony；索引）';
COMMENT ON COLUMN users.device_id                IS '设备标识（推送反查用，部分索引跳过 NULL；隐私级别：中）';
COMMENT ON COLUMN users.nickname                 IS '用户昵称（隐私级别：中）';
COMMENT ON COLUMN users.avatar                   IS '头像 URL（隐私级别：中）';
COMMENT ON COLUMN users.age_range                IS '年龄段（枚举：18-22 / 23-28 / 29-35 / 36-45 / 45+；M1.2 引导填写，可空；隐私级别：中）';
COMMENT ON COLUMN users.sitting_hours            IS '每日久坐时长（枚举：<4h / 4-8h / 8-12h / 12h+；M1.2 引导填写，可空；隐私级别：中）';
COMMENT ON COLUMN users.focus_parts              IS '关注部位多选（JSONB；枚举值：脸/头/肩颈/腰/腿/整体气色；M1.2 引导填写，可空；隐私级别：中）';
COMMENT ON COLUMN users.intensity                IS '训练强度偏好（枚举：轻柔 / 适中 / 进阶；M1.2 引导填写，可空；隐私级别：中）';
COMMENT ON COLUMN users.preferred_time           IS '打卡时间偏好（枚举：早 / 中 / 晚 / 不固定；M1.2 引导填写，可空；隐私级别：中）';
COMMENT ON COLUMN users.push_token               IS '推送 Token（隐私级别：高）';
COMMENT ON COLUMN users.push_channel             IS '推送通道（枚举：wx_subscribe / apns / fcm / hms / email；隐私级别：中）';
COMMENT ON COLUMN users.email                    IS '邮件兜底地址（RFC 5321 上限 254 字符；隐私级别：高；部分索引）';
COMMENT ON COLUMN users.created_at               IS '注册时间';
COMMENT ON COLUMN users.last_active_at           IS '最后活跃时间（索引）';
COMMENT ON COLUMN users.report_cache             IS '诊断报告缓存（JSONB；7 天复用，避免重复 AI 调用；隐私级别：中）';
COMMENT ON COLUMN users.report_cache_expires_at  IS 'report_cache 过期时间（7 天 TTL；触发器 ① 自动维护；部分索引）';
COMMENT ON COLUMN users.version                  IS '乐观锁版本号（AI 推荐更新场景）';
COMMENT ON COLUMN users.deleted_at               IS '软删除时间（NULL = 未删除；GDPR 90 天后物理清理；部分索引）';
COMMENT ON COLUMN users.created_by               IS '创建人（user_id 或 system/ai/<worker_id>；匿名用空串）';
COMMENT ON COLUMN users.created_time             IS '创建时间（与 created_at 语义合并）';
COMMENT ON COLUMN users.last_updated_time        IS '最后更新时间';
COMMENT ON COLUMN users.last_updated_by          IS '最后更新人（同 created_by 编码）';
COMMENT ON COLUMN users.status                   IS '用户状态（枚举：draft / active / churned；06-ddl-update-0707.sql 新增；部分索引）';

-- ═══════════════════════════════════════════════════════════════════════
-- 2. reports（M2 AI 诊断报告）· data-dictionary.md §2.2
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE reports IS 'AI 诊断报告，存储诊断结果与 LLM 调用费用（M2）；触发器 ② 自动写一份到 users.report_cache';

COMMENT ON COLUMN reports.id                IS '主键（PG 18 原生 uuidv7()；PG 15 需 uuid-ossp 扩展）；时序有序，避免 B-tree fragmentation';
COMMENT ON COLUMN reports.user_id           IS '关联 users.id（FK ON DELETE CASCADE）';
COMMENT ON COLUMN reports.photos            IS '3 张 CDN URL（JSONB 数组；隐私级别：高）';
COMMENT ON COLUMN reports.directions        IS '3-5 条改善方向（JSONB 数组）';
COMMENT ON COLUMN reports.tags              IS '7-14 个诊断标签（JSONB 数组；GIN 全文检索）';
COMMENT ON COLUMN reports.summary           IS 'AI 诊断总结文案（≤ 500 字；TEXT 避免 VARCHAR 中文截断）';
COMMENT ON COLUMN reports.llm_model         IS 'LLM 模型标识（如 qwen-vl-max / gpt-4o）';
COMMENT ON COLUMN reports.llm_cost          IS 'LLM 调用成本（元，DECIMAL(10,4)，上限 999999.9999，与 recall_sessions/ai_messages 统一精度）';
COMMENT ON COLUMN reports.created_at        IS '诊断时间（INDEX DESC）';
COMMENT ON COLUMN reports.deleted_at        IS '软删除时间（NULL = 未删除；部分索引）';
COMMENT ON COLUMN reports.created_by        IS '创建人';
COMMENT ON COLUMN reports.created_time      IS '创建时间（与 created_at 语义合并）';
COMMENT ON COLUMN reports.last_updated_time IS '最后更新时间';
COMMENT ON COLUMN reports.last_updated_by   IS '最后更新人';

-- ═══════════════════════════════════════════════════════════════════════
-- 3. videos（M2 全网视频库 · 公共数据）· data-dictionary.md §3.2
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE videos IS '跟练视频库，存储全网聚合视频元数据（M2 · 公共数据，不参与用户软删除联级）';

COMMENT ON COLUMN videos.id                IS '主键（视频唯一标识；PG 18 原生 uuidv7()；PG 15 需 uuid-ossp 扩展）';
COMMENT ON COLUMN videos.title             IS '视频标题（VARCHAR(256)；PG 默认 UTF8：1 个汉字 = 1 字符）';
COMMENT ON COLUMN videos.source            IS '视频来源（枚举：bilibili / xiaohongshu / douyin / youtube；CHECK 不加，未来扩展）';
COMMENT ON COLUMN videos.video_id          IS '原始平台视频 ID';
COMMENT ON COLUMN videos.url               IS '原始视频 URL（VARCHAR(1024)）';
COMMENT ON COLUMN videos.duration_sec      IS '视频时长（秒；CHECK：> 0 且 ≤ 3600）';
COMMENT ON COLUMN videos.difficulty        IS '难度系数（CHECK：1-5）';
COMMENT ON COLUMN videos.tags              IS '标签数组（JSONB；GIN 全文检索）';
COMMENT ON COLUMN videos.thumbnail         IS '缩略图 CDN URL';
COMMENT ON COLUMN videos.status            IS '上架状态（枚举：active / inactive；CHECK；索引）';
COMMENT ON COLUMN videos.created_at        IS '入库时间（INDEX DESC）';
COMMENT ON COLUMN videos.updated_at        IS '元数据更新时间（重爬/修订触发；与 last_updated_time 联动）';
COMMENT ON COLUMN videos.deleted_at        IS '软删除时间（公共数据，留字段但 §2 不建 partial index）';
COMMENT ON COLUMN videos.created_by        IS '创建人';
COMMENT ON COLUMN videos.created_time      IS '创建时间（与 created_at 语义合并）';
COMMENT ON COLUMN videos.last_updated_time IS '最后更新时间';
COMMENT ON COLUMN videos.last_updated_by   IS '最后更新人';

-- ═══════════════════════════════════════════════════════════════════════
-- 4. plans（M3 21 天方案）· data-dictionary.md §4.2
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE plans IS '21 天打卡方案，存储每日任务映射（M3）；CHECK：completed_at >= started_at';

COMMENT ON COLUMN plans.id                IS '方案唯一标识（PG 18 原生 uuidv7()；PG 15 需 uuid-ossp 扩展）';
COMMENT ON COLUMN plans.user_id           IS '关联 users.id（FK ON DELETE CASCADE）';
COMMENT ON COLUMN plans.report_id         IS '关联 reports.id（VARCHAR(64) 兼容历史雪花 ID；V1.2 起与 reports.id 对齐）';
COMMENT ON COLUMN plans.days              IS '21 天每日映射（JSONB 数组；结构：[{day, video_id, phase}, ...]）';
COMMENT ON COLUMN plans.status            IS '方案状态（枚举：active / completed / abandoned；CHECK；部分索引 WHERE status=active）';
COMMENT ON COLUMN plans.started_at        IS '方案开始日期（M3 用户首日打卡时回填；DATE 类型）';
COMMENT ON COLUMN plans.completed_at      IS '方案完成日期（21 天全部打卡后回填；DATE 类型）';
COMMENT ON COLUMN plans.created_at        IS '创建时间（INDEX DESC）';
COMMENT ON COLUMN plans.deleted_at        IS '软删除时间（NULL = 未删除；部分索引）';
COMMENT ON COLUMN plans.created_by        IS '创建人';
COMMENT ON COLUMN plans.created_time      IS '创建时间（与 created_at 语义合并）';
COMMENT ON COLUMN plans.last_updated_time IS '最后更新时间';
COMMENT ON COLUMN plans.last_updated_by   IS '最后更新人';

-- ═══════════════════════════════════════════════════════════════════════
-- 5. checkins（M4 每日打卡）· data-dictionary.md §5.2
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE checkins IS '每日打卡记录（M4）；UNIQUE(user_id, plan_id, day) 防重复打卡；MVP 21 天方案无 day CHECK 以便后续 30/90 天扩展';

COMMENT ON COLUMN checkins.id                IS '打卡记录唯一标识（PG 18 原生 uuidv7()；PG 15 需 uuid-ossp 扩展）';
COMMENT ON COLUMN checkins.user_id           IS '关联 users.id（FK ON DELETE CASCADE）';
COMMENT ON COLUMN checkins.plan_id           IS '关联 plans.id（VARCHAR(64) 兼容历史雪花 ID）';
COMMENT ON COLUMN checkins.day               IS '方案第几天（MVP 21 天方案；其它天的抱抱卡也走 day；不加 CHECK）';
COMMENT ON COLUMN checkins.video_id          IS '完成的视频 ID（FK → videos.id；VARCHAR(64)）';
COMMENT ON COLUMN checkins.feeling           IS '打卡感想（≤ 200 字；TEXT 避免中文 VARCHAR 字节数限制）';
COMMENT ON COLUMN checkins.created_at        IS '打卡时间（INDEX DESC）';
COMMENT ON COLUMN checkins.deleted_at        IS '软删除时间（NULL = 未删除；部分索引）';
COMMENT ON COLUMN checkins.created_by        IS '创建人';
COMMENT ON COLUMN checkins.created_time      IS '创建时间（与 created_at 语义合并）';
COMMENT ON COLUMN checkins.last_updated_time IS '最后更新时间';
COMMENT ON COLUMN checkins.last_updated_by   IS '最后更新人';

-- ═══════════════════════════════════════════════════════════════════════
-- 6. posts（M6 社区动态）· data-dictionary.md §6.2
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE posts IS '社区动态，UGC 内容发布（M6）；CHECK：reviewed_by 与 reviewed_at 一致性 + images ≤ 9 张';

COMMENT ON COLUMN posts.id                IS '帖子唯一标识（PG 18 原生 uuidv7()；PG 15 需 uuid-ossp 扩展）';
COMMENT ON COLUMN posts.user_id           IS '关联 users.id（FK ON DELETE CASCADE）';
COMMENT ON COLUMN posts.content           IS '动态内容（≤ 200 字；TEXT 避免 VARCHAR(200) 中文仅 67 字问题）';
COMMENT ON COLUMN posts.images            IS '≤ 9 张图片 CDN URL（JSONB 数组；CHECK：jsonb_array_length ≤ 9；隐私级别：高）';
COMMENT ON COLUMN posts.status            IS '审核状态（枚举：pending / approved / rejected；CHECK；部分索引 WHERE status=approved）';
COMMENT ON COLUMN posts.ai_comment        IS 'AI 暖心评论（TEXT 避免 VARCHAR(256) 中文 85 字过短）';
COMMENT ON COLUMN posts.official_comment  IS '官方精选评论';
COMMENT ON COLUMN posts.like_count        IS '点赞数（M6 社区核心功能，"最热" Tab 排序）';
COMMENT ON COLUMN posts.comment_count     IS '评论数（M6 社区核心功能，"最热" Tab 排序）';
COMMENT ON COLUMN posts.reviewed_by       IS '审核人（FK → users.id ON DELETE SET NULL；与 reviewed_at 必须同步 NULL/非 NULL）';
COMMENT ON COLUMN posts.reviewed_at       IS '审核时间';
COMMENT ON COLUMN posts.created_at        IS '发布时间（INDEX DESC）';
COMMENT ON COLUMN posts.deleted_at        IS '软删除时间（NULL = 未删除；部分索引）';
COMMENT ON COLUMN posts.created_by        IS '创建人';
COMMENT ON COLUMN posts.created_time      IS '创建时间（与 created_at 语义合并）';
COMMENT ON COLUMN posts.last_updated_time IS '最后更新时间';
COMMENT ON COLUMN posts.last_updated_by   IS '最后更新人';

-- ═══════════════════════════════════════════════════════════════════════
-- 7. agent_sessions（DEPRECATED · 读兼容到 W8）· data-dictionary.md §7.2 + 附录 H
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE agent_sessions IS 'AI 对话会话（DEPRECATED · V1.3 起被 ai_sessions 替代；保留读兼容到 W8，之后改 VIEW 然后 DROP）';

COMMENT ON COLUMN agent_sessions.id          IS '主键（PG 18 原生 uuidv7()；PG 15 需 uuid-ossp 扩展）';
COMMENT ON COLUMN agent_sessions.user_id     IS '关联 users.id（FK ON DELETE CASCADE）';
COMMENT ON COLUMN agent_sessions.session_id  IS '会话业务 ID（按小时分桶：{user_id}:{时间整点}；UNIQUE 与 user_id 联合）';
COMMENT ON COLUMN agent_sessions.messages    IS '当前会话对话历史（JSONB；DEPRECATED：V1.3 起拆 ai_messages 表）';
COMMENT ON COLUMN agent_sessions.context     IS '当前上下文（诊断结果、当前方案等 JSONB）';
COMMENT ON COLUMN agent_sessions.expires_at  IS '会话过期时间（短期 24h / 中期 7d；DEPRECATED：V1.3 改 30 分钟超时关闭走应用层 last_active_at）';
COMMENT ON COLUMN agent_sessions.created_at  IS '创建时间';
COMMENT ON COLUMN agent_sessions.updated_at  IS '最后活跃时间（过期清理用）';
COMMENT ON COLUMN agent_sessions.deleted_at  IS '软删除时间（NULL = 未删除；GDPR 物理清理走后台 Job，不依赖硬删触发器）';

-- ═══════════════════════════════════════════════════════════════════════
-- 8. feedback（V1.3 新增 · M7a/M7b/M9/M8 数据源）· data-dictionary.md 附录 D.1.2
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE feedback IS '统一反馈表（4 种 feedback_type：mood_text / mood_photo / period_photo / plan_compare_photo）；同时是 M8 召回素材与 M9 抱抱卡照片源';

COMMENT ON COLUMN feedback.id                 IS '主键（PG 18 原生 uuidv7()；PG 15 需 uuid-ossp 扩展）';
COMMENT ON COLUMN feedback.user_id            IS '关联 users.id（FK ON DELETE CASCADE）';
COMMENT ON COLUMN feedback.feedback_type      IS '4 种 feedback_type 枚举：mood_text / mood_photo / period_photo / plan_compare_photo（CHECK 约束）';
COMMENT ON COLUMN feedback.text_content       IS '文字反馈（≤ 500 字；CHECK 约束；mood_photo 时为空）';
COMMENT ON COLUMN feedback.photo_url          IS 'COS/MinIO 路径（MVP 走 Storage 抽象；隐私级别：高）';
COMMENT ON COLUMN feedback.body_part          IS '6 部位枚举：face / head / shoulder_neck / waist / leg / overall_look（与 users.focus_parts 对齐；period_photo / plan_compare_photo 必填）';
COMMENT ON COLUMN feedback.ai_ack_id          IS '关联 ai_messages.id（FK ON DELETE SET NULL；AI 回应记录）';
COMMENT ON COLUMN feedback.deleted_at         IS '软删除（NULL = 未删除；部分索引 WHERE deleted_at IS NULL）';
COMMENT ON COLUMN feedback.created_at         IS '创建时间（INDEX DESC）';
COMMENT ON COLUMN feedback.created_by         IS '创建人';
COMMENT ON COLUMN feedback.created_time       IS '创建时间（与 created_at 语义合并）';
COMMENT ON COLUMN feedback.last_updated_time  IS '最后更新时间';
COMMENT ON COLUMN feedback.last_updated_by    IS '最后更新人';

-- ═══════════════════════════════════════════════════════════════════════
-- 9. recall_sessions（V1.3 新增 · M8 主动回忆业务事件）· data-dictionary.md 附录 D.2.2
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE recall_sessions IS '一次"主动回忆"业务事件存档（不存逐轮对话，对话存 ai_sessions + ai_messages）';

COMMENT ON COLUMN recall_sessions.id                    IS '主键（PG 18 原生 uuidv7()；PG 15 需 uuid-ossp 扩展）';
COMMENT ON COLUMN recall_sessions.user_id               IS '关联 users.id（FK ON DELETE CASCADE）';
COMMENT ON COLUMN recall_sessions.plan_id               IS '关联 plans.id（FK ON DELETE SET NULL；NULL = 尚未关联方案）';
COMMENT ON COLUMN recall_sessions.trigger               IS '触发源（枚举：user_query / auto_day7 / auto_day14 / auto_day21；CHECK 约束；部分索引）';
COMMENT ON COLUMN recall_sessions.ai_summary            IS 'LLM 生成的总结（≤ 200 字；CHECK 约束）';
COMMENT ON COLUMN recall_sessions.ai_encourage          IS 'LLM 生成的鼓励语（≤ 80 字；CHECK 约束）';
COMMENT ON COLUMN recall_sessions.referenced_feedbacks  IS '召回的 feedback_ids[]（JSONB 数组）';
COMMENT ON COLUMN recall_sessions.referenced_photos     IS '调用的 photo_urls[]（JSONB 数组；signed URL，7 天有效；隐私级别：高）';
COMMENT ON COLUMN recall_sessions.llm_cost              IS 'LLM 调用成本（元，DECIMAL(10,4)）';
COMMENT ON COLUMN recall_sessions.safety_passed         IS '是否通过 Recall Safety 三层审查';
COMMENT ON COLUMN recall_sessions.ai_session_id         IS '关联 ai_sessions.id（FK ON DELETE SET NULL；一次 recall = 1 个 ai_sessions）';
COMMENT ON COLUMN recall_sessions.created_at            IS '创建时间（INDEX DESC）';
COMMENT ON COLUMN recall_sessions.deleted_at            IS '软删除时间（NULL = 未删除；部分索引）';
COMMENT ON COLUMN recall_sessions.created_by            IS '创建人';
COMMENT ON COLUMN recall_sessions.created_time          IS '创建时间（与 created_at 语义合并）';
COMMENT ON COLUMN recall_sessions.last_updated_time     IS '最后更新时间';
COMMENT ON COLUMN recall_sessions.last_updated_by       IS '最后更新人';

-- ═══════════════════════════════════════════════════════════════════════
-- 10. ai_sessions（V1.3 新增 · P03a 会话层）· data-dictionary.md 附录 D.3.2
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE ai_sessions IS 'P03a 内的一次会话（V1.1.1 从原 ai_conversations 单表拆出；30 分钟超时关闭走应用层 last_active_at）';

COMMENT ON COLUMN ai_sessions.id                    IS '主键（PG 18 原生 uuidv7()；PG 15 需 uuid-ossp 扩展）';
COMMENT ON COLUMN ai_sessions.user_id               IS '关联 users.id（FK ON DELETE CASCADE）';
COMMENT ON COLUMN ai_sessions.entry_card            IS '入口卡来源（M5 3 入口卡 + 输入框；枚举：smart_analyze / mood_diary / recall_self / direct_input；CHECK 约束）';
COMMENT ON COLUMN ai_sessions.primary_intent        IS '会话级聚合意图（枚举：module_redirect / read_query / recall / recall_ack / feedback_ack / feedback_create / medical_reject / unknown；CHECK 约束）';
COMMENT ON COLUMN ai_sessions.persona_state_start   IS '会话起始 Persona 状态（枚举：warm / neutral / slight_hug / medical_guarded；CHECK 约束；默认 warm）';
COMMENT ON COLUMN ai_sessions.persona_state_end     IS '会话结束状态（同上枚举；CHECK 约束；NULL = 未结束）';
COMMENT ON COLUMN ai_sessions.plan_id               IS '关联 plans.id（FK ON DELETE SET NULL；M3 跳转）';
COMMENT ON COLUMN ai_sessions.feedback_id           IS '关联 feedback.id（FK ON DELETE SET NULL；M7 ACK）';
COMMENT ON COLUMN ai_sessions.recall_session_id     IS '关联 recall_sessions.id（FK ON DELETE SET NULL；M8）';
COMMENT ON COLUMN ai_sessions.message_count         IS '会话内消息数';
COMMENT ON COLUMN ai_sessions.total_llm_cost        IS '累计 LLM 成本（元，DECIMAL(10,4)）';
COMMENT ON COLUMN ai_sessions.user_active           IS '用户是否主动敲字（FALSE = 全部被动触发）';
COMMENT ON COLUMN ai_sessions.started_at            IS '开启时间（INDEX）';
COMMENT ON COLUMN ai_sessions.last_active_at        IS '最后活跃时间（30 分钟超时关闭；INDEX DESC）';
COMMENT ON COLUMN ai_sessions.closed_at             IS '关闭时间（CHECK：closed_at >= started_at）';
COMMENT ON COLUMN ai_sessions.created_at            IS '创建时间（= started_at）';
COMMENT ON COLUMN ai_sessions.created_by            IS '创建人';
COMMENT ON COLUMN ai_sessions.created_time          IS '创建时间（与 created_at 语义合并）';
COMMENT ON COLUMN ai_sessions.last_updated_time     IS '最后更新时间';
COMMENT ON COLUMN ai_sessions.last_updated_by       IS '最后更新人';

-- ═══════════════════════════════════════════════════════════════════════
-- 11. ai_messages（V1.3 新增 · 会话内逐条消息）· data-dictionary.md 附录 D.4.2
-- ═══════════════════════════════════════════════════════════════════════
COMMENT ON TABLE ai_messages IS '会话内逐条消息（user / assistant / system）；UNIQUE(session_id, seq) 保证会话内序号唯一';

COMMENT ON COLUMN ai_messages.id                       IS '主键（PG 18 原生 uuidv7()；PG 15 需 uuid-ossp 扩展）';
COMMENT ON COLUMN ai_messages.session_id               IS '关联 ai_sessions.id（FK ON DELETE CASCADE）';
COMMENT ON COLUMN ai_messages.seq                      IS '会话内序号（UNIQUE 与 session_id 联合；CHECK：>= 1）';
COMMENT ON COLUMN ai_messages.role                     IS '消息角色（枚举：user / assistant / system；CHECK 约束）';
COMMENT ON COLUMN ai_messages.content                  IS '消息内容（≤ 65535 字；CHECK 约束；附录 F P0-3 防御恶意）';
COMMENT ON COLUMN ai_messages.context_photos           IS '历史照片引用（JSONB；仅元数据 + signed URL，不存 base64；隐私级别：高）';
COMMENT ON COLUMN ai_messages.referenced_feedback_ids  IS 'M8 召回引用的 feedback_ids（UUID[]；GIN 索引 WHERE <> {}）';
COMMENT ON COLUMN ai_messages.referenced_video_ids     IS 'M5 模块跳转 / 任务推荐引用的 video_ids（UUID[]；GIN 索引 WHERE <> {}）';
COMMENT ON COLUMN ai_messages.trigger                  IS '消息触发源（枚举：user_input / smart_router / module_dispatch / persona_ack / auto_recall_bubble / safety_fallback / medical_reject / unknown_fallback；CHECK 约束）';
COMMENT ON COLUMN ai_messages.intent                   IS '该条消息的具体 intent';
COMMENT ON COLUMN ai_messages.llm_cost                 IS 'LLM 调用成本（元，DECIMAL(10,4)）';
COMMENT ON COLUMN ai_messages.llm_model                IS 'LLM 模型标识';
COMMENT ON COLUMN ai_messages.llm_latency_ms           IS 'LLM 延迟（毫秒）';
COMMENT ON COLUMN ai_messages.safety_passed            IS 'Recall Safety 检查结果（NULL = 跳过检查；部分索引 WHERE FALSE 加速违规审计）';
COMMENT ON COLUMN ai_messages.safety_violations        IS '违规词组与位置（JSONB；仅 safety_passed=false 时填）';
COMMENT ON COLUMN ai_messages.token_count              IS '消息 token 数（附录 F P0-3 增补）';
COMMENT ON COLUMN ai_messages.created_at               IS '消息创建时间（INDEX DESC）';
COMMENT ON COLUMN ai_messages.created_by               IS '创建人';
COMMENT ON COLUMN ai_messages.created_time             IS '创建时间（与 created_at 语义合并）';
COMMENT ON COLUMN ai_messages.last_updated_time        IS '最后更新时间';
COMMENT ON COLUMN ai_messages.last_updated_by          IS '最后更新人';

COMMIT;

-- ═══════════════════════════════════════════════════════════════════════
-- 验证脚本（执行完后可手动跑一遍）
-- ═══════════════════════════════════════════════════════════════════════
-- 验证 1：每张表的注释列数
--   SELECT table_name, count(*) AS commented_cols
--   FROM information_schema.columns c
--   WHERE table_schema = 'public'
--     AND table_name IN (
--       'users','reports','videos','plans','checkins','posts','agent_sessions',
--       'feedback','recall_sessions','ai_sessions','ai_messages'
--     )
--   GROUP BY table_name
--   ORDER BY table_name;
--
-- 验证 2：所有字段的 COMMENT 文本（抽样检查）
--   SELECT c.table_name, c.column_name,
--          col_description(c.table_name::regclass, c.ordinal_position) AS comment
--   FROM information_schema.columns c
--   WHERE table_schema = 'public'
--     AND col_description(c.table_name::regclass, c.ordinal_position) IS NOT NULL
--   ORDER BY c.table_name, c.ordinal_position;
--
-- 验证 3：抽样确认（应返回中文注释）
--   \d+ users
--   \d+ ai_messages
--   \d+ feedback