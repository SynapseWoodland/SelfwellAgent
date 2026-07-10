# ADR-0007: 智能管家 Vision Pipeline 拆分

**状态**: Accepted  
**日期**: 2026-07-10  
**关联方案**: [assistant-smart-analyze-vision-pipeline_5_cursor-exec-plan.md](../plan/assistant-smart-analyze-vision-pipeline_5_cursor-exec-plan.md) V5.0

---

## 1. 背景与上下文

### 1.1 问题起源

V3/V4 阶段"智能管家 vision pipeline"存在 3 类耦合问题：

1. **SSE session 独占 Bug**（V3 §3 XC-1）：`_stream_smart_analyze` 中途 `await` 时 `session.commit()` 导致并发写冲突，chat 分支与 vision 分支在同一 session 下互相踩踏
2. **多层职责耦合**（V3 §3 XC-3/4/5）：`_stream_smart_analyze` 承担了 smart_analyze 逻辑、LLM 调用、emotion 分类、token_delta 前端推送全部职责，单文件 1200+ 行无法独立测试 vision 阶段
3. **golden set 覆盖不足**（V3 §3 XC-8）：21 条老用例全部是 L1-baseline，没有任何 vision/chat SSE 用例，LLM 行为变更无法提前发现

### 1.2 V5.0 决策范围

本 ADR 记录 V5.0 方案中涉及 **架构拆分** 的 3 项核心决策：

| 决策 | 编号 | 结论 |
|------|------|------|
| Vision pipeline 架构 | D-1 | 独立 `assistant_profile` JSONB 字段 + SSE 5 阶段 progress 协议 |
| Golden Set 三层分层 | D-2 | L1-baseline（21）+ L2-vision-chat（11）+ L3-error-contract（8）= 40 条 |
| Golden Set LLM 分支拆分 | D-4 | 智能分析 → multimodal_llm（doubao-seed-2-0-lite）；对话 → text_llm（glm-4.2） |
| MCP 写权限确认 | D-3 | MCP 强制只读 → alembic 迁移走 psql 直连 |

---

## 2. 评估过的备选方案

### D-1 · Vision pipeline 架构

#### A. 原方案：单 session 多分支（保持 V3 现状）

|| 优点 | 缺点 |
|| --- | --- |
| 无需 schema 变更 | `_stream_smart_analyze` 1200+ 行单文件不可测 |
| 快速上线 | vision timeout / HEIC 白名单 / emotion 分类耦合无法独立演进 |
| — | SSE progress 无法按阶段埋点，metrics 覆盖不全 |

#### B. 拆分方案：session ownership + assistant_profile JSONB ✅

|| 优点 | 缺点 |
|| --- | --- |
| vision/chat 完全隔离，各走独立 commit | 需要 alembic 迁移（`assistant_profile` JSONB） |
| 5 阶段 SSE progress 精确埋点 | 需改 `ai_sessions` 表结构 |
| 独立超时控制（`vision_timeout_sec`） | — |
| vision 降级链与 chat 完全解耦 | — |

**结论**：采用 B。V5.0 PR-F.1/4/6 逐步落地。

---

### D-2 · Golden Set 三层分层

#### A. 保持单层 21 条

|| 优点 | 缺点 |
|| --- | --- |
| 现状 | vision/chat 新路径完全无覆盖，LLM 变更盲区 |
| 无需改 runner | — |

#### B. 渐进三层（V5.0 决策）✅

|| 优点 | 缺点 |
|| --- | --- |
| L1 零成本回归（老用例短路） | 需要扩展 runner.py `ExpectedBlock` |
| L2 draft 可在 PR-F 实施中逐步回填 | L2 11 条用例有 `<TODO>` 占位符 |
| L3 E_CODE 契约精确匹配 | 需要 mock 端替身 |

**结论**：采用 B。baseline v2-three-layer 骨架已落地，Phase 1 实施完成后回填 L2。

---

### D-3 · MCP 写权限

#### A. MCP 可写（V4.1 假设）

|| 优点 | 缺点 |
|| --- | --- |
| alembic 迁移可走 MCP | **实测：MCP 强制 `BEGIN READ ONLY`，无法突破** |

#### B. MCP 只读 + psql 直连 ✅（子任务 1 实测）

|| 优点 | 缺点 |
|| --- | --- |
| 实测确认 MCP tx_ro=on | 需要本机有 psql 客户端（Win 默认无） |
| DSN 明确：`postgresql://selfwell:change_me_in_dev_only@localhost:5432/selfwell` | — |

**结论**：采用 B。实施 P1 探测记录 + P2/P3 回退路径。

---

### D-4 · Golden Set LLM 分支拆分

#### A. 单一 LLM 配置（保持原状）

| 优点 | 缺点 |
| --- | --- |
| 现状，无需改动 | **智能分析（vision）强制走文本 LLM**，无法利用多模态能力 |
| | golden set 无法区分场景，eval 行为非确定 |

#### B. 双 LLM 分支（本次决策）✅

| 优点 | 缺点 |
| --- | --- |
| 智能分析场景 → `multimodal_llm`（doubao-seed-2-0-lite-260428） | 需要在用例层声明 `llm_capability` 字段 |
| 对话场景 → `text_llm`（glm-4.2） | 需在 runner.py Case dataclass 增加字段 |
| L2-vision-chat 5 条用例走 multimodal，35 条走 text，语义清晰 | — |
| 真值来自 `.env`（68-70 行 multimodal，78-80 行 text） | — |

**结论**：采用 B。golden_set_v1.yaml metadata 更新 + 40 条用例 `llm_capability` 打完（text×35, multimodal×5）。

---

## 3. 决策

### D-1: Vision pipeline 架构拆分

```
ai_sessions 表新增 assistant_profile JSONB 字段：

{
  "vision_enabled": true,
  "last_vision_at": "2026-07-10T10:00:00Z",
  "vision_model": "doubao-vision-1.5",
  "vision_timeout_sec": 30.0,
  "persona_state": "warm"
}
```

**SSE 5 阶段 progress 协议**（与 `docs/api/sse-events.md` 对齐）：

```
阶段 1: progress {"stage": "analyzing_photos", "message": "正在分析照片..."}
阶段 2: progress {"stage": "calling_vision_llm", "message": "正在调用视觉模型..."}
阶段 3: progress {"stage": "summarizing", "message": "正在生成摘要..."}
阶段 4: progress {"stage": "calling_text_llm", "message": "正在生成报告..."}
阶段 5: done {"result": {...}}
```

**Vision 三级降级链**（来自子任务 1 §F.2）：

```
P1: Vision LLM (doubao-vision) → P2: Rule Engine (body-parts.yaml) → P3: Fallback ACK 模板
```

### D-2: Golden Set 三层分层

```
Layer 1 (L1-baseline): 21 条 —— V1 稳定路径，expected.code=None → _code_matches 短路
Layer 2 (L2-vision-chat): 11 条 —— V4.1 新增路径，含 <TODO: from V4.1 Step X.Y> 占位
Layer 3 (L3-error-contract): 8 条 —— E_CODE 原子契约，精确匹配 error.code + http_status
Total: 40 条
```

**baseline.json 回填三阶段**：

| 阶段 | 触发 | 动作 |
|------|------|------|
| Phase A（当前） | 三层合并 | 写 v2-three-layer 骨架，cases=[] |
| Phase B | PR-F 任一步合入 | `uv run python -m eval.runner --mode daily` |
| Phase C | Phase B 跑通 | 读 results/*.json → 回填 baseline.cases[] |

### D-3: MCP 只读 + 三级回退

```
P1: MCP query 试写（确认只读）→ P2: psql 直连（若 psql 有）→ P3: 人工 SQL
```

### D-4: Golden Set LLM 分支拆分

golden_set_v1.yaml metadata 更新为双分支结构：

```
智能分析场景（vision pipeline）:
  llm_multimodal_model:      "doubao-seed-2-0-lite-260428"
  llm_multimodal_base_url:   "https://ark.cn-beijing.volces.com/api/plan/v3"
  llm_multimodal_api_key_ref: null   # 安全原则：API key 不写入 git
                                     # 运行时由 runner.py 从 .env 读取，注入到 LLM 客户端

对话场景（chat pipeline）:
  llm_text_model:       "glm-4.2"
  llm_text_base_url:   "https://ark.cn-beijing.volces.com/api/plan/v3"
  llm_text_api_key_ref: null         # 同上，从 .env 读取

通用参数:
  llm_temperature: 0.7
  llm_max_tokens: 2048
  llm_monthly_budget_yuan: 700
```

> **安全原则**：API key 永远不写入 git 管理的配置文件（包括 golden_set_v1.yaml、baseline.json）。真值从 `.env` 读取，`.env` 本身在 `.gitignore` 中。

40 条用例 `llm_capability` 分布：

| 能力 | 用例数 | 场景 |
|------|--------|------|
| text | 35 | L1-baseline(21) + L2 CHAT/CROSS(9) + L3(8) |
| multimodal | 5 | L2 GN-ASSISTANT-VISION-001~005 |

---

## 4. 技术实现要点

### 4.1 alembic migration 三级回退流程

```markdown
## 6.2 Alembic 失败 → 三级回退执行记录
### 失败信息
- 失败时间: YYYY-MM-DD HH:MM
- alembic 命令: `alembic upgrade head`
- 报错原文（前 30 行）: <贴 alembic 报错>

### P1 · MCP `query` 试写探测
- 工具: `user-user-postgres::query`
- 调用 SQL: `CREATE TEMP TABLE _mcp_write_probe (id int);`
- 返回: `{"error": "MCP error -32603: cannot execute CREATE TABLE in a read-only transaction"}`
- 判定: ❌ MCP 强制 read-only 事务，降级到 P2

### P2 · psql 直连执行（如使用）
- 客户端探测: `where psql` → (空) → 降级到 P3
- 或: psql 已安装 → 命令: `psql "..." -f <DDL>.sql`

### P3 · 人工 SQL 兜底（如使用）
- 执行方式: ☐ psql / ☐ IDE DB / ☐ docker exec
- 执行人 / 时间 / 完整 SQL / stdout / stderr / 截图
```

### 4.2 envelope 错误响应（L3 契约层）

所有 router 层错误统一走 `AppBusinessError` → `ErrorEnvelope`：

```python
# 响应 shape
{
  "error": {
    "code": "E_ASSISTANT_MEDICAL_REJECT",  # 118 码之一
    "message_zh": "医疗相关问题我无法回答...",
    "message_en": "Medical queries are outside my scope...",
    "request_id": "abc123...",
    "details": null
  }
}
```

**8 条 L3 E_CODE 契约**（GN-ERR-001~008）：

| ID | code | http_status | 说明 |
|----|------|-------------|------|
| GN-ERR-001 | E_ASSISTANT_MEDICAL_REJECT | (200) | 业务拦截 |
| GN-ERR-002 | E_GENERAL_RATE_LIMIT | 429 | 限流 |
| GN-ERR-003 | E_UPLOAD_INVALID_CONTENT_TYPE | 400 | HEIC 等 |
| GN-ERR-004 | E_FEEDBACK_DAILY_LIMIT | 429 | 反馈上限 |
| GN-ERR-005 | E_RECALL_DAILY_LIMIT | 429 | 回忆上限 |
| GN-ERR-006 | E_COMPLIANCE_MEDICAL_CLAIM | 200/400 | 合规拦截 |
| GN-ERR-007 | E_ASSISTANT_SESSION_NOT_FOUND | 404 | 会话不存在 |
| GN-ERR-008 | E_ASSISTANT_SESSION_CLOSED | 410 | 会话已关闭 |

---

## 5. 后果

### 5.1 正面

- **Vision pipeline 独立演进**：assistant_profile JSONB 解耦 vision 配置与 chat 逻辑
- **Golden Set 覆盖 vision 路径**：40 条用例中 11 条 L2 覆盖新 vision/chat SSE 场景
- **错误契约可测**：8 条 L3 E_CODE 精确匹配，mock 替身避免依赖真实 LLM
- **Alembic 迁移有明确回退路径**：P1/P2/P3 三级，避免迁移卡死

### 5.2 负面 / 风险

| 风险 | 应对 |
| --- | --- |
| L2 11 条 `<TODO>` 占位符在 PR-F 实施完成前 runner 会短路失败 | Phase B 先跑 L1+L3（29 条），L2 等 PR-F.1~F.5 逐步回填 |
| `assistant_profile` JSONB 无 schema validation | PR-F.1 期间加 Pydantic schema |
| psql 客户端在 Windows 默认不存在 | P3 人工 SQL 兜底；或告知开发者装 `choco install postgresql` |

---

## 6. 何时推翻 / 重审

| 触发条件 | 重新评估 |
| --- | --- |
| Vision LLM 模型换成非字节系（doubao → GPT-4V） | `vision_model` 配置需重新对标 timeout 阈值 |
| Golden Set 规模超过 200 条 | 分层策略保持，按 domain 再切 sub-layer |
| MCP 协议更新支持写事务 | P1 可降级为首选，P2/P3 降为备用 |

---

## 7. 参考

- [V5.0 执行方案](../plan/assistant-smart-analyze-vision-pipeline_5_cursor-exec-plan.md)
- [V5.0 大纲](../plan/assistant-smart-analyze-vision-pipeline_5_outline.md)
- [子任务 1: F.2 MCP 写权限探测](../plan/v4.1-prep/01-f2-mcp-write-probe.md)
- [子任务 2: Golden 三层合并](../plan/v4.1-prep/02-golden-three-layer.md)
- [子任务 3: 基建文件 + 锚点](../plan/v4.1-prep/03-infra-and-anchors.md)
- [子任务 4: Error envelope](../plan/v4.1-prep/04-error-envelope.md)
- [Golden Set](../backend/eval/golden_set_v1.yaml) v2.0.0-three-layer
- [Baseline v2-three-layer](../backend/eval/baseline.json)
