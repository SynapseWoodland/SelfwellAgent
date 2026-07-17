# 用户视角业务场景拆解 · 总索引

> **本文档集是从用户视角出发的业务场景化拆解**,每份场景文档将 PRD V3.0 + MVP-PRD V1.3 + 技术架构 V3 三份真源中的功能拆解到**功能 → 技术点 → 实现方案 → 预期结果 → 场景用例**五层粒度,供前端、后端、AI 工程、QA、内容运营、PM 共同对齐。

---

## 0. 元信息

| 项 | 内容 |
| --- | --- |
| 版本 | V1.0 |
| 日期 | 2026-07-14 |
| 编写模式 | 1 人 + AI 工具加速 |
| 真源基线 | `docs/PRD/AI正向身心健康自律成长平台 PRD V3.0.md` + `docs/PRD/MVP-PRD V1.3.md` + `docs/architecture/tech-architecture-design-v3.md` |
| 关联 ADR | ADR-0001 ~ ADR-0017(0013/0014/0015 智能管家三件套:0013 输入框意图分类、0015 Persona 合同、0016 Feedback Unified、0017 Recall Safety) |
| 关联 SPEC | SPEC-A0-MASTER-IA(信息架构总纲)、SPEC-M1 ~ SPEC-M12 |
| 范围 | MVP 全 11 模块 + P1 已规划能力 + 系统级(推送/合规/数据导出) |
| **现状综述** | [00-status-and-gap.md](00-status-and-gap.md) — 通过 MCP 直连 PostgreSQL + 后端代码扫描得到的 14 场景 vs 实际资产差距分析(必读) |

---

## 1. 拆分原则

1. **以用户行为为单位,不以技术层为单位**:一个用户动作拆出一个场景文件,而不是按"前端模块"或"后端服务"拆。
2. **三层深度固定**:每个场景都覆盖 (1) **功能**(用户感知) → (2) **技术点**(实现依赖) → (3) **实现方案 + 预期结果 + 场景用例**(可直接交付)。
3. **技术点覆盖度**:数据库脚本 / API 接口 / 调度器 / Qdrant 召回 / Prompt+Golden / Eval / 数据导出 / 前后端契约 / Agent 协调 / MCP / 评测集 —— 每份文档都按需覆盖,不漏。
4. **不替写真源**:本文档集是**索引 + 拆解**,不修改 PRD/SPEC/ADR,冲突时回真源。
5. **MVP/P1/P2 分阶段标注**:每项技术点都标 `MVP` / `P1` / `P2`,便于排期。

---

## 2. 场景总表(14 份)

| # | 场景文件 | 用户感知路径 | MVP / P1 / P2 | 对应 PRD | 对应模块 |
|---|---------|------------|---------------|---------|---------|
| **S01** | [启动 + 极简登录 + 用户档案](S01-launch-login-profile.md) | 扫码 → 微信 OAuth / wx.login → 5 项档案 → 进入 P03a | MVP | PRD §5.1 / MVP-PRD §3.1 | M1 |
| **S02** | [智能管家对话主页 · 基线问候](S02-butler-home-baseline.md) | 任意时刻进入 Tab"智能管家" | MVP | PRD §六 / MVP-PRD §3.5 | M5(主页层) |
| **S03** | [AI 智能诊断 · 对话流内三步卡](S03-diagnosis-3step-card.md) | 点 🔍 智能分析入口卡 → 上传 → 分析 → 报告 | MVP | PRD §五 / MVP-PRD §3.2 | M2 |
| **S04** | [21 天方案生成 + 每日任务推送](S04-plan-21day-push.md) | 报告 CTA"开始 21 天" → 进入打卡循环 | MVP | PRD §五.3 / MVP-PRD §3.3 | M3 + 调度器 |
| **S05** | [每日打卡闭环 + 柔性话术](S05-checkin-loop.md) | 早 8 点服务通知 → 今日任务 → 跟练 → 打卡 | MVP | PRD §六.5 / MVP-PRD §3.4 | M4 |
| **S06** | [心情日记 + 多部位反馈](S06-mood-diary-feedback.md) | P03a 点 📖 或 P08a 编辑器保存 | MVP | PRD §八 / MVP-PRD §3.7 | M7a + M7b |
| **S07** | [与"过去的自己"对话 · 主动回忆](S07-recall-past-self.md) | Day 7/14/21 早晨推气泡 / 用户点 💬 / 空态 soft-tip | MVP | PRD §七.5 / MVP-PRD §3.8 | M8 |
| **S08** | [智能管家输入框 · SmartRouter](S08-butler-smart-router.md) | P03a 输入框打字或点 Chip | MVP(A+B 类)/ P1(C+D 类) | PRD §六.4 / MVP-PRD §3.5.3 | M5(意图层) |
| **S09** | [抱抱卡 + 进度环](S09-hug-card-progress.md) | 连续 7/14/21 天达标 | MVP | PRD §六.5 + §八.5 / MVP-PRD §3.9 | M9 |
| **S10** | [我的时光相册](S10-time-album.md) | 我的 → 我的时光 | MVP(极简时间轴)/ P2(完整对比) | PRD §八.6 / MVP-PRD §3.11 | M10 |
| **S11** | [蜕变成长广场 · 轻社区](S11-square-community.md) | 任意时刻发帖 / 浏览 | MVP | PRD §七.1-2 / MVP-PRD §3.6 | M6 |
| **S12** | [个人中心 · 数据导出/注销](S12-account-privacy-data.md) | 我的 → 设置 → 隐私 / 数据 / 注销 | MVP(基础) / P1(异步导出) | PRD §九 / 架构 §5.6 | 系统级 |
| **S13** | [推送与调度服务 · 早 8 点通知](S13-push-scheduler.md) | APScheduler + 微信服务通知 | MVP | PRD §七.5.2 / 架构 §3.4 | 调度器 |
| **S14** | [合规与内容安全四层防线](S14-compliance-4layer.md) | 全产品级常驻 | MVP | PRD §二 / 架构 §5 | 系统级 |

> ⚠️ **必读配套文档**:`[00-status-and-gap.md](00-status-and-gap.md)` — 涵盖每份场景文档**未写**的"现状 / 数据库现状 / 缺口 / 下一步行动 / 用例 check"四节内容,基于 PostgreSQL MCP 实证采集 + 后端代码扫描。**建议 PM / Tech Lead 先读 00 综述,再读对应 S0X 文档。**

---

## 2.5 场景关系图与依赖矩阵(新增 · 业务 + 技术双视角)

> 本节回答两个核心问题:**(A) 用户走完一个完整旅程会经过哪些场景,场景之间的业务衔接关系是什么?(B) 这些场景在技术层(数据库 / API / Agent / 调度 / 召回)上是怎么互相调用的?**

### 2.5.1 业务视角 · 用户旅程主链路(14 场景关系全景图)

```
                  ┌──────────┐
                  │ S14 合规 │ ← 全产品级常驻(横切关注点)
                  │  四层防线 │   (被 S01-S13 任一 AI 输出 / 用户输入触发)
                  └────┬─────┘
                       │ 拦截/审查
                       ▼
[旅程起点]──S01 启动+登录+档案──► [建立用户档案]
                                    │
                                    ▼
                       S02 智能管家主页(基线问候)
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
       S03 AI 诊断            (S08 输入框)              S06 心情日记
       (三步卡)               A/B 类查询             (可选反馈)
            │                  ▲│                      │
            │ CTA              ││ 跳转                  │ 反馈素材
            ▼                  │└─S07 主动回忆          │
       S04 21天方案 ──────────►├───────── 召回 ◄────────┘
            │                  │
            ▼                  │
       S13 早8点推送(S04/S07 调度)
            │
            ▼
       S05 每日打卡闭环
            │
            ├─7/14/21 达标──► S09 抱抱卡 + 进度环
            │
            └─ 看历史 ──► S10 我的时光相册
                            │
                            ▼
[任意时刻] ──S11 蜕变广场(轻社区)──► [分享 + 治愈]
            │
            ▼
[任意时刻] ──S12 个人中心(隐私/数据导出/注销)
```

#### 业务视角 · 场景依赖矩阵(横向 = 被依赖 / 纵向 = 依赖方)

| 依赖方 \ 被依赖 | S01 登录 | S02 主页 | S03 诊断 | S04 方案 | S05 打卡 | S06 反馈 | S07 回忆 | S08 输入框 | S09 抱抱卡 | S10 相册 | S11 广场 | S12 账户 | S13 推送 | S14 合规 |
|----------------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **S01 启动**   | · |   |   |   |   |   |   |   |   |   |   |   |   | ○ |
| **S02 主页**   | △ | · |   |   |   |   |   |   |   |   |   |   |   | ○ |
| **S03 诊断**   | △ | ★ | · |   |   |   |   |   |   |   |   |   |   | ○ |
| **S04 方案**   | △ | ★ | ◉ | · |   |   |   |   |   |   |   |   | ○ | ○ |
| **S05 打卡**   | △ | ★ |   | ◉ | · |   |   |   | △ |   |   |   | ◉ | ○ |
| **S06 反馈**   | △ | ★ |   |   |   | · |   |   | △ |   |   |   |   | ○ |
| **S07 回忆**   | △ | ★ |   | ◉ |   | ◉ | · |   |   |   |   |   | ◉ | ○ |
| **S08 输入框** | △ | ★ |   |   |   |   |   | · |   |   |   |   |   | ○ |
| **S09 抱抱卡** | △ |   |   | ◉ | ◉ | ◉ |   |   | · |   |   |   | ○ | ○ |
| **S10 相册**   | △ |   |   |   |   | ◉ |   |   |   | · |   |   |   | ○ |
| **S11 广场**   | △ |   |   |   |   |   |   |   |   |   | · |   |   | ○ |
| **S12 账户**   | ◉ |   |   |   |   |   |   |   |   |   |   | · |   | ○ |
| **S13 推送**   | △ |   |   | ◉ | ◉ |   | ◉ |   | ◉ |   |   |   | · |   |
| **S14 合规**   |   |   |   |   |   |   |   |   |   |   |   |   |   | · |

图例:
- `·` 自身(行 = 列)
- `△` 业务前置(用户必须先经过)
- `◉` 业务强依赖(数据/状态直接来自)
- `★` 路由入口关系(必须在 S02 主页发起)
- `○` 系统级横切(被 S14 合规拦截/审查)

#### 业务视角 · 三条主旅程路径

**旅程 A · 新用户首次闭环(冷启动 → 诊断 → 方案 → 打卡)**
```
S01 → S02(新用户问候) → S03(三步卡) → S04(21 天方案)
   → S13(早 8:00 推 Day 1) → S05(打卡) → S09(7 天达标抱抱卡)
   → S13(Day 7 早 8:00 推主动回忆) → S07(看 7 天前自己)
```
**业务依赖说明**:S03 诊断结果 = S04 方案输入 → S05 打卡依赖 S04 的 plan_days → S09 抱抱卡依赖 S05 累计天数 → S07 主动回忆召回 S06 的 feedback 文字 + S04 的 plan_days 事实。

**旅程 B · 老用户主动回忆 + 反馈(回访路径)**
```
S01 → S02(老用户 state) → S06(心情日记)/S07(主动回忆)
```
**业务依赖说明**:S07 主动回忆必须先有 S06 的 feedback 文字记录(否则走空态 soft-tip);S07 的输入框意图 "D 类" 由 S08 SmartRouter 路由。

**旅程 C · 注销与数据导出(终态路径)**
```
S01 → S02 → S12(我的 → 设置 → 隐私/数据) → S14(异步复审)
```
**业务依赖说明**:S12 异步数据导出走 Redis 队列(由 S13 同源 Worker 消费);S14 是横切的——所有用户输入 + AI 输出都要过四层审查。

---

### 2.5.2 技术视角 · 跨场景调用关系矩阵

> 本节回答"场景 A 在技术层调用了场景 B 的哪些资产"。从五个维度拆:**数据库 schema / API / 调度器 / Agent / 数据资产**。

#### (1) 数据库 schema 依赖

| 场景 | 自身表 | 依赖其他场景的表 | 依赖原因 |
|------|------|--------------|---------|
| S01 | `users`, `login_log` | — | 用户主表 |
| S02 | `ai_sessions`, `ai_messages` | `users`, `reports`, `feedback`, `plans`, `checkins` | 聚合入口卡 state |
| S03 | `reports`, `report_uploads` | `users`, `videos` | 视频关联 |
| S04 | `plans`, `plan_days`, `videos`, `daily_push_logs` | `users`, `reports` | 基于报告生成 |
| S05 | `checkins`, `fragments` | `users`, `plans`, `plan_days` | 关联打卡 |
| S06 | `feedback` | `users`, `plans` | 关联方案 |
| S07 | `recall_sessions`(S14 `sensitive_words` 共享 / S14 `safety_audit_logs` 共享) | `feedback`, `plan_days`, `users` | 召回素材 |
| S08 | `intent_templates`, `intent_unknown_logs` | `ai_sessions`, `ai_messages` | 路由结果写消息 |
| S09 | (无新表,复用) | `checkins`, `feedback`, `users`, `plans` | 抱抱卡照片源 |
| S10 | (无新表,复用 `feedback`) | `users`, `feedback` | 时间轴查询 |
| S11 | `post`, `post_comment`, `post_audit` | `users` | 社区表 |
| S12 | `data_export_jobs`, `account_deletion_log` | 全部业务表 | 全表导出 + 删除 |
| S13 | (无新表,复用 `daily_push_logs`) | `users`, `plans`, `feedback`, `recall_sessions` | 推送目标 |
| S14 | `safety_audit_logs`, `content_blocked_logs` | 全部业务表 | 审计 |

**关键 schema 共享**:
- `ai_sessions` + `ai_messages` 是 S02 / S03 / S06 / S07 / S08 **五场景共用的对话层**——任何对话产物都写这两张表
- `feedback` 是 S06 写入,S07 / S09 / S10 三场景**只读**
- `plans` / `plan_days` 是 S04 写入,S05 / S07 / S09 / S13 **四场景只读或局部更新**
- `users` 是**全场景基表**,每张业务表都通过 `user_id` 关联

#### (2) API 依赖

| 场景 | 调用其他场景的 API | 依赖原因 |
|------|------------------|---------|
| S02 | GET `/auth/wx-login`(S01) 验证 token | JWT 校验 |
| S03 | POST `/butler/sessions/open`(S02) 复用 ai_session | 对话流 |
| S04 | POST `/diagnosis/reports/{id}/detail`(S03) 取报告 | 生成方案 |
| S05 | GET `/plans/today-task`(S04) 取今日任务 | 打卡前提 |
| S06 | POST `/butler/sessions/{id}/messages`(S02) 写回应气泡 | AI 回应 |
| S07 | POST `/butler/sessions/open`(S02) + GET `/feedback/{id}`(S06 读) | 主动回忆 |
| S08 | POST `/butler/sessions/{id}/messages`(S02) 写消息 | 路由结果落对话 |
| S09 | GET `/checkins/today`(S05) + GET `/feedback?type=plan_compare_photo`(S06) | 抱抱卡照片源 |
| S10 | GET `/feedback`(S06) 时间轴列表 | 只读 |
| S11 | POST `/butler/sessions/open`(S02) 触发"分享到广场"AI 暖评 | 接入对话 |
| S12 | GET `/auth/wx-login`(S01) + 全部表的导出 API | 全表数据导出 |
| S13 | GET `/plans/active`(S04) + GET `/feedback/{id}`(S06) + GET `/checkins/today`(S05) | 推送目标筛选 |
| S14 | 中间件拦截 S01-S13 所有 `/api/v1/*` | 横切 |

#### (3) 调度器依赖(S13 是核心调度器,S04/S07/S09 各自有内部 cron)

| 调度任务 | 触发方 | 消费方 | 技术依赖 |
|---------|-------|-------|---------|
| 早 8:00 每日任务推送 | S13 cron | S04 plan_days + S05 checkin | 写 `daily_push_logs` |
| Day 7/14/21 主动回忆 | S13 cron | S07 RecallService | 写 `recall_sessions` + `ai_messages` |
| 7/14/21 天达标抱抱卡 | S13 cron | S09 HugCardService | 触发 `ai_messages`(trigger='hug_card_invite') |
| 会话 30 分钟自动关闭 | S13 cron(每分钟) | S02 ai_sessions | UPDATE closed_at |
| 23:59 仍未打卡检测 | S13 cron | S05 persona_state | 计算 missed_1d / 2d_plus |
| ai_sessions 自动归档 | S13 cron(每日 03:00) | S12 异步导出队列 | 30 天前数据归档到 OSS cold |
| 敏感词扫描/异步复审 | S13 cron | S14 Layer 4 | 写 `safety_audit_logs` |

**S13 是中枢调度器**:S04 / S05 / S07 / S09 自身的 cron 在 MVP 阶段直接放在对应 service,但 P1+ 统一归 S13 调度,避免多源 cron 难管理。

#### (4) Agent / LLM 调用依赖

```
PersonaAgent (S02 主调度)
├── S03 DiagnosisAgent (单次多模态 LLM)
├── S05 PersonaAckService (规则模板,不调 LLM)
├── S06 FeedbackAckService (规则模板 30 条池,不调 LLM)  ← ADR-0016 强制规则
├── S07 RecallAgent (单次轻 LLM + Safety Scanner)  ← ADR-0017 100+ 敏感词
├── S08 SmartRouter (关键词优先 + 兜底 LLM)
└── S14 SafetyGuardAgent (横切 LLM-as-judge)
```

**Agent 协调规则**:
- 任何 Agent 必须先经过 S02 PersonaAgent 的入口
- S06 / S07 输出必过 S14 SafetyGuardAgent
- S07 单独还有 Recall Safety Scanner(100+ 词)
- P1+ 拆分为 LangGraph 多 Agent 子图时,PersonaAgent 作为 root

#### (5) 数据资产 / 召回关系

| 召回方 | 召回数据源 | 召回方式 | 用途 |
|------|-----------|---------|------|
| S03 诊断 | 用户档案(S01) + 历史报告(S03 自身) | SQL / P1+ Qdrant | LLM prompt 组装 |
| S04 方案 | 视频库 `videos` 表(S04) | SQL 规则匹配 | 21 天编排 |
| S06 反馈 | 用户档案(S01) + 方案(S04) | SQL | feedback 入库 |
| S07 回忆 | `feedback` 文字(S06) + `plan_days` 事实(S04) | SQL(同 active plan 时间窗) | LLM 召回 |
| S08 输入框 | `intent_templates` 关键词表 | SQL + 兜底 LLM | 意图分类 |
| S10 相册 | `feedback`(S06) | SQL 时间轴 | 只读 |
| S13 推送 | 全部业务表的活跃用户 | SQL scan | 推送目标筛选 |
| S14 合规 | 全部 AI 输出 + 用户输入 | 流式网关拦截 | 横切审查 |

---

### 2.5.3 共用模块 / 共享资产汇总(跨场景去重)

> 14 个场景中存在大量共用资产,本节明确列出,避免重复开发 + 明确单一真源。

| 共享资产 | 提供方 | 消费方(场景) | 单一真源原则 |
|---------|-------|-------------|------------|
| **`users` 表** | S01 | S02-S14 全部 | 字段定义唯一,在 S01 §3.1 |
| **`ai_sessions` + `ai_messages`** | S02 | S03/S06/S07/S08/S09/S11 | 对话层 schema 唯一,S02 §3.1 |
| **`feedback` 表** | S06 | S07(只读)/S09(只读)/S10(只读)/S13(查询) | schema 唯一,S06 §3.1 |
| **`plans` + `plan_days`** | S04 | S05/S07/S09/S13 | schema 唯一,S04 §3.1 |
| **`checkins`** | S05 | S07(只读)/S09(只读)/S13 | schema 唯一,S05 §3.1 |
| **`videos` 表** | S04 | S03/S04 自身 | schema 唯一,S04 §3.1 |
| **30 条柔性话术池** | S05 | S05/S07(空态)/S09 | 单一文件 `backend/data/persona_ack_pool.json` |
| **ADR-0017 Recall Safety 100+ 敏感词** | S14 | S07/S08(E 类)/S14(横切)/S05(分级) | 唯一表 `sensitive_words`,`category IN ('recall_judge','medical','beauty_imply','effect_commit')` |
| **APScheduler cron 调度器** | S13 | S04/S05/S07/S09(内部 cron) | P1+ 统一归 S13 |
| **微信服务通知推送通道** | S13 | S04/S07/S09 | 唯一集成 `backend/app/integrations/wx/wx_push.py` |
| **StorageFacade 抽象** | S04 | S03/S06/S07 | 唯一文件 `backend/app/core/storage_facade.py` |
| **JWT / UnionID 鉴权** | S01 | S02-S14 全部 | 中间件统一 |
| **行级 RLS** | S01(原版) | 所有用户表继承 | 模板由 S01 提供 |
| **i18n key 规范** | S01/S02/S06 联合 | S02-S13 全部 | 单一 i18n 字典 |
| **P03a 主页 UI 骨架(4 层)** | S02 | S03/S06/S07/S08 嵌入对话卡 | 单一组件 `<butler-home>` |

---

### 2.5.4 共享/依赖关系的工程风险

| 风险 | 严重度 | 触发条件 | 应对 |
|------|------|---------|------|
| **R1** `feedback` schema 变更影响 S07/S09/S10 全部只读路径 | 高 | S06 加字段 | 所有只读路径必须走 `GET /feedback` 接口(契约稳定),禁止直接改 SQL |
| **R2** S02 `ai_sessions` 是中枢,一旦 schema 变更影响 5 个场景 | 高 | S02 加字段 | 所有写入走 `POST /butler/sessions/{id}/messages`,禁止直插 |
| **R3** S13 推送通道失败 → S04/S07/S09 推送全部失败 | 中 | 微信侧配额满 | 走 wx_push 失败兜底 + 巡检阈值 5% |
| **R4** S14 安全审查阻塞输出 → 用户感知"AI 没回应" | 中 | 误拦截 | 命中 Layer 3 替换兜底文案(不空回) |
| **R5** 30 条柔性话术池被 LLM 自由生成污染 | 中(P1 后) | S06 引入 LLM 生成 | ADR-0016 强制规则:话术必须走模板池,MVP 阶段严禁 LLM 自由生成 |
| **R6** S08 SmartRouter A 类误跳转 | 中 | 关键词命中过宽 | 兜底 unknown + intent_unknown_logs 监控 |
| **R7** 跨场景强耦合(S07 依赖 S04 + S06 同时故障) | 中 | 多服务同时异常 | 主动回忆失败时走 fallback 模板 + 不影响其他场景 |

---

## 3. 文档结构(每份场景文件)

每份场景文件统一包含以下章节:

```
1. 场景定义
   - 用户是谁 / 触发条件 / 终止条件 / MVP 范围
2. 功能清单(用户可感知的每项动作)
3. 技术点拆解(每项功能对应)
   3.1 数据库脚本(DDL / 索引 / RLS)
   3.2 API 接口(请求/响应契约 + 状态码)
   3.3 调度器(Cron / APScheduler 触发)
   3.4 Qdrant 召回(若有)
   3.5 Prompt + Golden Set(若有)
   3.6 Eval 回归(若有)
   3.7 数据导出/导入(若有)
   3.8 前后端契约(字段名/类型/枚举)
   3.9 Agent 协调(参与的子 Agent)
   3.10 MCP 工具(若有)
   3.11 评测集(Golden 用例编号)
4. 实现方案
   - 服务层选型 / 关键流程图 / 异常处理
5. 预期结果
   - 性能指标 / 用户感知指标 / 成本
6. 场景用例
   - 主路径 / 异常路径 / 边界用例
7. ADR/SPEC 引用
```

---

## 4. 阅读路径

- **PM / 设计师**:直接读各场景文件 §1-§2,理解用户可感知层。
- **后端工程师**:读 §3 + §4,了解 DDL / API / 调度器 / Agent 协调。
- **AI 工程师**:读 §3.5 + §3.9 + §3.11(Prompt / Agent / Eval)。
- **前端工程师**:读 §3.8(前后端契约) + §6(场景用例)。
- **QA**:读 §6(场景用例) + §3.11(评测集)。
- **DevOps**:读 §4(部署/成本)+ §5(性能指标)。
- **Security**:读 S14 合规 + 各场景 §3.1 数据库 RLS。

---

## 5. 与真源的差异约束

| 冲突点 | 处理 |
|------|------|
| PRD V3.0 §六 vs MVP-PRD V1.3 §3.5 | 一致(M5 智能管家对话主页) |
| PRD V3.0 §七.5 vs MVP-PRD V1.3 §3.8 | 一致(M8 主动回忆) |
| PRD V3.0 §八 vs MVP-PRD V1.3 §3.7 | 一致(unified-feedback) |
| 架构 V3 vs MVP-PRD V1.3 §3 表 schema | 一致(feedback / recall_sessions / ai_sessions / ai_messages) |
| ADR 编号引用 | V3 §1-§13 提到的 ADR-0013/0014/0015/0016/0017 与架构 V3 §3.5 对齐 |

### 5.1 ADR 编号说明(P10 / P12 修复 + 全检查发现的 L1 引用问题)

真源(PRD V3.0 §文档基础信息)给出的 ADR 编号自述:**ADR-0001~ADR-0014 + 新增 ADR-0015/0016/0017**。

但 PRD/架构/MVP-PRD 中**许多 ADR 没有完整命名**(只在引用时提到主题),"占位命名"情况如下:

| ADR 编号 | PRD 真源明确? | 本文档中"沿用"的语义 | 真源建立后处理 |
|---------|------------|------------------|--------------|
| ADR-0001 | ✅ 端选型 + ✅ UnionID | 双端选型 + UnionID 跨端 + RLS 治理 | 沿用 |
| ADR-0002 | ✅ MVP 合并 2 Agent | 沿用 | 沿用 |
| ADR-0005 | ✅ 公司主体升级 | 沿用 | 沿用 |
| ADR-0006 | ✅ 不做 H5/Web | 沿用 | 沿用 |
| ADR-0007 | ❓ (PRD 自述在 0001~0014,但 0014 内是否有"21 天方案"无明确) | 本文档把"21 天单一方案 + L1 视频匹配"统一映射到 ADR-0007 | 待 `docs/adr/0007-*.md` 真正建立后,以真源 ADR 文件标题为准 |
| ADR-0008 | ❓ (未在 PRD 中显式命名) | Notification Facade(由 S13 主张) | 同上 |
| ADR-0009 | ❓ (未在 PRD 中显式命名) | 单 LLM 诊断 + Storage 抽象(S03/S06/S09 共用此名) | 同上 |
| ADR-0010 | ✅ HarmonyOS 被动上架 | 沿用 | 沿用 |
| ADR-0011 | ❓ | APScheduler 选型 | 待真源 ADR 建立 |
| ADR-0012 | ❓ | 三档柔性话术 | 同上 |
| ADR-0013 | ✅ 输入框意图分类(P3 §3.5.3) | 沿用 | 沿用 |
| ADR-0014 | ❓ | 诊断流对话化 | 同上 |
| ADR-0015 | ✅ Persona | 沿用 | 沿用 |
| ADR-0016 | ✅ Feedback Unified | 沿用 | 沿用 |
| ADR-0017 | ✅ Recall Safety | 沿用 | 沿用 |

**重要原则**:**所有 ADR 编号在场景文档中是占位命名**(沿用 PRD V3.0 自述的 0001-0017 编号边界),当 `docs/adr/ADR-000X-*.md` 实体文档建立后,需批量回填真名。冲突时以真源 ADR 实体文档为准。

**已被本文档主动修复的 ADR 编号冲突**(自查发现):
- **P4/P5 修复**:S06 / S12 之前用 "ADR-0007 UnionID Cross Platform" 与 S04 用的 "ADR-0007 21 天单一方案" 冲突 → 已统一到 **ADR-0001**(双端 UnionID 跨端更合理)
- **P6 修复**:S04 / S07 之前用 "ADR-0018 视频内容匹配" → 超出真源(PRD 自述只到 0017) → 已并入 **ADR-0007**(21 天方案 + L1 视频池 同源)

### 5.2 SPEC 编号说明(P10)

PRD V3.0 / MVP-PRD / 架构 V3 三份真源**未建立 `docs/specs/SPEC-*.md` 实体文档**。本文档集中使用的 `SPEC-M1 ~ SPEC-M12` 和 `SPEC-A0-*` 编号是**目录预留命名**,不与真源冲突(因真源没有这些 SPEC)。建立实体时按真实 SPEC 文件标题回填。

### 5.3 数据库迁移顺序(P9 修复)

本套场景文档产生的 DDL 之间存在**强前后依赖**,alembic 迁移必须按下表顺序执行(P9 修复):

| 步骤 | 迁入文件 | 依赖前序 |
|------|---------|---------|
| 0001 | S01 `users` + `login_log` | — |
| 0002 | S02 `ai_sessions` + `ai_messages` + `mv_entry_card_state` | 0001(users.id) |
| 0003 | S03 `reports` + `report_uploads` | 0001 |
| 0004 | S04 `plans` + `plan_days` + `videos` | 0001 |
| 0005 | **S13 `push_records` + `user_push_preferences` + `scheduler_jobs`(S04 的 daily_push_logs P1 修复时合并到此)** | 0001 |
| 0006 | S05 `checkins` + `fragments` | 0001, 0004 |
| 0007 | S06 `feedback_type_enum` + `body_part_enum` + `feedback` | 0001 |
| 0008 | S07 `recall_sessions` | 0001, 0004, 0007 |
| 0009 | S08 `intent_templates` + `intent_unknown_logs` | 0001, 0002 |
| 0010 | S09 `hug_card_records` | 0001, 0006 |
| 0011 | S11 `post_status_enum` + `posts` + `post_images` + `activities` | 0001 |
| 0012 | S12 `export_jobs` + `deletion_status_enum` + `account_deletions` | 0001 |
| 0013 | **S14 `audit_source_enum` + `audit_action_enum` + `violation_severity_enum` + `safety_audit_logs` + `word_category_enum` + `sensitive_words`**(S07 的 recall_violation_words 和 recall_safety_audit P1 修复时统一到此) | 0001 |
| 0014 | S12 `ALTER TABLE safety_audit_logs ADD COLUMN operation_type` | **必须在 0013 之后**,这是 P9 修复发现的依赖 |

**P1 修复路径(消除 P1/P2/P3 表名冲突)**:
1. 0005 阶段:`daily_push_logs` 表不创建;S04 改为 `INSERT INTO push_records`
2. 0013 阶段:`recall_violation_words` + `recall_safety_audit` 不创建;S07 写审计走 `safety_audit_logs(audit_source='recall')`,词条录入 `sensitive_words(category='recall_judge')`

任何本文档与真源冲突 → 以真源为准并提交修订。

---

## 6. 后续维护

- 每完成一 PR 涉及新场景能力 → 同步更新对应场景文件 §3-§4
- 新增 ADR → 更新 §7 ADR/SPEC 引用表
- 用户行为埋点数据回流 → 更新 §5 预期结果校准
- P1/P2 上线前 → 每个场景文件 §1 标 P 阶段升级

---

**索引完。**
