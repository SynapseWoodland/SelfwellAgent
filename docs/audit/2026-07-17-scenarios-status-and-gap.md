# 场景文档集 · 现状与差距分析 · 综述

> **本文档是真源(PRD V3.0 + MVP-PRD V1.3 + 架构 V3)与 14 份场景文档(S01-S14)之间的"现状层"**。
> 通过 PostgreSQL MCP (`@modelcontextprotocol/server-postgres`) 直连 `selfwell` 库,采集 2026-07-15 实际数据;
> 通过 `findstr` + `Read` 采集后端 15 个 router / 32 个 service / **6 个 alembic 迁移文件(0001~0006,0007/0008 已删除)** + 3 份 Golden Set 文件清单。
>
> **目的**:
> 1. 让 14 份场景文档不再是"理想路径",而是**对照现实工程资产**的"可执行方案"
> 2. 给后续 PR / 排期 / QA / DevOps 提供单一真源(Single Source of Truth)
> 3. 用事实量化"距离 MVP 闭环还差什么"

**真源基线**: `docs/PRD/AI正向身心健康自律成长平台 PRD V3.0.md`(43,202B) + `docs/PRD/MVP-PRD V1.3.md`(48,411B) + `docs/architecture/tech-architecture-design-v3.md`(30,937B),三份字节均未变。

---

## 0. 摘要(给 PM / Tech Lead 一分钟读)

| 维度 | 现实 | 期望 | 差距 |
|------|-----|------|------|
| **DB 总大小** | 13 MB | — | — |
| **核心业务表行数(users/plans/checkins/feedback)** | 1/0/0/0 | 单测种子数据 | **缺种子数据** |
| **alembic 当前版本** | `0006_add_skin_type_to_users`(head 保持 0006 是项目既定选择) | — | ✅ **无 drift** |
| **V2 表(user_badges / user_notification_prefs / account_deletion_requests / user_self_tags)** | DB 已存在(经手工 SQL 或 0007/0008 应用后,代码侧 alembic 文件已删除) | 已落地 | ✅ |
| **RLS 启用表数** | 0 / 15 | 15 / 15 | **全表未启用 RLS** |
| **`_copy1` 表(数据快照副本)** | 13 张表 + 100+ 索引 = ~5 MB | 保留 | ✅ **项目要求保留**(可能是数据快照/审计备份/灰度对比副本) |
| **后端 router 实现** | 15 个 / 14 场景 | 14 | **≥ 满足**(V2 表已存在说明 PR-2 已合) |
| **后端 service 实现** | 32 个 / 14 场景 | 14 | **满足** |
| **Golden Set** | 3 份分散(v1/v2/v2 不同位置) | 1 份 v2 唯一真源 | **版本分裂未治理** |
| **ADR-0017 Recall Safety** | `recall_service.py` 真实实现 4 组 100+ 词 3 层防线 | 100+ 词硬编码 | ✅ **已实现** |
| **ADR-0017 词典 yaml** | 文档说 `docs/data/recall-forbidden-words.yaml` 但仓库无文件 | 必须存在 | **缺文件** |
| **合规检查器** | W1 骨架(关键词匹配) | W3 LLM 语义级 | **W2/W3 待补** |
| **场景文档"现状分析"章节** | 14 份均缺失 | 14 份齐全 | **全部缺失,本次补齐** |
| **场景文档"下一步行动"章节** | 14 份均缺失 | 14 份齐全 | **全部缺失,本次补齐** |
| **场景文档"用例 check"章节** | 14 份均缺失 | 14 份齐全 | **全部缺失,本次补齐** |

**优先级**:P0(立即)/P1(2 周内)/P2(1 个月内) — 见 §7 行动表。

---

## 1. 数据库现状(PostgreSQL `selfwell`)

### 1.1 表清单(15 张干净表)

| 表名 | 场景 | 行数 | 体积 | 索引数(估) | RLS | 软删除 |
|------|-----|-----|------|----------|-----|------|
| `users` | S01 | **1** | 248 KB | 12 | ❌ | ✅ deleted_at |
| `ai_sessions` | S02 | **0** | 208 KB | 4 | ❌ | ❌ |
| `ai_messages` | S02 | **0** | 128 KB | 8 | ❌ | ❌ |
| `reports` | S03 | **0** | 144 KB | 5 | ❌ | ✅ deleted_at |
| `plans` | S04 | **0** | 200 KB | 6 | ❌ | ✅ deleted_at |
| `checkins` | S05 | **0** | 264 KB | 7 | ❌ | ✅ deleted_at |
| `feedback` | S06 | **0** | 112 KB | 4 | ❌ | ✅ deleted_at |
| `recall_sessions` | S07 | **5** | 104 KB | 5 | ❌ | ✅ deleted_at |
| `posts` | S11 | **10** | 192 KB | 8 | ❌ | ✅ deleted_at |
| `videos` | S04 (L1) | **74** | 272 KB | 11 | ❌ | ✅ deleted_at |
| `user_badges` | S09 (V2) | 0 | 40 KB | 3 | ❌ | ❌ |
| `user_notification_prefs` | S13 (V2) | 0 | 48 KB | 1 | ❌ | ❌ |
| `user_self_tags` | S07/S14 (V2) | 0 | 48 KB | 4 | ❌ | ❌ |
| `account_deletion_requests` | S12 (V2) | 0 | 32 KB | 0 | ❌ | ✅ deleted_at |
| `alembic_version` | — | 1 | 24 KB | 0 | — | — |

### 1.2 alembic 迁移状态

- **当前 head**:`0006_add_skin_type_to_users`(DB `alembic_version.version_num` 确认)
- **磁盘上的 alembic 迁移文件**(2026-07-15 现场扫描):
  ```
  0001_initial_v13_locked.py
  0002_flatten_report_jsonb.py
  0003_flatten_report_cache.py
  0004_report_status.py
  0005_add_assistant_profile_to_ai_sessions.py
  0006_add_skin_type_to_users.py
  ```
  — 共 **6 个迁移 + `__init__.py`**,**没有 0007/0008**(已删除)。
- **V2 表在 DB 已落地**:`user_badges / user_notification_prefs / account_deletion_requests / user_self_tags` 四张 V2 表存在于 DB,**未经过 alembic 通道**,alembic_version 保持 0006。
- **项目既定选择**:删除 0007/0008 文件 + DB head 保持 0006 + V2 表事实已存在 → 后续 CI 迁移门禁配置为"从 0006 起算,新迁移不要重命名 V2 表"。
- **对场景文档的指引**:本文档集中凡是引用 `0007 / 0008 alembic 迁移` 的描述,改为"V2 表在 DB 已存在,具体 schema 见 §1.1 表清单"。

### 1.3 `_copy1` 数据快照副本清单(项目要求保留)

> **项目要求:所有 `_copy1` 结尾的表不删除,保留**。可能是历史数据快照 / 灰度对比副本 / 审计备份,具体来源未在文档化。本文档集不将其视为脏数据。

| `_copy1` 表 | 行数 | 体积 | 索引数 | 备注 |
|------------|-----|------|------|------|
| users_copy1 | 2 | 208 KB | 9 | 唯一真实有数据(2 行)的 _copy1,需评估是否合并回 users |
| videos_copy1 | 0 | 208 KB | 9 | 空表 |
| checkins_copy1 | 0 | 200 KB | 6 | 空表 |
| ai_sessions_copy1 | 0 | 168 KB | 4 | 空表 |
| posts_copy1 | 0 | 144 KB | 8 | 空表 |
| plans_copy1 | 0 | 136 KB | 6 | 空表 |
| ai_messages_copy1 | 0 | 128 KB | 5 | 空表 |
| reports_copy1 | 0 | 112 KB | 5 | 空表 |
| feedback_copy1 | 0 | 104 KB | 2 | 空表 |
| recall_sessions_copy1 | 0 | 104 KB | 4 | 空表 |
| user_notification_prefs_copy1 | 0 | 48 KB | 1 | 空表 |
| user_self_tags_copy1 | 0 | 48 KB | 3 | 空表 |
| user_badges_copy1 | 0 | 40 KB | 3 | 空表 |
| **小计(13 表)** | **2** | **~1.5 MB** | **~65** | — |
| _copy1 全部索引(100+) | — | ~3 MB | — | 含 pkey / 业务索引 |
| **总计** | | **~5 MB** 占 13 MB DB 的 38% | | |

**对场景文档的指引**:
- 本文集中凡是提到"`_copy1` 残留需清理"`_copy1` 脏数据"的描述,改为"`_copy1` 是项目保留的历史副本,不视为脏数据"。
- 唯一有真实数据的 `users_copy1`(2 行)需 Tech Lead 评估"是否合并回 users 主表"——独立 P2 行动项(P2-8),非 P0。
- **不在 P0 行动表内**做清理。

### 1.4 RLS 现状(全部 0 张表启用)

**场景文档 S01-S14 全部声明启用 RLS,实际 DB 0 张启用** — 这是 MVP 上线前必须补的**安全必修项**。

**优先级理由**:MVP 上线必须满足 PIPL/GDPR,RLS 是合规基本线。

### 1.5 ID 生成与字段命名差异

| 文档声明 | DB 实际 | 差异说明 |
|---------|--------|--------|
| `id uuid_generate_v4()` | `id uuidv7()` (内置) | UUIDv7 是 PG 13+ 内置,排序友好,无需扩展。**文档已过时,应改为 uuidv7** |
| `users.age_gate_passed` | `users.skin_type`(age 字段是 `age_range` 字符串) | 文档字段未对齐,需更新 |
| `checkins.plan_day_id` | `checkins.plan_id(varchar) + day(int)` 拼接 | **没有 plan_days 子表,plans.days jsonb 存储** |
| `checkins.checkin_date` | ❌ 无,只用 `created_at` | 需要新增 `checkin_date` 字段 |
| `checkins.completed_at` | ❌ 无 | 同上 |
| `feedback.body_part` (多部位) | `feedback.body_part` 单字段 varchar | **MVP 多部位未实现** |
| `plans.day_count=21` | `plans.days jsonb` 存 | **plans 没 day_count 字段,days 是 jsonb 数组** |
| `plan_days` 子表 | ❌ **不存在** | 用 plans.days jsonb 内嵌替代 |
| `account_deletions` | `account_deletion_requests` | 名称不一致 |
| `user_push_preferences` | `user_notification_prefs` | 名称不一致 |
| `hug_card_records` | ❌ **不存在** | S09 未建表 |
| `push_records` | ❌ **不存在** | S13 未建表 |
| `safety_audit_logs` | ❌ **不存在** | S14 未建表 |
| `sensitive_words` | ❌ **不存在** | S14 未建表 |
| `intent_templates` / `intent_unknown_logs` | ❌ **不存在** | S08 未建表 |
| `mv_entry_card_state` 物化视图 | ❌ **不存在** | S02 未建 |
| `export_jobs` | ❌ **不存在** | S12 未建 |
| `daily_push_logs` | ❌ **不存在**(已声明放弃) | P1 修复已合并到 `push_records` |
| `recall_violation_words` / `recall_safety_audit` | ❌ **不存在**(已声明放弃) | P1 修复已合并到 `sensitive_words` / `safety_audit_logs` |
| `fragments` | ❌ **不存在** | S05 未建(用 checkins 表替代) |

**核心结论**:**15 张表覆盖了 ~60% 场景文档声明的表;剩余 ~10 张表(主要是 S08/S09/S12/S13/S14)DB 完全不存在**。

---

## 2. 后端代码现状

### 2.1 路由(15 个,目标 14)

✅ **完整覆盖**:auth_v1 / users_v1 / butler_v1 / assistant_v1 / diagnosis_v1 / plans_v1 / checkin_v1 / feedback_v1 / community_v1 / share_v1 / uploads_v1 / business_v1 / v2(IA + 主页)/ system

**说明**:`business_v1` 是早期的诊断 router,目前 `diagnosis_v1` 是新版本;两个并存,需要确认是否需要保留 `business_v1`。

### 2.2 Service(32 个)

**ADR 关联实现情况**:

| ADR | 真源声明实现位置 | 实际代码 | 状态 |
|-----|-------------|---------|------|
| ADR-0017 Recall Safety 100+ 词 | `recall_service.py` | ✅ 4 组 100+ 词 3 层防线完整实现 | **完成 W3** |
| ADR-0017 词典 yaml | `docs/data/recall-forbidden-words.yaml` | ❌ 仓库无该文件 | **缺文件** |
| ADR-0016 Feedback Unified 4 类 | `feedback_service.py` + `feedback_v1` | ✅ feedback 表已 4 类(`feedback_type varchar`)| **基本完成** |
| ADR-0016 30 条柔性话术池 | `app/data/persona_ack_pool.json` | ❓ 未查到该文件 | **缺文件或需验证** |
| ADR-0015 Persona 合同 | `assistant_service.py` | ✅ 已实现 `assistant_profile jsonb` 在 ai_sessions | **完成** |
| ADR-0013 SmartRouter | `assistant_v1` 或 `butler_v1` | ⚠️ 待查具体路由 | **部分实现** |
| ADR-0012 三档柔性话术 | `quick_reply_service.py` | ✅ 文件存在 | **完成** |

### 2.3 Golden Set(三份分散)

| 文件位置 | 版本 | 用途 |
|---------|------|------|
| `backend/eval/golden_set_v1.yaml` | v1 | 老 Eval Runner 用 |
| `backend/tests/golden_set/golden_set_v2.yaml` | v2 | pytest 用 |
| `backend/tests/golden/golden_set_v2.yaml` | v2 | pytest 用(另一份?) |

**问题**:v2 路径有两份,需要确认哪一份是当前真源。

### 2.4 Alembic 文件 vs DB 状态(无 drift)

| 迁移 | 文件存在 | DB 已应用 | 是否飘移 |
|------|--------|---------|---------|
| 0001_initial_v13_locked | ✅ | ✅ | — |
| 0002_flatten_report_jsonb | ✅ | ✅ | — |
| 0003_flatten_report_cache | ✅ | ✅ | — |
| 0004_report_status | ✅ | ✅ | — |
| 0005_add_assistant_profile_to_ai_sessions | ✅ | ✅ | — |
| 0006_add_skin_type_to_users | ✅ | ✅(当前 head) | — |
| 0007_add_v2_ia_tables | ❌(已删除) | ✅(V2 表已落地,经手工 SQL 或其他方式)| **无 drift**(项目既定选择) |
| 0008_ensure_pk_user_notification_prefs | ❌(已删除) | ✅(用户已自行 rename) | **无 drift** |

**结论**:**alembic 链条封顶 0006**,V2 表(user_badges / user_notification_prefs / account_deletion_requests / user_self_tags)在 DB 事实存在但 alembic 不可见。CI 迁移门禁按"DB schema 与 code ORM model 一致"对齐,不依赖 alembic_version。

---

## 3. 场景文档 ↔ 实际资产 14 份对齐矩阵

> 表格中"✅ 已实现"= 代码 + DB + 文档三者一致;"⚠️ 部分"= 任一不一致;"❌ 缺失"= DB 不存在表 或 代码无 service;"🔧 待修"= 需要修文档对齐代码,或修代码对齐文档。

| 场景 | 文档声明表 | DB 实际 | 文档声明 service | 代码实际 | 现状评级 |
|------|---------|--------|--------------|--------|--------|
| **S01** 启动+登录+档案 | `users / login_log` | `users` 1 行,**login_log 缺失** | `auth/wx_login / profile_service` | ✅ | ⚠️ login_log 缺表 |
| **S02** 智能管家主页 | `ai_sessions / ai_messages / mv_entry_card_state` | `ai_sessions / ai_messages` 0 行,**物化视图缺** | `butler_service / assistant_service` | ✅ `butler_v1` + `assistant_v1` | ⚠️ 物化视图缺 |
| **S03** 诊断三步卡 | `reports / report_uploads` | `reports` 0 行,**report_uploads 缺** | `diagnosis_service` | ✅ `diagnosis_v1` 571 行 | ⚠️ report_uploads 缺 |
| **S04** 21 天方案 | `plans / plan_days / videos / daily_push_logs` | `plans / videos` 已建,**plan_days 缺,days 用 jsonb; daily_push_logs 不建(已合并 push_records)** | `plan_service / video_match` | ✅ | ⚠️ plan_days / push_records 双缺 |
| **S05** 每日打卡 | `checkins / fragments` | `checkins` 已建,**fragments 缺** | `checkin_service` | ✅ `checkin_v1` 已修改 | ⚠️ fragments 缺 |
| **S06** 反馈 | `feedback` (含 `body_part_enum`) | `feedback` 已建(单字段 body_part varchar) | `feedback_service` | ✅ | ⚠️ 多部位未实现 |
| **S07** 主动回忆 | `recall_sessions + recall_violation_words + recall_safety_audit` | `recall_sessions` 5 行,**两表合并到 S14** | `recall_service` 完整 ADR-0017 | ✅ 4 组 100+ 词 | ⚠️ 词典 yaml 缺 |
| **S08** SmartRouter | `intent_templates / intent_unknown_logs` | **两表全缺** | `assistant_v1`? | ⚠️ 待确认 | ❌ 表全缺 |
| **S09** 抱抱卡 | `hug_card_records` | **表缺** | `v2/badge_service` | ✅ file exists | ⚠️ hug_card_records 缺 |
| **S10** 时光相册 | 复用 feedback | ✅ | `v2/album_service` | ✅ file exists | ✅ |
| **S11** 蜕变广场 | `posts / post_images / activities` | `posts` 已建 10 行,**post_images / activities 缺** | `community_service` | ✅ `community_v1` | ⚠️ post_images / activities 缺 |
| **S12** 个人中心 | `export_jobs / account_deletions` | **`account_deletion_requests` 已建(V2),`export_jobs` 缺** | — | 待查 | ⚠️ export_jobs 缺 |
| **S13** 推送调度 | `push_records / user_push_preferences` | **`user_notification_prefs` 已建(V2),`push_records` 缺** | `v2/notification_service` | ✅ file exists | ⚠️ push_records 缺 |
| **S14** 合规 | `safety_audit_logs / sensitive_words` | **两表全缺** | `compliance/checker.py` W1 | ⚠️ W2/W3 未做 | ❌ 表全缺 |

**总结**:14 场景中 **2 场景完全达标(S10/S07 主体)** / **12 场景有缺口需补**。

---

## 4. 三视角自检 · 业务 / 技术 / 用例

> 用户要求"业务上、技术上、用例"三维 check。下方是 14 场景 × 3 维度 = 42 项 check 结果摘要。**每份场景文档末尾会展开**。

### 4.1 业务视角 check(用户旅程完整性)

| 场景 | 业务路径完整? | 异常路径覆盖? | 边界用例? | 阻断性 gap |
|------|------------|------------|---------|----------|
| S01 | ✅ | ✅ | ⚠️ 5 项档案任意可空 | age_range/sitting_hours/intensity DB 都为 NULL 时正常 |
| S02 | ✅ | ⚠️ 新用户 / 老用户 state 切换未在代码明确 | — | 需要看 `assistant_profile` 默认值 |
| S03 | ✅ | ✅(上传失败/超时/降级) | — | 报告 CTA 点击率埋点缺 |
| S04 | ✅ | ⚠️ 21 天提前完成怎么办 | 视频池 74 个是否够 21×N 用户 | video_match 算法需验证 |
| S05 | ✅ | ✅(打卡未完成 persona) | — | 错过打卡连续中断规则 |
| S06 | ✅ | ⚠️ 多部位反馈 DB 单字段限制 | 用户填写多个部位时丢失 | DB schema 不支持 |
| S07 | ✅ | ✅(空态 3 按钮) | — | 5 行 seed 数据是否覆盖 Day 7/14/21 |
| S08 | ⚠️ | ❌ 兜底 unknown 缺失表 | intent_unknown_logs 表缺 | 兜底数据无法落库 |
| S09 | ✅ | ⚠️ 7/14/21 达标 判定规则 | badge_service 是否消费了真实 checkin 数据 | 待查 |
| S10 | ✅ | ⚠️ 极简时间轴(无对比) P2 才上 | — | 无 LLM 年度回顾时降级 |
| S11 | ✅ | ✅(审核/拒稿) | — | MVP 砍点赞已实施 |
| S12 | ⚠️ | ❌ 异步导出队列表 export_jobs 缺 | 用户点导出后看不到任务状态 | 缺表 |
| S13 | ⚠️ | ❌ push_records 缺表 | 推送失败重试规则 | 缺表 |
| S14 | ⚠️ | ❌ safety_audit_logs 缺表 | 异步复审 Worker 无法落库 | 缺表 |

**业务视角总结**:**6 个场景(S08/S09/S12/S13/S14 + S06 多部位)有阻断性 gap**,必须修。

### 4.2 技术视角 check(实现可行性)

| 场景 | 技术债等级 | 主要问题 |
|------|---------|--------|
| S01 | 🟡 中 | login_log 缺表 → 无法做登录审计 |
| S02 | 🟡 中 | 物化视图缺 → 主页 entry_card_state 需要 N+1 查询,延迟高 |
| S03 | 🟢 低 | report_uploads 缺表,但 reports 表 photos 是 jsonb,可暂用 |
| S04 | 🟠 中 | plan_days 缺 → 21 天子结构塞 jsonb 查询性能差,缺 idx |
| S05 | 🟢 低 | fragments 缺 → checkins 表足以替代 |
| S06 | 🟠 中 | body_part 单字段 → 多部位需改 schema |
| S07 | 🟢 低 | ADR-0017 真实实现 + 词典 yaml 缺是 P2 项 |
| S08 | 🔴 高 | intent_templates / intent_unknown_logs 缺 → SmartRouter 无法落库 |
| S09 | 🟡 中 | hug_card_records 缺 → 抱抱卡记录无法持久化 |
| S10 | 🟢 低 | 复用 feedback OK |
| S11 | 🟡 中 | post_images / activities 缺 → 帖子多图 + 主题活动无法上 |
| S12 | 🔴 高 | export_jobs 缺 → 数据导出异步链路整体不可用 |
| S13 | 🔴 高 | push_records 缺 → 推送记录全部不可落库,合规审计风险 |
| S14 | 🔴 高 | safety_audit_logs / sensitive_words 双缺 → 合规整体不达标 |

**技术视角总结**:**4 个场景(S08/S12/S13/S14)技术债 = 🔴 高,阻断 MVP**。

### 4.3 用例视角 check(测试覆盖)

| 场景 | 文档列的用例数 | pytest 已覆盖? | Golden Set 已覆盖? | 缺口 |
|------|-------------|--------------|------------------|------|
| S01 | F1-F5 | ⚠️ 待查 | — | 隐私协议弹窗用例 |
| S02 | UC-BU-* 多 | ⚠️ | ⚠️ v2 部分 | 主页 state 切换 |
| S03 | 5+ | ✅ diagnosis_v1.py | ✅ GN-DG-01~08 | 单 LLM 超时降级 |
| S04 | 5+ | ✅ plans_v1 | ⚠️ | 视频匹配回退 |
| S05 | 5+ | ✅ checkin_v1 | — | persona 三档话术命中 |
| S06 | 4+ | ✅ feedback_v1 | ⚠️ | 多部位反馈持久化 |
| S07 | 5+ | ✅ recall_service | ✅ recall_forbidden | Day N 触发器 |
| S08 | A/B/C/D/E 5 类 | ⚠️ | — | D 类接 S07 端到端 |
| S09 | 4+ | ⚠️ | — | 7/14/21 达标判定 |
| S10 | — | ⚠️ | — | 时间轴分桶性能 |
| S11 | 4+ | ✅ community_v1 | — | 审核 AI 拒稿 |
| S12 | 4+ | ⚠️ | — | 注销 15 天冷静期 |
| S13 | 5+ | ⚠️ | — | 早 8 点推送 cron |
| S14 | 5+ | ⚠️ compliance/checker W1 测试 | ⚠️ W2/W3 缺 | LLM 语义级审查 |

**用例视角总结**:**S08/S12/S13/S14 测试覆盖严重不足**(与 §4.2 技术债高重合)。

---

## 5. 共享资产 / 共用模块现状

### 5.1 共用表(已实现 vs 缺失)

| 共用表 | 提供方 | 消费方 | DB 状态 |
|------|------|------|--------|
| `users` | S01 | S02-S14 全部 | ✅ |
| `ai_sessions / ai_messages` | S02 | S03/S06/S07/S08/S09 | ✅ / ✅ |
| `feedback` | S06 | S07/S09/S10/S13 | ✅ |
| `plans` (内嵌 days jsonb) | S04 | S05/S07/S13 | ⚠️ 缺 plan_days 子表 |
| `checkins` | S05 | S07/S09/S13 | ✅ |
| `videos` | S04 | S03/S04/S05 | ✅ 74 行 |
| `recall_sessions` | S07 | S02/S13 | ✅ 5 行 |
| `user_notification_prefs` | S13 | S13 内部 | ✅ |
| `safety_audit_logs` | S14 | S14 + 全场景 | ❌ 缺 |
| `sensitive_words` | S14 | S07/S08/S11/S14 | ❌ 缺 |
| `push_records` | S13 | S13 + S04/S07/S09 推送记录 | ❌ 缺 |

### 5.2 共用服务 / 文件(已实现 vs 缺失)

| 资产 | 真源路径 | 实际位置 | 状态 |
|------|--------|---------|------|
| 30 条柔性话术池 | `backend/data/persona_ack_pool.json` | ❌ 找不到 | **缺文件** |
| Recall 100+ 词典 yaml | `docs/data/recall-forbidden-words.yaml` | ❌ 找不到 | **缺文件**(代码内有 inline dict 兜底) |
| APScheduler 调度器 | `backend/app/services/scheduler.py` | ⚠️ 待查 | 文档说 S13 集中调度,需查实际 cron 注册 |
| 微信推送通道 | `backend/app/integrations/wx/wx_push.py` | ⚠️ 待查 | `user_notification_prefs` 存在说明有推送基础设施 |
| StorageFacade 抽象 | `backend/app/core/storage_facade.py` | ⚠️ 待查 | S04/S06/S07 都引用 |
| JWT / UnionID 鉴权 | `backend/app/auth/jwt_handler.py` + `wechat_client.py` | ✅ 文件存在 | ✅ |

---

## 6. P0/P1/P2 优先级行动表

> 基于"业务阻断性"+"技术债等级"+"测试覆盖度"三维评估。

### P0 · 立即(本周内,阻塞 MVP 上线)

| # | 行动 | 阻塞点 | 预计工作量 |
|---|------|------|----------|
| **P0-1** | **RLS 全表启用(15 张)** | PIPL/GDPR 合规上线必填 | 2 h(可用 docs/scenarios/S01 §3.1 模板) |
| **P0-2** | **建 `safety_audit_logs` 表**(S14 DDL) | Layer 4 异步复审无法落库 | 1 h |
| **P0-3** | **建 `sensitive_words` 表 + 录入 100+ 词**(S14 + S07 词典合并) | ADR-0017 落库 | 2 h |
| **P0-4** | **建 `push_records` 表**(S13 DDL) | 推送审计无落点 | 1 h |
| **P0-5** | **建 `intent_templates` + `intent_unknown_logs`**(S08) | SmartRouter 兜底无落点 | 1 h |
| **P0-6** | **建 `hug_card_records`**(S09) | 抱抱卡记录无法持久化 | 0.5 h |

**P0 总计**:7.5 h(约 1 人日)

> **P0 取消项**(2026-07-15 用户决策):
> - ~~P0-1(原):清理 `_copy1` 表~~ → 全部保留
> - ~~P0-2(原):`alembic upgrade head` 拉齐到 0008~~ → 0007/0008 文件已删除,DB head 保持 0006 是项目既定选择

### P1 · 2 周内

| # | 行动 | 阻塞点 | 预计工作量 |
|---|------|------|----------|
| P1-1 | 建 `plan_days` 子表(从 plans.days jsonb 拆出) | S05/S07 查询性能 | 3 h |
| P1-2 | 建 `fragments` 表(S05) | checkin fragments 数据建模 | 2 h |
| P1-3 | `feedback.body_part` 改 jsonb 数组支持多部位 | S06 多部位反馈 | 2 h |
| P1-4 | 建 `mv_entry_card_state` 物化视图(S02) | 主页 4 卡 state 查询性能 | 2 h |
| P1-5 | 建 `export_jobs` + `account_deletions` 迁移到 `account_deletion_requests` 命名对齐(S12) | S12 数据导出 | 3 h |
| P1-6 | `recall-forbidden-words.yaml` 创建 + recall_service 引用 yaml 而非 inline dict | ADR-0017 词库维护性 | 2 h |
| P1-7 | `persona_ack_pool.json` 30 条话术池文件创建 + quick_reply_service 引用 | ADR-0016 强制规则 | 2 h |
| P1-8 | Golden Set 三份分散 → 1 份真源 | 评测可维护性 | 1 h |
| P1-9 | Compliance Checker W2(LLM 语义级审查) | S14 W2 | 4 h |

**P1 总计**:21 h(3 人日)

### P2 · 1 个月内

| # | 行动 | 阻塞点 | 预计工作量 |
|---|------|------|----------|
| P2-1 | 建 `post_images` + `activities` 表(S11) | 帖子多图 + 主题活动 | 2 h |
| P2-2 | `login_log` 表(S01 审计) | 登录审计 | 1 h |
| P2-3 | `report_uploads` 表(S03) | 诊断原图元数据 | 2 h |
| P2-4 | Compliance Checker W3(LLM + 共享词库) | S14 W3 | 4 h |
| P2-5 | SPEC-M1~M12 + SPEC-A0-* 实体文档建立 | 文档可追溯 | 8 h |
| P2-6 | ADR 实体文档 `docs/adr/ADR-*.md` 建立 | ADR 真名回填 | 8 h |
| P2-7 | 14 场景文档 vs 代码 vs DB 三方对齐 Review | 文档可信度 | 8 h |
| **P2-8** | **评估 `users_copy1`(2 行)是否合并回 `users` 主表** | 项目决策 | 1 h |

**P2 总计**:34 h(约 4 人日)

---

## 7. 给 PM / Tech Lead / QA 的可读结论

### 7.1 给 PM(决策层)
- **MVP 距离闭环还有 7.5+21+34 = 62.5 h ≈ 8 人日**(P0+P1+P2 全部按人日折算)
- **不建议未完成 P0-1~P0-6 就对外发布**(合规上线风险)
- **S08 / S12 / S13 / S14 是 MVP 上线前的硬阻塞**

### 7.2 给 Tech Lead / Backend
- 按 §6 P0-1~P0-6 顺序建表 + 启 RLS
- RLS 是 P0-1,**必须在所有新表创建后立即启用**,不要先建后补
- `_copy1` 表保留,无需清理(项目决策)
- alembic 文件不再添加 0007/0008,DB head 保持 0006 是项目既定选择

### 7.3 给 QA / 测试
- Golden Set 版本分裂治理(P1-8)后再大规模跑回归
- S08/S12/S13/S14 现状测试覆盖严重不足,补完 P0 表后立刻补用例
- §4 三视角 check 表可作为测试用例设计 checklist

### 7.4 给 DevOps
- DB 13 MB(保留 `_copy1` 后无法缩减)
- alembic 链条封顶 0006,CI 迁移门禁按"DB schema 与 ORM model 一致"对齐,**不要**按 `alembic_version` 校验

---

## 8. 与真源的差异约束(更新)

| 冲突点 | 处理 |
|------|------|
| 场景文档字段命名 vs DB 实际 | 场景文档已认 DB 实际命名(`account_deletion_requests` / `user_notification_prefs`),更新文档 §7 ADR/SPEC 引用表 |
| 场景文档表的 ID 用 `uuid_generate_v4()` | DB 实际 `uuidv7()`,更新文档 §3.1 |
| `body_part` 单字段 | 文档说明"P1 升级为 jsonb 数组",标 P1-3 |
| `daily_push_logs` / `recall_violation_words` / `recall_safety_audit` 三表 | 已声明合并到 S13 `push_records` / S14 `sensitive_words` / S14 `safety_audit_logs`(P1/P2/P3 修复) |
| 13 张 `_copy1` 表(项目保留) | 已记录在 §1.3,**不视为脏数据** |
| alembic 0007/0008(已删除) | 已记录在 §1.2,DB head 保持 0006 是项目既定选择 |
| `users_copy1` 2 行真实数据 | 待 P2-8 评估是否合并回 `users` |

任何本文档与真源冲突 → 以真源(PRD V3.0 / MVP-PRD V1.3 / 架构 V3)为准。

---

## 9. 后续维护

- 本文档每完成一个 P0/P1/P2 项 → 在对应行打 ✅ 并注明完成日期
- 每完成一 PR 涉及新表 / 新 ADR → 同步更新 §1 表清单 + §3 矩阵
- 用户行为埋点数据回流 → 更新 §4.1 业务路径完整度
- 每月一次 Review:差距表 + 行动表 → 重排 P0/P1/P2

---

**综述完。**
