# SPEC-M5: 智能管家对话主页

> **版本**: V1.0  
> **日期**: 2026-07-05  
> **依赖文档**: `facts-anchor.md` (§1, §4, §7), `MVP-PRD V1.3.md` (§3.5, §3.7, §3.8)  
> **模块编号**: M5（W4 第 2 个上线，详见 facts-anchor §1：智能管家对话主页，V1.3 新增 / 重写）
> **状态**: Accepted（V1.3 locked）
> **已对齐**: facts-anchor.md V2.0 + openapi.yaml V1.1.0

---

> **文案合规基线**：[docs/design/forbidden-words.md](../design/forbidden-words.md) V1.0（≥ 50 词，6 大类）

> **视觉/原则强约束**：详见 [docs/design/design-spec.md](../design/design-spec.md) V1.1 §14（5 条合规红线 1:1 进入 Prompt）

> **IA-REF**: docs/design/ia-and-wireframe.md §4.3 P03a 智能管家对话主页（入口卡 + Chips + 输入框）

---

## 1. 模块概述

| 维度 | 内容 |
|------|------|
| 一句话定义 | 用户进入 P03a，AI 展示基线问候 + 3 入口卡 + Chips + 输入框，SmartRouter 分类 → ModuleDispatcher 派发 |
| 上线顺序 | 第 5（需 M1/M2 前置） |
| 前置依赖 | M1（登录 + 档案）、M2（智能分析） |
| 关联模块 | M7a/M7b（心情日记）、M8（主动回忆） |

---

## 2. 功能描述

### 2.1 输入

| 字段 | 说明 | 来源 |
|------|------|------|
| 用户打开 P03a | 进入智能管家对话主页 | 客户端路由 |
| 用户输入文字 | 经 SmartRouter 意图分类 | 输入框 |
| 3 入口卡点击 | 触发对应模块跳转 | UI 交互 |

### 2.2 处理

```python
# M5 输入框意图分类流程
def handle_input(user_id: str, text: str) -> ChatResponse:
    # Step 1: SmartRouter 关键词 + Mini LLM
    intent = smart_router.classify(text)  # A/B/C/D/E 五类

    # Step 2: 边界检查（E 类永远拒）
    if intent == "medical_reject":
        return medical_reject_response()

    # Step 3: ModuleDispatcher 派发
    result = module_dispatcher.dispatch(intent, user_id, text)

    # Step 4: PersonaEngine 生成温柔话术
    return persona_engine.generate_warm_response(result, intent)
```

### 2.3 输出

| 字段 | 类型 | 说明 | facts-anchor § |
|------|------|------|---------------|
| `session_id` | string | 会话 ID（ai_sessions.id） | §4 |
| `message_id` | string | 消息 ID（ai_messages.id） | §4 |
| `content` | string | AI 回复内容（≤ 4000 字） | §4 |
| `entry_card` | string | 入口卡标签 | §4 |
| `primary_intent` | string | 8 类聚合意图之一 | §4 |
| `persona_state` | string | 4 态之一 | §4 |
| `llm_cost` | decimal | LLM 调用成本 | §4 |
| `created_at` | datetime | 消息时间 | §4 |

---

## 3. 合规红线 / 关键约束

> 来源：facts-anchor §7 = PRD §3.8 = ADR-0015 §3.3

| # | 约束 | 违反动作 |
|---|------|----------|
| C1 | **不催促**："你怎么还没打卡" 永远不说 | PersonaEngine WELCOME_POOL 拦截 |
| C2 | **不打分**："你打了 80 分" 永远不算 | 30 条 ACK 模板 `_check_ack_safe` 拦截"分数/排名" |
| C3 | **不评判美丑**："你皮肤真好" 永远不说 | ACK 模板拦截"颜值/好看/白/瘦" |
| C4 | **不提数字成就**："你连续 7 天" 永远不提 | ACK 模板拦截"坚持/打卡/进步/改善" |
| C5 | **不空喊**："今天也要加油哦" 单独出现 | Client 埋点：用户未进 P03a 时不主动渲染 AI 气泡 |

### Persona 状态机（4 态）

```
warm (默认)
   ↓ 用户连续 7 天无 feedback
slight_hug ("你最近都没分享，我随时都在")
   ↓ 用户主动交互
warm
   ↓ 触发医疗/医美关键词
medical_guarded (一次触发，回到 warm)
   ↓
neutral (默认)
```

**枚举约束**（CHECK：`warm / neutral / slight_hug / medical_guarded`，ai_sessions 表约束）。

---

## 4. 技术实现

### 4.1 降级策略

| 失败场景 | 降级方案 |
|----------|----------|
| SmartRouter 识别失败 | 走 `unknown` → FALLBACK_UNKNOWN 温柔兜底 |
| Mini LLM 超时（>1.5s） | 降级为纯关键词匹配 |
| 连续 2 次 LLM 失败 | 锁定 Mini LLM，切换纯规则引擎 |
| M5 输入框误读 feedback.photo_url | 服务层 caller 白名单物理隔离（ADR-0016 §3.5） |

### 4.2 缓存策略

| 条件 | 动作 |
|------|------|
| 同一用户 5 分钟内相同输入 | 直接返回缓存 AI 回复 |
| ai_sessions.open 未关闭（< 30 分钟） | 复用现有 session |

### 4.3 成本约束

| 指标 | 目标 | 说明 |
|------|------|------|
| M5 输入框关键词 P95 | ≤ 1.5s | 纯关键词匹配路径 |
| M5 含 Mini LLM P95 | ≤ 4s | Mini LLM 调用路径 |
| 日对话量上限 | ≤ 500 次/用户 | Redis 计数器 |

### 4.4 SessionLifecycleManager（30 分钟超时关闭）

```python
class SessionLifecycleManager:
    SESSION_TIMEOUT_MINUTES = 30

    async def open_session(self, user_id: str, entry_card: str) -> str:
        # 同用户同时刻最多 1 个 open session
        existing = await self.db.query(ai_sessions).filter(
            ai_sessions.user_id == user_id,
            ai_sessions.closed_at.is_(None),
        ).first()
        if existing:
            await self.close_session(existing.id)
        session = await self.db.create(ai_sessions, {...})
        return session.id
```

### 4.5 5 类意图 ↔ primary_intent 映射（与 openapi V1.1.0 对齐）

> 原"8 类 primary_intent" 与 openapi.yaml `ActiveSessionResponse.primary_intent`（line 2183-2186 仅为 VARCHAR(32)）不一致；M5 实际只对应 **5 类 primary_intent**（其余 3 类留作 P1/P2 扩展字段）。与 `AIMessageBasic.intent`（5 类同步，见 openapi line 2108 注释）一致。

| 用户输入类 | MVP | P1 | P2 | primary_intent | openapi 对应 |
|-----------|-----|-----|-----|----------------|--------------|
| A 触发已有模块跳转 | ✅ | ✅ | ✅ | `module_redirect` | entry_card ∈ smart_analyze/mood_diary/recall_self |
| B 任务/推荐类快问 | ⚠️ 部分 | ✅ | ✅ | `read_query` | query 类快问 |
| C 心情倾诉/吐槽 | ❌ 兜底 unknown | ✅ | ✅ | `unknown` | 兜底 |
| D 主动回忆（用户主动） | ❌ 兜底 recall | ✅ | ✅ | `recall` | 触发 M8 |
| E 医疗健康提问 | ❌ 永远拒 | ❌ | ❌ | `medical_reject` | 命中医疗词 |

### 4.6 WELCOME_POOL 基线问候（7 条）

```python
WELCOME_POOL = [
    "早上好，我是小愈。今天想做什么？",
    "下午好，有什么我可以帮你的？",
    "晚上好，今天感觉怎么样？",
    "你好呀，随时可以说说你的感受。",
    "嗨，我来陪你聊聊今天的事。",
    "又见面了，今天有什么想聊的？",
    "欢迎回来，今天有什么需要？",
]
```

---

## 5. API 规范

### 5.1 POST /api/v1/assistant/chat

**描述**: 发送消息，获取 AI 管家回复

**Request**（对齐 openapi.yaml V1.1.0 `AssistantChatRequest`，line 2095-2110）：
```json
{
  "message": "帮我分析一下肩颈问题",
  "entry_card": "direct_input",
  "client_message_id": "msg-uuid-001"
}
```

**字段约束**（与 openapi 一致）：
- `message`：string，≤ 200 字（maxLength=200；openapi line 2101）
- `entry_card`：enum ∈ [`smart_analyze`, `mood_diary`, `recall_self`, `direct_input`]，默认 `direct_input`（openapi line 2105）
- `client_message_id`：string，客户端生成 UUID，用于幂等去重（openapi line 2108）

> session_id 不在请求体，由 SessionLifecycleManager 维护（详见 §4.4）。

**Response** (200):
```json
{
  "session_id": "sess_xxx",
  "message_id": "msg_xxx",
  "content": "好的，让我看看你最近的肩颈情况。你有上传过肩颈的照片吗？",
  "primary_intent": "module_redirect",
  "persona_state": "warm",
  "llm_cost": 0.001,
  "created_at": "2026-07-05T10:00:00Z"
}
```

**错误码**（详见 `docs/api/error-codes.md` §10xxx 助理章节）：
- `E_ASSISTANT_MESSAGE_INVALID`：消息内容为空或超长
- `E_ASSISTANT_RATE_LIMIT`：超过日对话量上限
- `E_ASSISTANT_MEDICAL_REJECT`：医疗关键词命中，委婉拒绝
- `E_ASSISTANT_LLM_ERROR`：4 级降级链全失败
- `E_ASSISTANT_SESSION_NOT_FOUND`：session_id 无效
- `E_ASSISTANT_SESSION_CLOSED`：session 已关闭（30 分钟超时）

### 5.2 GET /api/v1/assistant/entry-cards

**描述**: 获取用户当前的 3 入口卡状态

**Response** (200):
```json
{
  "cards": [
    {
      "card_id": "smart_analyze",
      "icon": "🔍",
      "title": "智能分析",
      "subtitle": "上传 3 张照片，生成你的养护参考",
      "state": "completed",
      "highlighted": true
    },
    {
      "card_id": "mood_diary",
      "icon": "📖",
      "title": "心情日记",
      "subtitle": "上次记录 3 天前 →",
      "state": "active",
      "highlighted": true
    },
    {
      "card_id": "recall_self",
      "icon": "💬",
      "title": "问过去的自己",
      "subtitle": "好奇几个月的你吗？",
      "state": "default",
      "highlighted": false
    }
  ]
}
```

### 5.3 GET /api/v1/assistant/sessions/active

**描述**: 获取当前用户的活跃会话

**Response** (200):
```json
{
  "sessions": [
    {
      "session_id": "sess_xxx",
      "entry_card": "direct_input",
      "primary_intent": "unknown",
      "persona_state": "warm",
      "message_count": 3,
      "started_at": "2026-07-05T09:30:00Z",
      "last_active_at": "2026-07-05T09:45:00Z"
    }
  ]
}
```

### 5.4 POST /api/v1/assistant/sessions/{id}/close

**描述**: 关闭指定会话

**Response** (200):
```json
{
  "session_id": "sess_xxx",
  "closed_at": "2026-07-05T10:00:00Z",
  "message_count": 5,
  "total_llm_cost": 0.005
}
```

---

## 6. 验收标准（Gherkin）

### Feature: 智能管家对话主页

```gherkin
Feature: 智能管家对话主页（M5 P03a）

  Scenario: 进入 P03a 主页 < 1 秒
    Given 用户点击底部 Tab "智能管家"
    Then 系统在 1 秒内展示 P03a 骨架（顶栏 + 对话流 + 入口卡 + 输入框）
    And AI 基线问候气泡已展示

  Scenario: 3 入口卡持久显示
    Given 用户进入 P03a
    Then 3 入口卡（🔍智能分析 / 📖心情日记 / 💬问过去的自己）全部展示
    And 入口卡点击后跳转到对应页面
    And 退出再进入，入口卡仍然存在（不消失）

  Scenario: A 类意图识别准确率 ≥ 85%
    Given 用户输入 "帮我分析肩颈"
    When SmartRouter 分类
    Then 识别为 module_redirect 的准确率 ≥ 85%（Golden Set 50 条）

  Scenario: A 类意图触发模块跳转
    Given 用户输入 "我想分析照片"
    When SmartRouter 分类为 module_redirect
    Then ModuleDispatcher 派发到 M2 智能分析
    And AI 回复引导用户上传照片

  Scenario: E 类意图永远拒答
    Given 用户输入 "怎么治疗颈椎病"
    When SmartRouter 命中 medical 关键词
    Then AI 回复委婉拒绝
    And 回复不含任何医疗建议
    And 记录 ai_messages.trigger = "medical_reject"

  Scenario: 未知意图走温柔兜底
    Given 用户输入 "今天心情好复杂"
    When SmartRouter 无法识别（无 Mini LLM 或超时）
    Then AI 回复温柔兜底："我没太听懂，你可以换个说法，或者从下面的入口卡点一个试试？"
    And 记录 primary_intent = "unknown"

  Scenario: AI 不在用户未进 P03a 时弹出
    Given 用户在 P02 首页 / P06 广场 / P07 我的
    Then P03a 不会主动推送任何气泡
    And 客户端埋点验证 0 次意外弹出

  Scenario: Day 7/14/21 主动推回忆气泡
    Given 用户已完成 Day 7 方案
    When 用户进入 P03a
    Then AI 主动推送回忆气泡
    And 气泡文案 "我们已经一起走了 7 天。要不要看看 7 天前的自己？"
```

### Feature: 3 入口卡状态

```gherkin
Feature: 3 入口卡状态规则

  Scenario: 未开始状态
    Given 用户刚完成登录，未做智能分析
    Then 🔍 智能分析：副文案 "上传 3 张照片，生成你的养护参考"
    And 📖 心情日记：副文案 "想记录今天的感受吗？"
    And 💬 问过去的自己：副文案 "好奇几个月的你吗？"

  Scenario: 进行中状态
    Given 用户已开始智能分析但未完成
    Then 🔍 智能分析：副文案 "补档案，完成分析" + ⭐薄荷绿描边

  Scenario: 已完成状态
    Given 用户已完成智能分析 + 21 天方案
    Then 🔍 智能分析：副文案 "查看报告 →" + ⭐薄荷绿描边
    And 💬 问过去的自己：副文案 "查看对话 →" + ⭐薄荷绿描边

  Scenario: 7 天未互动状态
    Given 用户连续 7 天未上传 feedback
    Then 📖 心情日记：副文案 "最近都没分享，要不要随便说点什么？"
```

### Feature: Persona 温柔约束

```gherkin
Feature: Persona 温柔约束

  Scenario: AI 不催促用户打卡
    Given 用户连续 3 天未打卡
    When 用户进入 P03a
    Then AI 不说 "你怎么还没打卡"
    And AI 不说 "今天要记得打卡哦"

  Scenario: AI 不打分/评判美丑
    Given 用户上传了反馈照片
    When AI 回应
    Then 不出现 "你打了 80 分"
    And 不出现 "你的皮肤变好了"
    And 不出现 "颜值/好看/瘦"

  Scenario: Persona 状态切换
    Given 用户连续 7 天无 feedback
    When 用户进入 P03a
    Then AI persona_state 切换为 slight_hug
    And AI 基线问候为 "感觉你最近没怎么分享，我随时都在。"
```

---

## 7. 关键字段映射（精简 · 完整定义见 data-dictionary.md）

> **完整字段定义见 [`docs/data/data-dictionary.md`](../data/data-dictionary.md) §1.10 `ai_sessions` 表 / §1.11 `ai_messages` 表。** 本节仅列 SPEC 重点约束字段，避免与 data-dictionary 重复维护。

### 7.1 SPEC 重点约束字段

| 字段 | 类型 | 约束 | 来源 |
|------|------|------|------|
| `ai_sessions.id` | UUID | PK | openapi `EntryCardsResponse` 隐含 |
| `ai_sessions.user_id` | UUID | FK + INDEX | data-dictionary §1.10 |
| `ai_sessions.entry_card` | VARCHAR(32) | enum ∈ [`smart_analyze`, `mood_diary`, `recall_self`, `direct_input`] | openapi.yaml line 2105 |
| `ai_sessions.primary_intent` | VARCHAR(32) | enum ∈ [`module_redirect`, `read_query`, `unknown`, `recall`, `medical_reject`]（**5 类**，非 8 类；见 §4.5） | openapi.yaml line 2183 |
| `ai_sessions.persona_state_start` | VARCHAR(32) | enum ∈ [`warm`, `neutral`, `slight_hug`, `medical_guarded`] | openapi.yaml line 2187 |
| `ai_sessions.persona_state_end` | VARCHAR(32) | 同上（4 态之一） | openapi.yaml line 2187 |
| `ai_sessions.message_count` | INT | ≥ 0 | data-dictionary §1.10 |
| `ai_sessions.total_llm_cost` | DECIMAL | 月预算 ≤ ¥700（详见 facts-anchor §4） | data-dictionary §1.10 |
| `ai_sessions.started_at` / `last_active_at` / `closed_at` | TIMESTAMPTZ | SESSION_TIMEOUT_MINUTES = 30（§4.4） | data-dictionary §1.10 |
| `ai_messages.referenced_feedback_ids` | UUID[] | M8 召回专用，普通 ACK 为 NULL | data-dictionary §1.11 |
| `ai_messages.safety_passed` | BOOLEAN | INDEX WHERE FALSE | data-dictionary §1.11 |
| `ai_messages.safety_violations` | JSONB | 违规词组记录 | data-dictionary §1.11 |

> 注：完整字段索引 / CHECK 约束 / 部分索引（`WHERE safety_passed = FALSE`）见 [data-dictionary.md §1.10-§1.11](../data/data-dictionary.md)。本 SPEC 不重复维护。

---

## 8. 交叉引用

| 类型 | 编号 | 说明 |
|------|------|------|
| **依赖** | facts-anchor.md | §1（模块编号）、§4（阈值常量）、§7（合规红线） |
| **依赖** | MVP-PRD V1.3.md | §3.5（M5 智能管家对话主页）、§3.7（M7a/M7b）、§3.8（Persona 边界） |
| **前置 SPEC** | SPEC-M1 | 极简登录 + 用户档案 |
| **前置 SPEC** | SPEC-M2 | 上传照片 + AI 联合智能分析 |
| **后续 SPEC** | SPEC-M7 | 心情日记（M7a）+ 多部位反馈（M7b） |
| **后续 SPEC** | SPEC-M8 | 主动回忆（M8） |
| **关联 ADR** | ADR-0015 | Persona 合同（温柔管家型 + 4 态状态机 + 5 条硬约束） |
| **关联 ADR** | ADR-0016 | Feedback Unified（unified-feedback 表 + 30 条 ACK 模板 + 服务层白名单） |
| **关联 ADR** | ADR-0017 | Recall Safety（三层 Safety + 100+ 敏感词库） |

---

**下一步**: 提交 W1 评审

---

## 9. SmartRouter 意图分类

> **承接来源**：PRD V1.1 §1.4.4 智能管家输入框；S08 §3.1~§3.5

### 9.1 意图分类（A~D 四类）

| 类别 | 描述 | MVP / P1 |
|------|------|---------|
| A 类 | 健康咨询（问症状/问原因） | MVP |
| B 类 | 操作指令（查打卡/查方案） | MVP |
| C 类 | 情感倾诉（倾诉情绪/寻求安慰） | P1 |
| D 类 | 越界内容（医疗/自伤/违规） | MVP |

### 9.2 A/B 类意图分类（MVP）

> **来源**：S08 §3.1 意图分类
> **TODO**：规则引擎 vs LLM 分类的技术选型
> **TODO**：`intent_templates` / `intent_unknown_logs` 表结构（从 S08 §3.1 DDL 迁移）

### 9.3 C/D 类意图分类（P1）

> **来源**：S08 §3.1 P1 升级
> **TODO**：C/D 类 LLM 分类 Prompt 设计
> **TODO**：C 类情感倾诉的兜底话术

### 9.4 API 契约（TODO）

> **来源**：S08 §3.2 API 端点
> **TODO**：以下端点待补充

| 端点 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `POST /api/v1/butler/classify` | 意图分类 | MVP A/B 类 | TODO |

### 9.5 验收标准（TODO）

> **来源**：S08 §6 场景用例
> **TODO**：以下 AC 待从 S08 §6 迁移
