# TDS-M2: 多模态诊断 - 验收标准

> **版本**: V1.0
> **状态**: Draft
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`

---

## Feature: AI 联合智能分析

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
And 报告包含至少 N 条改善方向（N = distinct 部位数）
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
Given 用户在 7 天内已有智能分析报告
And user.report_cache 存在且未过期
When 用户进入智能分析页
Then 系统显示"您有可用的智能分析报告"
And 用户可直接查看缓存报告
And 不触发 LLM 调用
And llm_cost=0
```

### Scenario: LLM 失败时降级链（M2-FR-03）
```gherkin
Given LLM 服务不可用（MULTI_MODEL 超时 30s 或 HTTP 500）
When 用户发起智能分析
Then 系统切换到 BACKUP_MULTI_MODEL（轻量多模态）
And 记录降级日志（llm_error=true, tier=1, model=BACKUP_MULTI_MODEL）
And 报告标记 fallback=true
```

### Scenario: BACKUP_MULTI_MODEL 也失败时返回 Fallback ACK（M2-FR-03）
```gherkin
Given BACKUP_MULTI_MODEL 也不可用（超时或 HTTP 500）
When 用户发起智能分析
Then 系统返回 Fallback ACK 模板 + 24h 人工跟进承诺
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
```

---

## Feature: 照片校验

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

### Scenario: 用户档案不完整时禁止分析（M2-FR-01）
```gherkin
Given 用户档案缺失（5 个必填字段未全填）
When 用户尝试发起智能分析
Then 返回业务码 E_USER_PROFILE_INCOMPLETE
And 提示用户先完善档案
And 不调用 LLM
```

---

## Feature: SSE 流式进度

### Scenario: SSE 返回 8 阶段事件流（M2-FR-04）
```gherkin
Given 用户发起智能分析
When GET /api/v1/diagnosis/{id}/stream
Then 后端按顺序推送事件：connected → processing → image_validated → llm_calling → compliance_check → progress(N) → result/fallback/error → done
And 每 15 秒推送心跳事件
And 事件格式符合 SSE 规范（event: <name>\ndata: <json>）
```

---

## Feature: 成本约束

### Scenario: 单次 LLM 成本不超过 ¥0.15（M2-FR-03）
```gherkin
Given 用户发起一次智能分析
When 分析完成
Then 单次 llm_cost ≤ ¥0.15
And 日累计 llm_cost ≤ ¥30
And 月累计 llm_cost ≤ ¥500
```

### Scenario: 日 LLM 预算超限拦截（M2-FR-03）
```gherkin
Given 今日 LLM 预算已累计超 ¥30
When 用户尝试发起智能分析
Then 返回业务码 E_DIAGNOSIS_RATE_LIMIT
And 提示"今日分析次数已达上限，请明天再来"
```
