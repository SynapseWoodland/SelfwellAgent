# SPEC-M6: 蜕变成长广场（轻社区）

> **版本**: V1.0  
> **日期**: 2026-07-05  
> **依赖文档**: `facts-anchor.md` (§2.6, §4), `MVP-PRD.md` (§3.6, §5.3)  
> **模块编号**: M6（W5 第 1 个上线）
> **状态**: Accepted（V1.3 locked）
> **已对齐**: facts-anchor.md V2.0 + openapi.yaml V1.1.0

---

> **文案合规基线**：[docs/design/forbidden-words.md](../design/forbidden-words.md) V1.0（≥ 50 词，6 大类）

> **视觉/原则强约束**：详见 [docs/design/design-spec.md](../design/design-spec.md) V1.1 §14（5 条合规红线 1:1 进入 Prompt）

> **IA-REF**: docs/design/ia-and-wireframe.md §4.5 P05 广场页（图文 + AI 暖评 + 分享）

---

## 1. 模块概述

| 维度 | 内容 |
|------|------|
| 一句话定义 | 用户发布图文打卡动态，经 AI + 人工审核后上墙，获得 AI 暖评和官方评论 |
| 上线顺序 | 第 6 |
| 前置依赖 | M4（每日打卡闭环） |

---

## 2. 功能描述

### 2.1 核心功能（仅做 3 件事）

> 来源：PRD §3.6.1

| # | 功能 | 说明 |
|---|------|------|
| 1 | 打卡动态发布 | 图文 + ≤ 50 字心得，每天 1 条/人上限 |
| 2 | AI 暖评 + 官方评论 | 用户发帖后 1-2 小时内预置话术池选 1 条 |
| 3 | 小红书/朋友圈分享 | 一键生成"我在慢慢变好"分享卡 |

### 2.2 明确不做

> 来源：PRD §3.6.2

| ❌ 功能 | 原因 |
|--------|------|
| 视频帖 | MVP 不做审核 |
| 点赞/转发/评论 | 避免社交压力 |
| 关注/粉丝/排行榜 | 避免任何"比较"机制 |
| 实时互动 | 避免 engagement 陷阱 |
| 树洞专区 | MVP 阶段不做 |

---

## 3. 审核流

> 来源：PRD §3.6.3

```
用户发帖
  → AI 关键词拦截（50 条敏感词 + 医疗/医美词）
  → 通过 → 进入待审核队列
  → 未通过 → 显示"我们换个表达试试？" + 友好提示
  → 人工审核（每天 5-10 篇）
  → 通过 → 上墙 + AI 暖评 + 官方评论
```

### 3.1 AI 关键词拦截

| 拦截类型 | 示例词 |
|----------|--------|
| 医疗词 | 治疗、治愈、处方、病症 |
| 医美词 | 瘦脸、割双眼皮、玻尿酸 |
| 效果承诺 | 会变白、会变小、保证瘦 |
| 颜值打分 | 打分、评分、几分 |
| 容貌比较 | 比XX好看、更美 |

### 3.2 每日发布上限

> 来源：PRD §13.3

| 约束 | 值 | 说明 |
|------|-----|------|
| 每日发帖上限 | 10 篇/天 | 全平台 |
| 单用户每日上限 | 1 篇/人 | MVP 简化 |
| 超出处理 | 自动关闭发帖功能 | 运营介入 |

---

## 4. 数据模型

| 字段 | 类型 | 说明 | facts-anchor §2.6 |
|------|------|------|-------------------|
| `id` | string | 动态主键 | ✓ |
| `user_id` | string | 关联 user | ✓ |
| `content` | string | 内容（≤ 200 字） | ✓ |
| `images` | json | 图片（≤ 9 图） | ✓ |
| `status` | enum | pending/approved/rejected | ✓ |
| `ai_comment` | string | AI 暖评 | ✓ |
| `official_comment` | string | 官方评论 | ✓ |
| `created_at` | datetime | 创建时间 | ✓ |

---

## 5. 字数约束

| 约束 | 值 | 来源 |
|------|-----|------|
| 动态内容字数 | ≤ 200 字 | PRD §6.6 / §3.6.1 |
| 打卡感想字数 | ≤ 50 字 | PRD §6.5 / §3.4.1 |
| 动态图片上限 | ≤ 9 图 | PRD §6.6 |

---

## 6. 技术实现

### 6.1 审核时效要求

| 指标 | 目标 | 来源 |
|------|------|------|
| 单帖发布到上墙 | ≤ 4 小时（95 分位） | PRD §3.6.4 |
| 敏感词拦截率 | ≥ 99% | PRD §7.2 |

### 6.2 AI 暖评话术库

> 来源：PRD §3.6.1

```python
# WARM_COMMENTS / OFFICIAL_COMMENTS 话术池
# 唯一真源：docs/data/ack-pool.yaml（同 M7 共用 ack_pool.yaml；M6 复用"AI 暖评"+"官方评论"两个分桶）
# 推荐：CI 加 build-time 校验，禁止在本 SPEC 或 M7 内嵌 ACK 文本。
```

### 6.3 合规巡检

> 来源：PRD §3.6.4

```python
def ensure_zero_compliance_violations():
    """
    验收标准：
    - 0 次出现颜值打分/医疗/容貌比较相关帖子
    """
    # 每日巡检
    daily_audit()
    
    # 任何违规自动告警
    if detect_violation(post):
        alert_运营团队(post)
```

---

## 7. API 规范

### 7.1 GET /api/v1/community/posts

**描述**: 获取动态列表

**Query Parameters**（详见 [`docs/api/pagination.md` §2](../api/pagination.md)）：

| 参数 | 类型 | 说明 |
|------|------|------|
| `limit` | int | 每页数量（默认 20，最大 50） |
| `offset` | int | 偏移量（默认 0） |
| `filter` | string | my/approved（我的/已通过） |

**Response** (200):
```json
{
  "posts": [
    {
      "id": "post_xxx",
      "user": {
        "id": "usr_xxx",
        "nickname": "小美",
        "avatar": "https://cdn.example.com/avatar.jpg"
      },
      "content": "今天完成了第 7 天的打卡，感觉肩膀轻松了很多...",
      "images": [
        "https://cdn.example.com/post/img1.jpg"
      ],
      "ai_comment": "每一步都是进步，你已经在路上了。",
      "official_comment": "感谢分享！继续保持。",
      "created_at": "2026-07-05T10:00:00Z"
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 156,
    "has_next": true
  }
}
```

### 7.2 POST /api/v1/community/posts

**描述**: 发布动态

**Request**:
```json
{
  "content": "今天完成了第 7 天的打卡，感觉肩膀轻松了很多...",
  "images": [
    "https://cdn.example.com/post/img1.jpg"
  ]
}
```

**Response** (201):
```json
{
  "id": "post_xxx",
  "status": "pending",
  "message": "发布成功，等待审核",
  "estimated_wait_time": "1-2 小时",
  "created_at": "2026-07-05T10:00:00Z"
}
```

**错误码**（详见 `docs/api/error-codes.md` §6xxx 社区章节）：

|| 业务码 | message_zh | 触发场景 |
||--------|------------|----------|
|| `E_COMPLIANCE_CONTENT_BLOCKED` | 内容包含敏感词（医疗/医美/效果承诺/颜值打分/容貌比较） | 关键词命中 |
|| `E_COMMUNITY_CONTENT_TOO_LONG` | 内容超过 200 字 | content 字段超长 |
|| `E_COMMUNITY_IMAGES_TOO_MANY` | 图片超过 9 张 | images array 长度 > 9 |
|| `E_COMMUNITY_DAILY_LIMIT_USER` | 今日已发布过动态（单用户 1 篇/天） | 当日已有 status≠rejected 动态 |
|| `E_COMMUNITY_DAILY_LIMIT_EXCEEDED` | 发帖功能已关闭（超出每日限额 10 篇/天） | 全平台当日 ≥ 10 篇 |
|| `E_GENERAL_UNAUTHORIZED` | 用户未登录 | JWT 缺失或无效 |

### 7.3 GET /api/v1/community/posts/{id}

**描述**: 获取动态详情

**Response** (200):
```json
{
  "id": "post_xxx",
  "user": {...},
  "content": "...",
  "images": [...],
  "ai_comment": "...",
  "official_comment": "...",
  "created_at": "...",
  "status": "approved"
}
```

---

## 8. 验收标准（Gherkin）

### Feature: 动态发布

```gherkin
Feature: 动态发布

  Scenario: 用户成功发布动态
    Given 用户已完成今日打卡
    And 用户进入广场页
    When 用户点击"发布"
    And 输入内容（≤ 200 字）
    And 上传图片（≤ 9 张）
    Then 动态进入待审核队列
    And 显示"发布成功，等待审核"

  Scenario: 内容包含敏感词被拦截
    Given 用户输入内容包含医疗/医美词
    When 用户点击发布
    Then 显示"我们换个表达试试？"友好提示
    And 动态不被发布

  Scenario: 字数超限被拦截
    Given 用户输入内容超过 200 字
    When 用户点击发布
    Then 显示字数超限提示
    And 不允许提交

  Scenario: 每天只能发布 1 条
    Given 用户今日已发布动态
    When 用户再次点击发布
    Then 显示"今日已发布过"
    And 不允许再次发布
```

### Feature: 审核流

```gherkin
Feature: 审核流

  Scenario: 动态发布后 1-2 小时上墙
    Given 用户动态通过人工审核
    Then 动态在 1-2 小时内上墙
    And 95 分位 ≤ 4 小时

  Scenario: 通过动态获得 AI 暖评
    Given 动态已上墙
    Then 系统从 30 条话术池选 1 条作为 AI 暖评
    And AI 暖评显示在动态下方

  Scenario: 通过动态获得官方评论
    Given 动态已上墙
    Then 系统从 30 条官方评论选 1 条
    And 官方评论显示在动态下方

  Scenario: 敏感词拦截率 ≥ 99%
    Given 平台每日新增动态
    When AI 关键词拦截
    Then 拦截率 ≥ 99%
    And 剩余 1% 靠人工兜底

  Scenario: 每日发布超 10 篇自动关功能
    Given 平台每日发布动态 ≥ 10 篇
    When 用户尝试发布
    Then 发帖功能自动关闭
    And 显示"发帖功能已临时关闭"
```

### Feature: 合规巡检

```gherkin
Feature: 合规巡检

  Scenario: 0 次出现颜值打分帖子
    Given 每日巡检
    When 检测到任何帖子包含颜值打分内容
    Then 自动告警
    And 帖子进入人工复核

  Scenario: 0 次出现医疗引导帖子
    Given 每日巡检
    When 检测到任何帖子包含医疗/医美引导
    Then 自动告警
    And 帖子立即下架

  Scenario: 0 次出现容貌比较帖子
    Given 每日巡检
    When 检测到任何帖子包含容貌比较内容
    Then 自动告警
    And 帖子进入人工复核
```

---

## 9. 关键字段映射检查表

| PRD §6.6 字段 | SPEC 字段名 | 类型 | 验证 |
|---------------|-------------|------|------|
| id | `id` | string | ✓ |
| user_id | `user_id` | string | ✓ |
| content | `content` | string (≤200字) | ✓ |
| images | `images` | json (≤9图) | ✓ |
| status | `status` | enum | ✓ |
| ai_comment | `ai_comment` | string | ✓ |
| official_comment | `official_comment` | string | ✓ |
| created_at | `created_at` | datetime | ✓ |

---

## 10. 交叉引用

| 类型 | 编号 | 说明 |
|------|------|------|
| **依赖** | facts-anchor.md | 字段定义 §2.6、字数约束 §4 |
| **依赖** | MVP-PRD.md | §3.6 功能描述、§5.3 社区发帖流程图 |
| **前置 SPEC** | SPEC-M4 | 每日打卡闭环（打卡动态入口） |
| **后续 SPEC** | SPEC-M7 | 时光相册（公开照片进入广场） |
| **关联 ADR** | ADR-0012 | 内容选品 |

---

**下一步**: 提交 W1 评审

---

## 11. 社区内容三段式审核

> **承接来源**：PRD V1.1 §1.7.4 社区审核；S11 §3.4 审核流程

### 11.1 三段式审核流程

| 阶段 | 执行方 | 时机 | 通过条件 |
|------|--------|------|----------|
| 第一段：关键词扫描 | 规则引擎 | 发布前同步 | 无违规词 |
| 第二段：采样 LLM 分类 | LLM（deepseek-flash） | 异步（< 5s） | LLM 判断为 safe |
| 第三段：人工队列 | 运营人工 | 触发阈值后 | 人工确认 |

### 11.2 审核状态机

```
draft → pending_review → approved
                      → rejected（关键词命中）
                      → rejected（LLM 判断违规）
                      → rejected（人工判定）
```

### 11.3 审核超时降级

> **TODO**：异步审核超时（5s 内未返回）时的降级策略

### 11.4 违规内容处理

| 违规类型 | 处理方式 |
|----------|----------|
| 关键词命中 | 直接拒绝，不进入 LLM |
| LLM 判定违规 | 拒绝，给出 reason |
| 人工判定违规 | 拒绝，给出 reason |

> **TODO**：违规原因的 user-facing 文案规范

### 11.5 审核日志

> **TODO**：`community_review_logs` 表结构
> **TODO**：异步审核的 APScheduler job 或队列触发机制

### 11.6 验收标准（TODO）

> **来源**：S11 §6 场景用例
> **TODO**：以下 AC 待从 S11 §6 迁移
