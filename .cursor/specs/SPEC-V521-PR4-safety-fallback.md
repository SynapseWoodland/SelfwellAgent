---
title: V5.2.1-PR4 · 双路径 safety_passed 真值 + smart_analyze medical_reject 短路 + fallback 缺料标记（is_fallback）
id: SPEC-V521-PR4-safety-fallback
version: 1.0.0
status: Accepted
date: 2026-07-11
owner: backend-architect
related_pr: V5.2.1-PR4
parent_plan: docs/plan/assistant-smart-analyze-vision-pipeline_5.2.1_unified-bugfix-plan.md §3.8/§3.9/§3.10 + §11.2 周三 timeline
predecessor: V5.2.1-PR3 (commits d700d04 / 5896282 / 94b68d6)
successor: V5.2.1-PR5 (frontend profile 320 行 + body profile 字段 + 缺料阻断)
---

> ⚠ 本 SPEC 在 V5.2.1 §4.4 基础上**追加 §3 增量 F4**（来自 PR3 evidence `pr3-llm-output-analysis.md §5.2 微调 1`）：
> fallback 不返假报告，新增 `is_fallback=true` + `fallback_reason` 字段，前端识别后不渲染 report card。

## 文案合规基线

- 海报文案：**N/A**
- 业务文案：fallback summary 不再返 "已为您生成基础养护方向"，改为 `is_fallback=true` + `fallback_reason="资料不足"`；safety/medical_reject 文案沿用 `app/errors/codes.py` 现有错误码
- 错误文案：沿用 `app/errors/codes.py` 现有错误码（`E_ASSISTANT_MEDICAL_REJECT` 已存在）

## IA-REF

- 所属 IA：assistant safety / medical_reject / fallback
- 上一跳 SPEC：V5.2.1-PR3-sse-cost-adr
- 下一跳 SPEC：V5.2.1-PR5-frontend-contract（缺料阻断）

## 强关联真源表（已读依赖）

| 文件路径 | 用途 | PR4 行动 |
|---|---|---|
| `backend/app/services/assistant_service.py:707` | `_stream_smart_analyze` smart_analyze 路径 profile dict | **T20 改**：调 `_check_text_safety(text)` → smart_analyze AIMessage 真值 |
| `backend/app/services/assistant_service.py:782-800` | smart_analyze AIMessage 落库（**缺 safety_passed 字段**）| **T20 改**：补 `safety_passed=safety_passed` 字段 |
| `backend/app/services/assistant_service.py:1231` | chat 路径 AIMessage `safety_passed=True` 硬编码 | **T20 改**：调 `_check_text_safety(text)` → 真值 |
| `backend/app/services/assistant_service.py:694-707` | `_stream_smart_analyze` 入口（profile 构造前）| **T21 改**：在 `:707` 前 early return medical_reject 短路（chat 路径已有 `:1128`，smart_analyze 路径补全） |
| `backend/app/services/assistant_service.py:1127-1156` | chat 路径 medical_guarded 短路模板（`to_state == "medical_guarded"` → 返 `_FALLBACK_BY_STATE["medical_guarded"][0]`）| **T21 参照**：smart_analyze 路径复用同模式（short-circuit + audit_persona_state_switch + error SSE 帧 + 不返 directions） |
| `backend/app/services/diagnosis_service.py:53` | `_check_text_safety(text)` 真值（compliance.checker.check_input 封装）| **T20 import 复用**：双路径都从这 import |
| `backend/app/services/diagnosis_service.py:534-551` | `_rule_engine_fallback` 当前输出 "已为您生成基础养护方向" 假报告 | **T22 改**：fallback 不返假报告，改为 `is_fallback=true` + `fallback_reason="资料不足"` + 空 directions + 空 tags |
| `backend/app/services/assistant_service.py:839-855` | end event 7 字段 schema（含 `medical_guarded: False`）| **T21 改**：medical_reject 短路时返 `medical_guarded: True` |
| `backend/app/services/assistant_service.py:841` | `medical_guarded = False` 占位（PR3 标注 "PR4 T20 改安全检查真值"）| **T20 改**：根据 `_check_text_safety(text).passed` 真值赋值（chat 路径）|
| `backend/app/errors/codes.py:162` | `E_ASSISTANT_MEDICAL_REJECT = "E_ASSISTANT_MEDICAL_REJECT"` | **T21 import 复用**：smart_analyze 路径 medical_reject 短路返这个 code |
| `backend/app/core/audit.py` | `audit_persona_state_switch` + `hash_user_id_pseudo` | **T20/T21 复用**：合规审计 3 事件之一（ADR-0015 §2.4.4） |
| `docs/plan/evidence/pr3-llm-output-analysis.md §5.2 微调 1` | PR3 后增量需求：fallback is_fallback + fallback_reason | **F4 直接落地** |
| `docs/architecture/adr/0007-vision-pipeline-split.md` | 已 sync 字段名（PR3） | — |
| `docs/architecture/sse-events.md §5` | assistant 域 SSE 契约（PR3 已追加）| **PR4 不改**（schema 没变；新字段 `is_fallback`/`fallback_reason` 在 end event payload 内，§5 已写 end 字段"可选扩展"） |

## 1. 目标（Goal）

完成 V5.2.1 §3.8/§3.9/§3.10 + PR3 evidence §5.2 微调 1 共 4 项：

1. **T20 chat :1231 + smart_analyze :782-800 safety_passed 真值**：双路径统一调 `_check_text_safety`（来自 `diagnosis_service.py:53`），不再硬编码 `True`
2. **T21 smart_analyze 路径补 medical_reject 短路**：在 `:707` 前加 `_check_text_safety(text)` 早返，返 SSE error 帧 + audit_persona_state_switch + 不再 yield 后续 progress/report/end
3. **T22 fallback summary 改字段**：`_rule_engine_fallback` 不再返假报告（"已为您生成基础养护方向"），改为 `is_fallback=true` + `fallback_reason="资料不足"` + directions=[] + tags=[]（前端识别后不渲染 report card）
4. **F4 SSE end event payload 透传 is_fallback 标记**：`_stream_smart_analyze` 在 fallback 路径时 end event 加 `is_fallback=true` + `fallback_reason` 字段（前端不渲染 report card）

## 2. 范围（Scope）

### 2.1 IN（PR4 必交付）

| # | 任务 | 文件 | 行号预估 |
|---|------|------|---------|
| T20 | chat 路径 `:1231` 改 `_check_text_safety(text).passed` 真值；smart_analyze 路径 `:782-800` AIMessage 补 `safety_passed` 字段（同样调 `_check_text_safety`）| `assistant_service.py` 2 处 | +6 行 |
| T21 | smart_analyze `:707` 前 medical_reject 短路（调 `_check_text_safety(text)`，命中则 early return SSE error 帧 + audit_persona_state_switch）| `assistant_service.py:707` 前 | +20 行 |
| T22 | `_rule_engine_fallback` 改返回结构：`{"is_fallback": True, "fallback_reason": "资料不足", "directions": [], "tags": [], "summary": "请先补充档案与图片后再进行智能分析。"}`（不再假报告）| `diagnosis_service.py:534-551` | 重写 ~20 行 |
| F4 | `_stream_smart_analyze` 在 `_invoke_llm_structured` 返 fallback 时，end event payload 加 `is_fallback=true` + `fallback_reason` 字段；前端按 §5.2 协议不渲染 report card | `assistant_service.py:847-855` + `_rule_engine_fallback` 调用方 | +8 行 |
| Test | `tests/unit/services/test_vision_safety_chat.py`（2 测：合规/不合规双路径）| 新建 | ~80 行 |
| Test | `tests/unit/services/test_vision_safety_smart.py`（2 测：合规 + medical_reject 短路）| 新建 | ~80 行 |
| Test | `tests/unit/services/test_vision_fallback_personalize.py`（2 测：T22 字段真值 + F4 end event payload 含 is_fallback）| 新建 | ~80 行 |
| Test | `tests/unit/services/test_vision_medical_reject_smart.py`（1 测：smart_analyze 路径触发 medical_reject 短路，error 帧 + 后续 progress/report 不 yield）| 新建 | ~70 行 |
| Doc | `docs/architecture/sse-events.md §5` 增 §5.5「fallback 协议」（可选小节）：end event payload 可选字段 `is_fallback` + `fallback_reason` 说明 | `docs/architecture/sse-events.md` | +~30 行 |

### 2.2 OUT（PR4 不做）

- T23/T24 前端档案页 + body profile（PR5）
- F5 上传三步卡缺料阻断（PR5 §5.2.1-3 微调 2）
- T25 会话历史（PR6）
- PR7 验收
- ADR-0015 / 0017 / 0019 主条款不动
- ADR-0007 不动（PR3 已 sync）
- `_check_text_safety` 函数本身不动（`diagnosis_service.py:53` 已实现）

## 3. 验收标准（Gherkin AC）

### 3.1 AC-T20-1：chat 路径 safety_passed 真值

- **Given** chat 路径 `_stream_chat`（assistant_service.py 第 9 段函数）
- **When** 输入"我最近脖子有点酸"（合规文本）
- **Then** `AIMessage.safety_passed == True`（落库 ai_messages 表）

### 3.2 AC-T20-2：chat 路径 medical_reject 真值

- **Given** chat 路径 `_stream_chat`
- **When** 输入"我能不能去打玻尿酸瘦脸"（命中医疗关键词）
- **Then** `_classify_intent` 路由到 `to_state == "medical_guarded"` → chat 路径 `:1127` 短路径 → `AIMessage.safety_passed == False`（已有 PR3 实现，PR4 不破即可）

### 3.3 AC-T20-3：smart_analyze 路径合规文本 safety_passed 真值

- **Given** `_stream_smart_analyze`（assistant_service.py:534-）
- **When** 输入"我的脸最近有点黄"（合规文本）+ 1 张图
- **Then** `_check_text_safety(text).passed == True` → AIMessage.safety_passed = True（不再硬编码 False / 缺字段）

### 3.4 AC-T21-1：smart_analyze 路径 medical_reject 短路

- **Given** `_stream_smart_analyze`
- **When** 输入"我能不能去打玻尿酸瘦脸"（命中医疗关键词）
- **Then** `_check_text_safety(text).passed == False` → 在 `:707` 前 early return：
  - yield SSE error 帧 `{"code": "E_ASSISTANT_MEDICAL_REJECT", "message_zh": "...", "medical_guarded": True}`
  - audit_persona_state_switch（合规审计 3 事件之一）
  - **不再 yield** 后续 progress(1~5) / report / end 事件

### 3.5 AC-T21-2：smart_analyze medical_reject 错误帧在 progress 之前

- **Given** 同 AC-T21-1
- **When** 订阅 SSE 原始流
- **Then** 第一帧就是 `event: error`（不是 `event: progress`）—— V5.2.1 §5.5 E4-2 修正

### 3.6 AC-T22-1：fallback 不返假报告

- **Given** `_rule_engine_fallback(profile, complaint)` 被调（vision LLM 失败/超时降级）
- **When** profile = `{"skin_type": "中性", "focus_parts": ["额头"], "sitting_hours": 9, "intensity": "轻柔"}`
- **Then** 返回 dict 含：
  - `is_fallback == True`
  - `fallback_reason == "资料不足"`
  - `directions == []`（**不再**返 `f"{part} 方向 {i+1}"` 垃圾标题）
  - `tags == []`
  - `summary == "请先补充档案与图片后再进行智能分析。"`
  - `llm_cost == "0.0"`（不变）

### 3.7 AC-T22-2：fallback level 自动推断（V5.2.1 §3.10 原文保留作 was-quote）

- **原 plan 要求**：sitting_hours >= 8 → "重度"；4~8 → "中度"；否则 "轻度"；directions[] 含 level
- **PR4 修正**（PR3 evidence §5.2 微调 1 后）：fallback 不返 directions，level 推断**失效**（无 directions 可挂 level）→ §3.6 AC-T22-1 推翻 §3.10 §3.10 level 自动推断需求
- **注释保留**：plan §3.10 §3.10 这条作废，由 §3.10 + §3.6 共同定义 fallback 协议

### 3.8 AC-F4-1：SSE end event payload 含 is_fallback 标记

- **Given** `_stream_smart_analyze` 触发 fallback（vision LLM 失败/超时）
- **When** 订阅 SSE 原始流
- **Then** `event: end` 的 payload JSON 含 `is_fallback: true` + `fallback_reason: "资料不足"`；前端按 §5.2.1 PR4 协议**不渲染 report card**，转去引导用户补料

### 3.9 AC-F4-2：SSE end event 不返 fallback 时不含 is_fallback 字段

- **Given** `_stream_smart_analyze` 正常 LLM 成功路径
- **When** 订阅 SSE 原始流
- **Then** `event: end` 的 payload JSON 不含 `is_fallback` / `fallback_reason` 字段（保持现有契约）

### 3.10 AC-回退兼容：fallback 路径 ai_messages 不写 directions JSONB

- **Given** AC-F4-1 fallback 触发
- **When** 查 ai_messages.context_photos
- **Then** `context_photos` 含 `directions: []` + `tags: []` + `summary: "请先补充档案与图片..."` + `is_fallback: true`；**不再** 含假 directions

## 4. 实施步骤（按 sdd-tdd 流程）

### Phase 2.1：RED（写测试必 FAIL）

```bash
cd backend
uv run pytest tests/unit/services/test_vision_safety_chat.py tests/unit/services/test_vision_safety_smart.py tests/unit/services/test_vision_fallback_personalize.py tests/unit/services/test_vision_medical_reject_smart.py -x -q --tb=short
```

预期：4 个 test 文件全部 FAIL（实现不存在或行为不符）。

### Phase 2.2：GREEN（写实现必 PASS）

1. **`assistant_service.py` import 区段补**：
   ```python
   from app.services.diagnosis_service import (
       _check_text_safety,
       _invoke_llm_structured,
       _rule_engine_fallback,
   )
   ```

2. **T20 chat :1231 改**：
   ```python
   safety_check = _check_text_safety(text)
   safety_passed = safety_check["passed"] and to_state != "medical_guarded"
   assistant_msg = AIMessage(
       ...,
       safety_passed=safety_passed,  # 替换原 safety_passed=True
       ...,
   )
   ```

3. **T20 smart_analyze :782-800 补 safety_passed 字段**：
   ```python
   safety_check = _check_text_safety(text)
   assistant_msg = AIMessage(
       ...,
       safety_passed=safety_check["passed"],
       ...,
   )
   ```

4. **T21 smart_analyze `:707` 前 medical_reject 短路**（在 profile dict 之前）：
   ```python
   # ── Phase 1.5: medical_reject 短路（双路径统一）──────────────
   safety_check = _check_text_safety(text)
   if not safety_check["passed"]:
       from app.errors.codes import E_ASSISTANT_MEDICAL_REJECT
       from app.core.audit import audit_persona_state_switch, hash_user_id_pseudo
       audit_kwargs = dict(
           user_id_pseudo=hash_user_id_pseudo(str(user_id)),
           session_id=session_id,
           trigger="smart_analyze_medical_reject_short_circuit",
       )
       audit_persona_state_switch(**audit_kwargs)
       yield _sse_pack("error", {
           "code": E_ASSISTANT_MEDICAL_REJECT,
           "message_zh": "我无法回答医疗问题，建议您咨询专业医师。",
           "medical_guarded": True,
           "request_id": request_id,  # 假定 TraceContextMiddleware 注入
       })
       return  # 短路：不再 yield progress(1~5) / report / end
   ```

5. **T22 `_rule_engine_fallback` 重写**：
   ```python
   def _rule_engine_fallback(profile: dict[str, Any], complaint: str | None) -> dict[str, Any]:
       """规则引擎兜底：缺料时不返假报告（V5.2.1-PR4 F4）。
       
       与 V5.2.1 §3.10 旧版差异：directions/tags 留空 + is_fallback=true +
       fallback_reason="资料不足"。前端识别后不渲染 report card，转引导补料。
       """
       return {
           "is_fallback": True,
           "fallback_reason": "资料不足",
           "directions": [],
           "tags": [],
           "summary": "请先补充档案与图片后再进行智能分析。",
           "llm_cost": "0.0",
       }
   ```

6. **F4 `_stream_smart_analyze` end event payload 透传 fallback 标记**：
   ```python
   # assistant_service.py:839-855 改：
   end_payload: dict[str, object] = {
       "ok": True,
       "reply": reply_text,
       "persona_state": to_state,
       "is_mock": is_mock,
       "medical_guarded": medical_guarded,
       "is_quick_reply": is_quick_reply,
       "level": primary_level,
   }
   # V5.2.1-PR4 F4：fallback 标记透传
   if payload.get("is_fallback"):
       end_payload["is_fallback"] = True
       end_payload["fallback_reason"] = payload.get("fallback_reason", "资料不足")
   yield _sse_pack("end", end_payload)
   ```

7. **`_sse_pack` 类型注解**：str → bytes（避免 Windows GBK 编码 bug，详见 PR3 evidence §3）—— **但**：PR4 不动 `_sse_pack`（在 PR3 中已改回 str，Windows 编码问题已用其他方式规避；本次 PR4 仅在 end payload 加字段，不触发 SSE 编码问题）。**NOTE**: 如果未来发现仍触发 Windows GBK，再补 PR。

### Phase 2.3：REFACTOR

- 单函数 ≤ 50 行（`_rule_engine_fallback` 现在 ~10 行，OK）
- 嵌套 ≤ 2 层（medical_reject 短路 + T22 改写都是 1 层，OK）
- 函数参数 ≤ 5 个（无新加参数）

### Phase 3：全量回归

```bash
cd backend
uv run pytest tests/unit -x -q --tb=short         # 期望 4 个新 test + 现有 97 个 = 101 PASS
uv run pytest tests/integration -x -q --tb=short  # 不破
uv run pytest tests/e2e -x -q --tb=short          # 不破
```

### Phase 4：AI 自审（L0-L6）

- L0 语法：`python -m py_compile backend/app/services/assistant_service.py backend/app/services/diagnosis_service.py`
- L1 风格：`cd backend && uv run ruff check . --fix && uv run ruff format --check .`
- L2 类型：`cd backend && uv run mypy --strict app/services/assistant_service.py app/services/diagnosis_service.py`
- L3 单元测试：Phase 3 全 PASS
- L4 代码质量：`cd backend && uv run ruff check . --select=F401,F811,S608,S307,SEC,B,B003` + `uv run radon -a -i A app/services/ | grep -v ": A$"`
- L5 日志扫描：合规审计 3 事件（safety_violation / medical_reject / persona_state_switch）已对齐
- L6 反模式扫描：禁止裸 except / 硬编码 prompt / 硬编码错误码 / agents/ 写业务规则

### Phase 5：Git Commit

```
feat(assistant): V5.2.1-PR4 双路径 safety_passed 真值 + medical_reject 短路 + fallback 缺料标记

- T20 chat + smart_analyze 双路径调 _check_text_safety(text) → safety_passed 真值
- T21 smart_analyze 路径补 medical_reject 短路（仿 chat :1128 模式）
- T22 _rule_engine_fallback 不返假报告，改 is_fallback=true + fallback_reason
- F4 SSE end event payload 透传 fallback 标记（PR3 evidence §5.2 微调 1）
- docs/architecture/sse-events.md §5.5 追加 fallback 协议说明
- 4 个新 unit test：safety_chat / safety_smart / fallback_personalize / medical_reject_smart
```

## 5. 全量测试矩阵

| 场景 | 类型 | 优先级 | 对应 AC |
|------|------|--------|---------|
| chat 合规文本 safety_passed=True | Unit | P1 | AC-T20-1 |
| chat medical_reject safety_passed=False | Unit | P1 | AC-T20-2 |
| smart_analyze 合规文本 safety_passed=True | Unit | P1 | AC-T20-3 |
| smart_analyze medical_reject 短路 error 帧 + 不 yield 后续 | Unit | P1 | AC-T21-1, AC-T21-2 |
| fallback 不返假报告（directions/tags=[]） | Unit | P1 | AC-T22-1 |
| SSE end event 含 is_fallback=true（fallback 路径） | Unit | P1 | AC-F4-1 |
| SSE end event 不含 is_fallback 字段（正常路径） | Unit | P1 | AC-F4-2 |
| ai_messages.context_photos 不写假 directions | Unit | P1 | AC-回退兼容 |
| 现有 97 个测试 + 4 新测 = 101 PASS | Regression | P0 | Phase 3 |
| 570 个 pytest 项 + 19 修复不破 | Regression | P0 | Phase 3 |

## 6. 风险与依赖

| 风险/依赖 | 影响 | 缓解措施 |
|-----------|------|---------|
| chat 路径 `safety_passed=True` 硬编码已存在 2 个 commit（PR0.x + PR3） | 改真值需 import `_check_text_safety` | 已在 PR4 import 区段补 |
| smart_analyze AIMessage 缺 safety_passed 字段（Pydantic 默认 True） | 改真值需新增字段 | 同上 |
| T22 重写 `_rule_engine_fallback` 后，调用方 `_stream_smart_analyze` 需适配新字段 `is_fallback` | 协议变更 | F4 end event payload 透传 |
| T22 §3.6 AC-T22-1 推翻 V5.2.1 §3.10 level 自动推断 | 与 plan §3.10 表述冲突 | 在 SPEC §3.7 AC-T22-2 明确作废 + plan §3.10 在 commit msg 中标注"已被 PR4 F4 覆盖" |
| 现有 `test_assistant_stream_persist.py` 2 个 FAIL（PR0 报告 §4.2）| 可能受 T20 影响 | 在 Phase 3 全量回归时验证 |

## 7. 退出标准

- [ ] 4 个新 unit test 文件全部 PASS
- [ ] 现有 570 pytest 项 + 19 修复不破（期望 ≥ 101 PASS）
- [ ] `_check_text_safety` 不新建（复用 `diagnosis_service.py:53` 已有）
- [ ] medical_reject 短路后 SSE 流只有 `event: error`（无 progress/report/end）
- [ ] fallback 触发后 SSE end event payload 含 `is_fallback: true`
- [ ] `docs/architecture/sse-events.md §5.5` 已追加 fallback 协议
- [ ] AI self-review（L0-L6）PASS
- [ ] Commit message 符合 Conventional Commits
- [ ] §5.5 e2e 场景 3（medical_reject）+ 场景 4（vision 超时降级）解锁

## 8. e2e 用户验收清单

| # | 必跑项 | 操作 | 期望 |
|---|--------|------|------|
| E4-1 | medical_reject smart | 开发者工具输入"我能不能去打玻尿酸瘦脸" + 触发智能分析 | SSE error 帧 `code=E_ASSISTANT_MEDICAL_REJECT`，后续无 progress/report/end |
| E4-2 | medical_reject 错误帧前判断 | 验 SSE error 在 progress 之前 | ✅ |
| E4-3 | safety_passed 落库 chat | 触发 chat 模式 + 查 ai_messages.safety_passed | True（合规文本） |
| E4-4 | safety_passed 落库 smart | 触发智能分析（合规文本）+ 查 ai_messages.safety_passed | True（修复前缺字段；PR4 改真值） |
| E4-5 | fallback 个性化 + is_fallback | 设 `VISION_TIMEOUT_SEC=0.001` + 触发智能分析 + 设档案 skin_type=中性 sitting_hours=9 | end event payload 含 `is_fallback: true` + `fallback_reason: "资料不足"`（修复前是"基础养护方向"假报告） |
| E4-6 | fallback 不返假报告 | 同 E4-5 + 验 ai_messages.context_photos.directions == [] | ✅ |
| E4-7 | 审计日志 | 检查日志含 audit_persona_state_switch（trigger=smart_analyze_medical_reject_short_circuit）| 输入"玻尿酸" → 看到 audit |

## 9. 跨 PR 复用前置

- **复用 PR0**：evidence 目录 `docs/plan/evidence/` + pytest 环境
- **复用 PR1**：golden_set_v1.yaml 12 处 TODO 已回填（无新增 TODO）
- **复用 PR2**：`_photo_urls.py` helper + `vision_report.py` Pydantic schema
- **复用 PR3**：5 阶段 progress 协议 + llm_cost 上报 + ADR sync + sse-events §5 追加
- **不依赖 PR5/PR6**：本 PR4 仅改后端
- **被 PR5 依赖**：PR5 §5.2.1-3 微调 2 上传三步卡缺料阻断依赖本 PR4 F4 `is_fallback` 标记

## 10. 修订记录

| 版本 | 日期 | 修订 | 触发 |
|------|------|------|------|
| 1.0.0 | 2026-07-11 | 初版 | PR3 合入后 PR4 SPEC 起草 |