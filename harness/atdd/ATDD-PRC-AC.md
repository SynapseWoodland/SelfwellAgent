# ATDD-PRC-AC: PR-Contract-Fix 验收标准

> **对应 TDS**: `docs/architecture/TDS/SPEC-M4-PR-Contract-Fix.md`
> **版本**: V1.0
> **状态**: Draft

---

## Feature: C-1 SSE 流契约修复

### Scenario: assistant smart-analyze 创建诊断报告和 job

```gherkin
Given assistant_service.create_session receives entry_card=smart_analyze
When create_session is called
Then a Report row is created with status='queued'
And job_state.create_job is called with report_id and user_id
And response includes report_id, job_id, and stream_url
```

### Scenario: 诊断 SSE 流可通过 stream_url 消费

```gherkin
Given assistant create_session returned stream_url for smart_analyze
When diagnosis-loading-v2 connects to stream_url
Then SSE events stream with progress updates
And final event includes diagnosis report data
```

---

## Feature: C-2 创建方案契约修复

### Scenario: 前端调用正确路径生成方案

```gherkin
Given diagnosis-report-v2.onGeneratePlan is triggered
When POST /plans/generate is called with report_id
Then response returns plan_id and plan data
And plan-delivery loads preview with valid plan_id
```

### Scenario: 前端不调用错误路径

```gherkin
Given diagnosis-report-v2 is loaded
When user requests plan generation
Then POST /plans/generate is called with body {report_id: ...}
And POST /plans {session_id: ...} is NOT called
```

---

## Feature: C-3 预览契约修复

### Scenario: 21天预览端点存在且返回正确字段

```gherkin
Given GET /plans/{plan_id}/preview?days=21 is called
When plan exists
Then response is 200 with data {plan_id, days: [...]} field
And each day includes day_index, duration_minutes, and task
```

### Scenario: 预览端点参数边界

```gherkin
Given GET /plans/{plan_id}/preview?days=N is called
When N is between 1 and 21
Then response is 200 with N days of preview
When N is greater than 21
Then response is 400 with validation error
```

---

## Feature: 链路回归

### Scenario: assistant_v1 单测全 pass

```gherkin
Given pytest runs tests/unit/test_assistant_v1.py
When all tests execute
Then all tests pass
And no new failures are introduced
```

### Scenario: plans_v1 单测全 pass

```gherkin
Given pytest runs tests/unit/test_plans_v1.py
When all tests execute
Then all tests pass
And no new failures are introduced
```

### Scenario: 新增契约测试 pass

```gherkin
Given pytest runs tests/unit/test_assistant_smart_analyze_extra_fields.py
And pytest runs tests/unit/test_plans_preview.py
When all tests execute
Then all tests pass
```
