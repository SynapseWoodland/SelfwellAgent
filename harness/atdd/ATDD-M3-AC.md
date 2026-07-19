# TDS-M3: 21天方案 - 验收标准

> **版本**: V1.0
> **状态**: Draft
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`

---

## Feature: 21 天方案生成

### Background
```gherkin
Background:
  Given 用户已完成 M2 智能分析，获得 7-14 个标签
  And 用户持有有效 JWT
```

### Scenario: 基于智能分析标签生成 21 天方案（M3-FR-01）
```gherkin
Given 用户已完成 M2 智能分析，获得 7-14 个标签
When 用户点击"生成 21 天方案"
Then 系统返回 21 天每日任务清单
And 每天包含至少 1 个视频任务
And 21 天内同一 video_id 不重复出现
And 响应时间 P95 < 2 秒
```

### Scenario: 阶段 1（第 1-7 天）每天仅 1 个任务（M3-FR-02）
```gherkin
Given 方案已生成
When 用户查看第 1-7 天任务
Then 每天仅有 1 个视频任务
And 每任务时长 5-15 分钟
And 阶段 1 视频难度为 L1（轻柔）
```

### Scenario: 阶段 2（第 8-14 天）每天 1-2 个任务（M3-FR-02）
```gherkin
Given 方案已生成
When 用户查看第 8-14 天任务
Then 每天有 1-2 个视频任务
And 每任务时长 10-25 分钟
And 视频来源为 L1 + 用户档案自适应
```

### Scenario: 阶段 3（第 15-21 天）每天 2-3 个任务（M3-FR-02）
```gherkin
Given 方案已生成
When 用户查看第 15-21 天任务
Then 每天有 2-3 个视频任务
And 每任务时长 15-30 分钟
And 视频来源包含用户已打卡动作回看
```

### Scenario: 方案可一键进入首页（M3-FR-01）
```gherkin
Given 用户完成方案生成
When 用户点击"开始 21 天"
Then 跳转至首页（P02）
And 首页今日任务卡片显示第 1 天视频
And 进度环显示 day=1/21
```

---

## Feature: 视频匹配算法

### Background
```gherkin
Background:
  Given 视频库总数 ≥ 50 条
  And 用户档案已填写（intensity / preferred_time）
```

### Scenario: 标签匹配度权重最高（M3-FR-03）
```gherkin
Given 视频 A 标签匹配度 Jaccard=0.8，时长 10min，难度 2
And 视频 B 标签匹配度 Jaccard=0.4，时长 15min，难度 3
When 计算得分 score = 0.5*标签 + 0.3*时长 + 0.2*难度
Then 视频 A 排名高于视频 B
```

### Scenario: 跳过率超过 30% 触发告警（M3-FR-03）
```gherkin
Given 某视频被用户跳过次数 / 总展示次数 > 0.30
When 系统统计跳过率
Then 发送告警通知（邮件 + IM）
And 记录需人工运营介入
And 视频进入待审核队列
```

### Scenario: 视频库不足 50 条时降级为标准模板（M3-FR-03）
```gherkin
Given 视频库数量 < 50 条
When 用户请求生成方案
Then 系统使用预置标准 21 天模板
And 不阻塞上线
And 记录降级日志
```

---

## Feature: 今日任务获取

### Background
```gherkin
Background:
  Given 用户已激活方案 plan_id='xxx'
  And 当前日期为方案开始后第 N 天
```

### Scenario: 获取今日任务（M3-FR-04）
```gherkin
Given 用户已激活方案
When 用户 GET /api/v1/plans/today
Then 返回今日任务（day / phase / tasks）
And phase ∈ [1, 2, 3]
And tasks 包含 video_id / title / source / thumbnail / duration_sec
```

### Scenario: 方案生成超时返回降级（M3-FR-03）
```gherkin
Given 方案匹配算法 P95 超过 2 秒
When 用户请求生成方案
Then 返回业务码 E_PLAN_GENERATION_TIMEOUT
And 返回基于档案标签的标准方案兜底
```

### Scenario: 用户已有活跃方案禁止重复生成（M3-FR-01）
```gherkin
Given 用户已有 status='active' 的方案
When 用户再次请求生成方案
Then 返回业务码 E_PLAN_ALREADY_EXISTS
And 提示用户查看已有方案
```

---

## Feature: 错误处理

### Scenario: 关联的智能分析报告不存在（M3-FR-01）
```gherkin
Given 用户传入的 report_id 无效
When 用户请求生成方案
Then 返回业务码 E_DIAGNOSIS_NOT_FOUND
And 提示"关联的智能分析报告不存在"
```

### Scenario: 视频库为空时返回错误（M3-FR-03）
```gherkin
Given video_pool 全空
When 用户请求生成方案
Then 返回业务码 E_VIDEO_NOT_FOUND
And 提示"视频库为空，请联系运营"
```
