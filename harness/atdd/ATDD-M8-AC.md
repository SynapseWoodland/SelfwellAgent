# TDS-M8: 主动回忆 - 验收标准

> **版本**: V1.0
> **状态**: Draft
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`

---

## Feature: AI 主动触发（Day N）

### Background
```gherkin
Background:
  Given 用户已完成方案
  And 用户已完成 Day 7/14/21 打卡
```

### Scenario: Day 7 早上 8:00 推送回忆气泡（M8-FR-01）
```gherkin
Given 用户注册已满 7 天
And 用户连续打卡满 7 天
When Celery Beat 扫表触发 auto_day7
Then 服务通知推送 + P03a 主页出现回忆气泡
And 气泡文案 "我们已经一起走了 7 天。要不要看看 7 天前的自己？"
And P95 渲染时间 ≤ 2 秒
```

### Scenario: Day 14 / Day 21 同样触发（M8-FR-01）
```gherkin
Given 用户注册已满 14 天（已连续打卡 14 天）
When Celery Beat 扫表
Then 同 Day 7 逻辑，气泡文案相应变化
And 气泡文案 "我们已经一起走了 14 天。"
```

### Scenario: 打卡中断但日历日期到达不自动推送（M8-FR-01）
```gherkin
Given 用户 Day 7 时打卡中断
And 日历日期已到达第 7 天
When 系统检测
Then 不自动推送 Day 7 回忆气泡
And 但用户主动点「问问过去的自己」仍可用
```

### Scenario: 用户 48 小时内回访（M8-FR-01）
```gherkin
Given 用户收到 Day N 回忆通知
When 用户在 48 小时内打开 P03a
Then 用户点击回忆气泡，进入 M8 对话
And 入口卡点击率 ≥ 8%（指标 G7）
```

---

## Feature: 用户主动触发

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
  And 用户点击 💬 问过去的自己入口卡
```

### Scenario: 用户点 💬 问过去的自己入口卡（M8-FR-02）
```gherkin
Given 用户在 P03a 点 💬 入口卡
When 用户点击
Then 系统触发 user_query
And AI 回复 ≤ 5 秒（P95 召回纯文字）
And 展示历史缩略图
```

### Scenario: 用户点 💬 后历史照片缩略图加载（M8-FR-02）
```gherkin
Given 用户进入 M8 对话
And 用户有历史 feedback 含照片
When 页面渲染
Then 缩略图 load P95 ≤ 3 秒
And signed URL 有效期 7 天
And 不将图片 base64 传给 LLM
```

### Scenario: 空态 soft-tip 展示（M8-FR-02）
```gherkin
Given 用户从未上传过 feedback
When 用户点 💬 入口卡
Then AI 展示 soft-tip 气泡
And 3 按钮均可点击
And 任意按钮都能跳通（不报错）
```

---

## Feature: 空态 soft-tip

### Background
```gherkin
Background:
  Given 用户触发空态回忆
  And AI 展示 soft-tip 气泡
```

### Scenario: soft-tip [补一组] 按钮路由（M8-FR-02）
```gherkin
Given 用户触发空态
When 用户点 [补一组]
Then 跳转 P08a 编辑器（提示"这是一段以前的回忆"）
And 写入 feedback.type=period_photo
And photo_url / body_part 必填
```

### Scenario: soft-tip [就这样聊] 按钮路由（M8-FR-02）
```gherkin
Given 用户触发空态
When 用户点 [就这样聊]
Then 留在 P03a 对话
And 用户可正常提问
```

### Scenario: soft-tip [取消] 按钮路由（M8-FR-02）
```gherkin
Given 用户触发空态
When 用户点 [取消]
Then 回到 P03a 主页
And soft-tip 关闭
And 不强制再推
```

---

## Feature: Recall Safety（三层合规）

### Background
```gherkin
Background:
  Given 用户进入 M8 对话
  And AI 生成 ai_summary + ai_encourage
```

### Scenario: Layer 1 Prompt hardcode 约束模型（M8-FR-03）
```gherkin
Given LLM 接收 Recall Prompt
When 模型生成输出
Then 4 条"绝对不可违反"已 hardcode 在输入中
And 模型输出不含评判性语句
And 不出现"比之前好/差"
```

### Scenario: Layer 2 敏感词 100+ 拦截（M8-FR-03）
```gherkin
Given LLM 输出 "你比 7 天前进步了"
When RecallSafetyGuard 扫描
Then 命中 before_after_judge 词组
And safety_passed=FALSE
And 用安全兜底文案替换违规内容
```

### Scenario: 违规内容 0 容忍（M8-FR-03）
```gherkin
Given 违规率统计 > 0.1%
When 告警触发
Then 自动降级为纯规则模板
And 人工抽检 10%
And ai_messages.safety_violations 记录违规词组
```

### Scenario: 违规审计可追溯（M8-FR-03）
```gherkin
Given 某次 recall safety_passed=FALSE
Then ai_messages.safety_violations JSONB 记录违规词组
And 告警立即发送（邮件 + IM）
And 违规记录保留 90 天后自动删除
```

### Scenario: "前后评判"违规 0 容忍（M8-FR-03）
```gherkin
Given 用户收到回忆内容
When 系统校验内容
Then 不含 "比之前好/差"
And 不含 "进步了/改善了/变好了"
And 不含 "颜值/好看/瘦"
And 不含 "你坚持了 X 天真棒"
```

---

## Feature: 召回数据源规范

### Background
```gherkin
Background:
  Given 用户触发主动回忆
  And RecallRetriever 执行 retrieve
```

### Scenario: 仅召回白名单数据（M8-FR-04）
```gherkin
Given RecallRetriever 执行 retrieve
When 数据召回
Then 仅使用 feedback.mood_text + plan.days.actions
And 仅取 photo_url 元数据 + signed URL
And DENIED_RETRIEVAL_SOURCES 不被访问
```

### Scenario: 永不复用打卡天数（M8-FR-04）
```gherkin
Given recall_sessions 构建摘要
When 摘要生成
Then 不引用 checkin.count
And 不出现 "你已经坚持了 X 天"
And 不出现 "你的打卡天数是"
```

### Scenario: 不喂图片 LLM（M8-FR-04）
```gherkin
Given 用户有历史 feedback 含照片
When RecallRetriever 召回
Then 仅返回 signed URL（7 天有效）
And 不将图片 base64 传给 LLM
And photos.before_after_compare 不被访问
```

### Scenario: 引用用户原文时加时间标注（M8-FR-03）
```gherkin
Given 用户有 mood_text feedback
When AI 生成 summary
Then 引用原文时格式为 "你 {date} 写过：'{text_excerpt}'"
And 日期来自 created_at（Asia/Shanghai）
And 不加评判性描述
```

---

## Feature: 输出约束

### Background
```gherkin
Background:
  Given AI 生成 ai_summary + ai_encourage
```

### Scenario: ai_summary ≤ 200 字（M8-FR-03）
```gherkin
Given AI 生成 summary
When 校验输出
Then ai_summary ≤ 200 字
And ai_encourage ≤ 80 字
And 超长内容截断处理
```

### Scenario: ai_encourage 为鼓励语不评判（M8-FR-03）
```gherkin
Given AI 生成 encourage
When 校验输出
Then 内容为鼓励语
And 不评判、不对比、不量化
And 来自安全兜底文案池
```

---

## Feature: 错误处理

### Scenario: LLM 调用失败（M8-FR-03）
```gherkin
Given LLM 服务不可用
When 用户触发主动回忆
Then 返回安全兜底文案
And llm_cost=0
And safety_passed=null
```

### Scenario: 无活跃 ai_sessions 时新建会话（M8-FR-02）
```gherkin
Given 无活跃 ai_sessions
When 用户触发主动回忆
Then 系统新建 ai_sessions
And 自动重试召回流程
And 不报错给用户
```
