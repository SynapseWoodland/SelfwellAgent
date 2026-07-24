# ATDD-Diagnosis: 多模态诊断

> **版本**: V1.1
> **状态**: Draft
> **对应模块**: M2
> **对应 TDS**: `docs/architecture/TDS/TDS-M2-multimodal-diagnosis.md`
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`
> **修订说明**: V1.1 基于 PRD/TDS 澄清，新增分层降级链、锁定机制、最少部位要求等场景

---

## 一、AI 联合智能分析

### Background
```gherkin
Background:
  Given 用户已完成登录并持有有效 JWT
  And 用户档案完整（5 个必填字段已填写）
  And 用户未在 7 天内完成过智能分析
```

### Scenario: 用户上传照片后 LLM 自动识别部位（M2-FR-01）
```gherkin
Given 用户上传 1-3 张照片（无 body_part 标注）
When 用户点击"开始智能分析"
Then 后端 LLM 分析每张照片，自动识别 body_part（face/head/shoulder_neck）
And 对识别结果做 distinct，得到 N ∈ {1, 2, 3}
And 返回 N 个部位对应的改善方向
```

### Scenario: N=1 时 LLM 识别出 1 个部位（M2-FR-01）
```gherkin
Given 用户上传 [照片A, 照片A, 照片A]（3 张相同）
When LLM 自动识别 body_part
Then 识别结果可能都是 face → distinct 后 N=1
And 报告仅生成 1 个部位的改善方向
```

### Scenario: 用户完成照片上传后在 20 秒内看到智能分析报告（M2-FR-01）
```gherkin
Given 用户已上传 1-3 张照片
And 用户档案完整
When 用户点击"开始智能分析"
Then 系统在 20 秒内返回智能分析报告（P95 ≤ 20s）
And 报告包含 N 条改善方向（N = distinct 部位数）
And 每条方向对应 1 个部位
```

### Scenario: 智能分析报告包含合规的改善方向（M2 合规红线）
```gherkin
Given 用户完成智能分析
Then 每条改善方向包含具体视频链接（bilibili/小红书/抖音）
And 改善方向格式为"养护方向/生活方式建议/参考动作"
And 不包含任何医疗表述（治疗/治愈/医生/处方/病症/病）
And 不包含效果承诺（会变白/会变小/会提升）
And 合规审查标记为 PASS
```

### Scenario: 医疗关键词触发拦截（M2 合规红线 R5）
```gherkin
Given 用户在智能分析过程中输入"帮我治疗颈椎病"
When 系统检测到医疗关键词
Then 系统回复"我无法回答医疗问题，建议您咨询专业医师"
And 不生成任何智能分析报告
And 记录 ai_messages.trigger='medical_reject'
```

### Scenario: 7 天内不重复上传直接展示缓存（M2-FR-02）
```gherkin
Given 用户上一次诊断完成时间 - 当前时间 < 7天
And diagnosis_status='completed'
When 用户进入智能分析页
Then 系统显示"您有可用的智能分析报告"
And 用户可直接查看缓存报告
And 不触发 LLM 调用
And llm_cost=0
```

### Scenario: LLM 降级链 P1→P2（M2-FR-03）
```gherkin
Given 用户发起智能分析
When LLM 调用失败（P1=MULTI_MODEL 超时 30s 或 HTTP 500）
Then 系统切换到 P2=BACKUP_MULTI_MODEL
And 记录降级日志（llm_error=true, tier=1, model=BACKUP_MULTI_MODEL）
And 报告标记 fallback=true
```

### Scenario: BACKUP_MULTI_MODEL 也失败时返回 Fallback ACK（M2-FR-03）
```gherkin
Given BACKUP_MULTI_MODEL 也不可用（超时或 HTTP 500）
When 用户发起智能分析
Then 系统返回 P3 Fallback ACK 模板 + 24h 人工跟进承诺
And 记录降级日志（llm_error=true, tier=2, model=null）
And 报告标记 fallback=true
And 照片保留供后续重试
```

### Scenario: 连续 2 次 LLM 失败锁定智能分析功能（M2-FR-03）
```gherkin
Given 连续 2 次 LLM 调用失败
When 用户再次尝试发起智能分析
Then 系统返回"智能分析功能暂时不可用，请稍后再试"
And 锁定智能分析入口
And 锁定时长 30 分钟
And 30 分钟后自动解锁并重试
```

---

## 二、照片校验

### Scenario: 照片数量不足被拦截（M2-FR-01）
```gherkin
Given 用户上传照片数组长度 < 1
When 用户点击"开始智能分析"
Then 返回业务码 E_DIAGNOSIS_INVALID_INPUT
And 提示"请至少上传 1 张照片"
And 不调用 LLM
```

### Scenario: 照片数量超过 3 张被拦截（M2-FR-01）
```gherkin
Given 用户上传照片数组长度 > 3
When 用户点击"开始智能分析"
Then 返回业务码 E_DIAGNOSIS_INVALID_INPUT
And 提示"最多上传 3 张照片"
And 不调用 LLM
```

### Scenario: 照片尺寸过大被拦截（M2-FR-01）
```gherkin
Given 用户上传的单张照片边长 > 1024px
When 用户点击"开始智能分析"
Then 返回业务码 E_DIAGNOSIS_IMAGE_TOO_LARGE
And 提示"照片尺寸过大（需压缩至 1024px）"
```

### Scenario: 照片部位全为 unclassified 被拦截（M2-FR-01）
```gherkin
Given 用户上传的照片 AI 识别后全部为 unclassified
When 用户点击"开始智能分析"
Then 返回业务码 E_DIAGNOSIS_INVALID_INPUT
And 提示"请上传包含人体部位的照片"
And 不调用 LLM
```

### Scenario: 用户档案不完整时禁止分析（M2-FR-01）
```gherkin
Given 用户档案缺失（5 个必填字段未全填：age_range/focus_parts/intensity/preferred_time/sitting_hours）
When 用户尝试发起智能分析
Then 返回业务码 E_USER_PROFILE_INCOMPLETE
And 提示用户先完善档案
And 不调用 LLM
```

---

## 三、SSE 流式进度

### Scenario: SSE 返回 8 阶段事件流（M2-FR-04）
```gherkin
Given 用户发起智能分析
When GET /api/v1/diagnosis/{id}/stream
Then 后端按顺序推送事件：connected → processing → image_validated → llm_calling → compliance_check → progress(N) → result/fallback/error → done
And 每 15 秒推送心跳事件
And 事件格式符合 SSE 规范（event: <name>\ndata: <json>）
And 前端 UI 折叠 processing + image_validated 为用户视角的「照片预处理」一个步骤（避免重复表述造成用户困惑）
```

### 8 阶段事件说明

| # | 服务端 SSE 事件 | 用户视角文案 | 用途 | 预计耗时 | 累计 |
|---|----------------|------------|------|---------|------|
| 1 | `connected` | （不进 UI）| 握手确认 | — | — |
| 2 | `processing` | （不显示，≤50ms）| 业务开始处理 | 瞬时 | — |
| 3 | `image_validated` | **照片预处理中...** → ✓ 照片预处理完成 | 照片校验完成 | ≤ 2s | 2s |
| 4 | `llm_calling` | **AI 正在分析你的照片...** | LLM 调用中 | ≤ 15s | 17s |
| 5 | `compliance_check` | **合规审查中...** | 合规审查 | ≤ 3s | 20s |
| 6 | `progress` | **正在生成改善方向 1/N...**（可多次） | 通用进度 | — | — |
| 7 | `result` / `fallback` / `error` | **✓ 报告生成完成** / 降级中... / 出错了... | 诊断结果 | — | — |
| 8 | `done` | （结束事件，前端跳转报告页） | 流结束 | — | — |

**说明**：用户加载页实际看到 5-6 个步骤（不显示 processing 与 done）；服务端事件流 8 个保持不变，方便调试与可观测性。`processing` + `image_validated` 在 UI 层合并为"照片预处理"完整动作。

---

## 四、成本约束

### Scenario: 单次 LLM 成本不超过 ¥0.15（M2-FR-03）
```gherkin
Given 用户发起一次智能分析
When 分析完成
Then 单次 llm_cost ≤ ¥0.15
And 日累计 llm_cost ≤ ¥30
And 月累计 llm_cost ≤ ¥500（与M5对话共享月度¥700预算）
```

### Scenario: 日 LLM 预算超限拦截（M2-FR-03）
```gherkin
Given 今日 LLM 预算已累计超 ¥30
When 用户尝试发起智能分析
Then 返回业务码 E_DIAGNOSIS_RATE_LIMIT
And 提示"今日分析次数已达上限，请明天再来"
```

---

## 五、诊断状态同步

### Scenario: 诊断完成后状态更新（M2→M5）
```gherkin
Given 用户完成智能分析
When 报告生成成功
Then diagnosis_status 更新为 'completed'
And 同步到 ai_sessions.diagnosis_status
And M5 入口卡状态可感知到变化
```

### Scenario: 诊断过期判定（M2→M5）
```gherkin
Given 用户上一次诊断完成时间距今 > 30 天
When M5 询问诊断结果
Then AI 提示"上次分析已经是 30 天前了，要不要重新分析一下？"
And 引导用户重新上传照片进行诊断
And diagnosis_status 标记为 'expired'
```

---

## 六、引用说明

### 相关定义
- 诊断状态枚举：详见 [ATDD-Shared.md §一.2](../ATDD-Shared.md#一用户状态枚举)
- 合规红线：详见 [ATDD-Shared.md §三](../ATDD-Shared.md#三合规红线)
- 降级策略：详见 [ATDD-Shared.md §五](../ATDD-Shared.md#五降级策略)
- 错误码定义：详见 [ATDD-Shared.md §四](../ATDD-Shared.md#四错误码字典)
- 用户旅程：详见 [ATDD-Journey.md §二](../ATDD-Journey.md#二诊断旅程)

---

## 七、M2 → M3 手动触发联动

> **说明**：M2 诊断完成后**不自动触发** M3 方案生成。用户需在诊断报告页手动点击"生成我的 21 天方案"按钮，才调用 `POST /plans/generate`。这是用户主动行为，非系统自动联动。

### Background
```gherkin
Background:
  Given 用户已完成智能分析并看到报告页
  And 诊断状态为 'completed'
  And 用户档案完整（5 个必填字段）
```

### Scenario: 用户从诊断报告页手动触发方案生成（M2→M3）
```gherkin
Given 用户在诊断报告页（P03c）
When 用户点击"生成我的 21 天方案"按钮
Then 前端调用 POST /api/v1/plans/generate（传入 report_id）
And 后端基于 report_id 关联的 tags + N 生成 21 天方案
And 方案状态为 'queued'（未激活）
And 前端跳转至方案交付页（P04）
And 用户可预览前 5 天任务
```

### Scenario: 用户点击后 1800ms 动画加载（M2→M3）
```gherkin
Given 用户点击"生成我的 21 天方案"
When 按钮触发 triggerGenerate(targetStep=3)
Then 按钮文字变为"生成中…"
And 按钮禁用防止重复点击
And 1800ms 后自动跳转至方案交付页
```

### Scenario: 诊断报告页停留等待用户主动操作（M2→M3）
```gherkin
Given 诊断完成，报告显示 N 条改善方向
When 用户未点击"生成我的 21 天方案"
Then 报告页保持停留，不自动跳转
And 用户可随时点击按钮触发方案生成
And 不限制用户在报告页停留时长
```

---

## 八、修订历史

| 日期 | 版本 | 改动 |
|------|------|------|
| 2026-07-21 | V1.0 | 初次创建，补充诊断状态同步场景 |
| 2026-07-21 | V1.1 | 1. 新增分层降级链 P1→P2→P3 场景<br>2. 新增锁定机制 30 分钟场景<br>3. 新增照片部位全 unclassified 拦截场景<br>4. SSE 事件流明确为 8 阶段<br>5. UI 层合并 processing + image_validated 为"照片预处理"（方案 B 用户体验优化）<br>6. 删除严重度等级场景（确认不需要）<br>7. 更新降级兜底描述为 Fallback ACK + 24h 人工跟进 |
| 2026-07-22 | V1.2 | 新增 §七 M2→M3 手动触发联动：明确诊断完成后不自动联动方案生成，用户需在报告页手动点击触发 |
