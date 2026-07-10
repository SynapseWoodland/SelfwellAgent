# SPEC-M11: 智能管家 Vision Pipeline

> **版本**: V1.0  
> **日期**: 2026-07-10  
> **依赖文档**: `facts-anchor.md` (§4, §7), `MVP-PRD V1.3.md` (§3.5, §3.8)  
> **模块编号**: M11（W5 横切能力，详见 facts-anchor §1：智能管家 vision pipeline 拆分，V5.0 新增）
> **状态**: Accepted（V5.0 locked）
> **已对齐**: facts-anchor.md V2.0 + openapi.yaml V1.1.0 + ADR-0007

---

> **文案合规基线**：[docs/design/forbidden-words.md](../design/forbidden-words.md) V1.0（≥ 50 词，6 大类）

> **IA-REF**: docs/design/ia-and-wireframe.md §4.3 P03a 智能管家对话主页（vision 上传入口）

---

## 1. 模块概述

|| 维度 | 内容 |
|------|------|
| 一句话定义 | 用户上传 1~3 张照片，AI 管家经 5 阶段 SSE 流式输出 smart_analyze 报告，涵盖视觉分析 + LLM 摘要 + 养护建议 |
| 上线顺序 | W5 横切能力（与 M5 智能管家对话主页并行，V5.0 新增） |
| 前置依赖 | M1（登录 + 档案）、M5（智能管家对话主页） |
| 关联模块 | M5（对话入口）、M2（智能分析，共享 vision LLM） |

---

## 2. 功能描述

### 2.1 输入

|| 字段 | 说明 | 来源 |
|------|------|------|
| 用户上传照片 | 1~3 张，`image/jpeg` / `image/png` / `image/webp` / `image/heic` | P03a 上传入口 |
| 用户输入文字（可选） | 附注说明（如"最近肩颈酸痛"） | P03a 输入框 |
| session_id | 复用 M5 会话，ai_sessions 表 | 客户端传入 |

### 2.2 处理（SSE 5 阶段）

```
用户提交照片
    ↓
阶段1: analyzing_photos —— 分析照片格式/尺寸/光照
    ↓
阶段2: calling_vision_llm —— 调用 vision LLM（doubao-vision-1.5）
    ↓ 超时 30s 降级
    ↓ 降级链 P2: rule_engine_fallback → P3: ACK 模板兜底
    ↓
阶段3: summarizing —— 视觉分析结果汇总
    ↓
阶段4: calling_text_llm —— 调用 text LLM 生成养护报告
    ↓
阶段5: done —— 推送完整报告结构
```

### 2.3 输出（SSE event）

|| event | 字段 | 说明 |
|------|-------|------|------|
| `progress` | `stage` | 阶段名 |
| `progress` | `message` | 用户可见中文消息 |
| `progress` | `token_delta` | 前端 token 增量（用于 UI 打字机效果） |
| `done` | `result.summary` | 养护摘要（≤ 500 字） |
| `done` | `result.tags[]` | 标签列表 |
| `done` | `result.advice` | 养护建议（≤ 800 字） |
| `error` | `code` / `message_zh` | 错误信封（L3 E_CODE） |

---

## 3. 合规红线 / 关键约束

> 来源：facts-anchor §7 = ADR-0007 §4 = ADR-0015 §3.3

|| # | 约束 | 违反动作 |
|---|------|----------|
| C1 | **不提供医疗诊断**："根据照片判断你可能患有..." 永远不说 | Vision LLM Prompt 硬约束 + ACK 模板拦截 |
| C2 | **不说"会变小/会变白"** | ACK 模板拦截"变小/变白/瘦"类承诺 |
| C3 | **不说"你的皮肤真好"等评判美丑** | ACK 模板拦截"好看/颜值/美人" |
| C4 | **Vision LLM 超时 30s 强制降级**（不无限等待） | `asyncio.wait_for` + `vision_timeout_sec=30.0` 配置 |
| C5 | **HEIC 格式必须支持**（iOS 14+ 默认格式） | uploads_v1 白名单加 `image/heic` MIME |

### 3.1 Vision LLM 超时三级降级链

```
P1: doubao-vision-1.5 (默认)
    ↓ vision_timeout_sec=30s
P2: rule_engine_fallback (body-parts.yaml 专家规则)
    ↓ LLM 兜底
P3: Fallback ACK 模板 ("收到你的照片，我会持续学习，期待下次一起看看变化！")
```

### 3.2 照片上传约束

|| 字段 | 约束 | 来源 |
|------|------|------|
| 照片数量 | 1~3 张 | facts-anchor §4 |
| 单张大小 | ≤ 10 MB | openapi.yaml V1.1.0 |
| 格式 | `image/jpeg` / `image/png` / `image/webp` / `image/heic` | V5.0 新增 |
| body_parts | ∈ [`face`, `neck`, `shoulder_left`, `shoulder_right`, `back`, `arm_left`, `arm_right`, `hand_left`, `hand_right`, `leg_left`, `leg_right`, `foot_left`, `foot_right`] | body-parts.yaml |

---

## 4. 技术实现

### 4.1 LLM 配置（双分支）

智能分析场景走 `multimodal_llm`（多模态大模型），对话场景走 `text_llm`（文本大模型），真值来自 `.env`：

| 场景 | LLM 分支 | 模型 | 来源 |
|------|----------|------|------|
| 智能分析（vision） | `multimodal_llm` | `doubao-seed-2-0-lite-260428` | `.env` §MULTI_MODEL（69 行） |
| 对话（chat） | `text_llm` | `glm-4.2` | `.env` §MODEL（79 行） |

Golden Set 关联：`llm_capability = "multimodal"` 标记 5 条 vision 用例，其余 35 条走 `text`。

### 4.2 存储字段（assistant_profile JSONB）

```sql
ALTER TABLE ai_sessions ADD COLUMN assistant_profile JSONB DEFAULT '{}';

-- 写入结构
{
  "vision_enabled": true,
  "last_vision_at": "2026-07-10T10:00:00Z",
  "vision_model": "doubao-vision-1.5",
  "vision_timeout_sec": 30.0,
  "persona_state": "warm"
}
```

### 4.3 路由端点

|| 端点 | 方法 | 说明 |
|------|------|------|------|
| `/api/v1/assistant/sessions/{id}/smart_analyze` | POST | 触发 vision pipeline |
| `/api/v1/assistant/smart_analyze/stream` | GET | SSE 流式输出（5 阶段 progress + done） |

### 4.4 Metrics 埋点

|| 指标 | 类型 | Labels |
|------|------|------|--------|
| `selfwell_smart_analyze_done_total` | Counter | `is_mock` |
| `selfwell_smart_analyze_failed_total` | Counter | `stage` |
| `selfwell_smart_analyze_duration_seconds` | Histogram | buckets: 1/5/10/30/60s |
| `selfwell_vision_latency_seconds` | Histogram | `model`, `outcome` |

### 4.5 限流

Per-user sliding window log（Redis ZSET Lua 脚本）：

```
key = ratelimit:smart_analyze:{user_id}
limit = 30 次 / 60 秒
超出 → 429 + Retry-After + E_ASSISTANT_RATE_LIMIT envelope
```

---

## 5. API 规范

### 5.1 POST /api/v1/assistant/sessions/{id}/smart_analyze

**描述**: 上传照片，触发 smart_analyze vision pipeline

**Request**：
```json
{
  "photo_urls": [
    "https://cdn.selfwell.com/photos/abc123.jpg"
  ],
  "body_parts": ["shoulder_left", "shoulder_right"],
  "note": "最近肩颈酸痛"
}
```

**Response** (200): 无 body，SSE 流式输出

**错误码**：
- `E_ASSISTANT_SESSION_NOT_FOUND` (404): session 不存在
- `E_ASSISTANT_SESSION_CLOSED` (410): session 已关闭
- `E_ASSISTANT_RATE_LIMIT` (429): 限流
- `E_UPLOAD_INVALID_CONTENT_TYPE` (400): 不支持的图片格式

### 5.2 SSE Event 流协议

```typescript
// Client 订阅
GET /api/v1/assistant/smart_analyze/stream?session_id=xxx

// Server 推送
event: progress
data: {"stage": "analyzing_photos", "message": "正在分析照片...", "token_delta": 5}

event: progress
data: {"stage": "calling_vision_llm", "message": "正在调用视觉模型...", "token_delta": 12}

event: progress
data: {"stage": "summarizing", "message": "正在生成摘要...", "token_delta": 8}

event: progress
data: {"stage": "calling_text_llm", "message": "正在生成报告...", "token_delta": 15}

event: done
data: {"result": {"summary": "...", "tags": ["肩颈", "体态"], "advice": "..."}}

event: error
data: {"error": {"code": "E_ASSISTANT_VISION_TIMEOUT", "message_zh": "视觉分析超时，使用简化模式生成报告"}}
```

---

## 6. 验收标准（Gherkin）

### Feature: Vision Pipeline 5 阶段流式输出

```gherkin
Feature: Vision Pipeline 5 阶段流式输出（M11）

  Scenario: 照片上传后 5 阶段 SSE progress 依次推送
    Given 用户在 P03a 上传 3 张肩颈照片
    When 调用 /api/v1/assistant/smart_analyze/stream
    Then 收到 4 个 progress event（analyzing_photos → calling_vision_llm → summarizing → calling_text_llm）
    And 最后收到 1 个 done event
    And 所有 progress.message 含中文用户可读消息

  Scenario: Vision LLM 超时 30s 降级
    Given vision LLM 响应超过 30s
    Then 自动降级到 rule_engine_fallback
    And 推送 error event 含 E_ASSISTANT_VISION_TIMEOUT
    And 不阻塞 SSE 流，最终仍返回 done

  Scenario: HEIC 格式支持
    Given 用户上传 iPhone 照片（image/heic）
    When 系统处理
    Then 不返回 E_UPLOAD_INVALID_CONTENT_TYPE
    And 正常进入 analyzing_photos 阶段

  Scenario: Per-user 限流
    Given 单用户 60 秒内请求超过 30 次
    When 发送第 31 次请求
    Then 返回 429 envelope 含 E_ASSISTANT_RATE_LIMIT
    And 响应头含 Retry-After

  Scenario: Session 关闭后拒绝
    Given ai_sessions.closed_at 已设置
    When 调用 smart_analyze
    Then 返回 410 envelope 含 E_ASSISTANT_SESSION_CLOSED
    And 不触发任何 LLM 调用
```

### Feature: Vision 合规约束

```gherkin
Feature: Vision 合规约束

  Scenario: Vision 不输出医疗诊断
    Given 用户上传照片 + "帮我看看是不是颈椎病"
    When Vision LLM 分析
    Then AI 回复不含"判断你可能患有" / "确诊" / "治疗方案"
    And 回复落地在"养护参考"而非"医疗诊断"

  Scenario: Vision 不承诺美丑变化
    Given 用户上传皮肤照片
    When AI 回应
    Then 不含"会变白" / "会变小" / "颜值提升"
    And 使用"期待下次一起看看变化"类 ACK 兜底
```

---

## 7. 关键字段映射

|| 字段 | 表 | 类型 | 约束 |
|------|------|------|------|
| `ai_sessions.id` | ai_sessions | UUID | PK |
| `ai_sessions.assistant_profile` | ai_sessions | JSONB | V5.0 新增，含 vision 配置 |
| `ai_sessions.vision_model` | - | VARCHAR | 由 assistant_profile.vision_model 读 |
| `ai_sessions.last_vision_at` | - | TIMESTAMPTZ | 由 assistant_profile.last_vision_at 读 |
| `ai_messages.photo_urls` | ai_messages | VARCHAR[] | 本次分析引用的照片 |
| `ai_messages.is_vision_analysis` | ai_messages | BOOLEAN | 是否为 vision 分析结果 |

---

## 8. 交叉引用

|| 类型 | 编号 | 说明 |
|------|------|------|
| **前置 SPEC** | SPEC-M5 | 智能管家对话主页（vision 入口在 M5 P03a） |
| **依赖** | ADR-0007 | Vision pipeline 拆分决策记录 |
| **依赖** | facts-anchor.md | §4（超时阈值）、§7（合规红线） |
| **关联** | docs/api/sse-events.md | SSE 事件 schema，5 阶段定义 |
| **关联** | docs/api/error-codes.md | 118 码，10xxx ASSISTANT 章节 |
| **关联** | docs/data/body-parts.yaml | 13 部位枚举 |

---

**下一步**: V5.0 Phase 1 实施（PR-F.1~F.6）
