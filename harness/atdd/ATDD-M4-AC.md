# TDS-M4: 每日打卡 - 验收标准

> **版本**: V1.0
> **状态**: Draft
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`

---

## Feature: 每日打卡

### Background
```gherkin
Background:
  Given 用户已激活 21 天方案
  And 用户已完成今日视频跟练
  And 用户持有有效 JWT
```

### Scenario: 用户完成视频跟练后打卡（M4-FR-01）
```gherkin
Given 用户已完成今日视频跟练
When 用户点击"已完成打卡"
Then 打卡成功
And 用户碎片 +1（不设递增系数）
And 用户连续天数 +1
And 显示打卡成功话术（禁用"真的棒"）
And 返回打卡记录（id / fragments / streak_days）
```

### Scenario: 打卡操作步骤 ≤ 2 步（M4-FR-01）
```gherkin
Given 用户在首页
When 用户完成跟练
Then 点"已完成打卡"即可完成打卡
And 操作步骤 ≤ 2 步
```

### Scenario: 感想字数限制 50 字（M4-FR-01）
```gherkin
Given 用户输入打卡感想
When 感想超过 50 字
Then 系统提示字数超限
And 不允许提交
And 返回业务码 E_CHECKIN_FEELING_TOO_LONG
```

### Scenario: 每日打卡仅限 1 次（M4-FR-01）
```gherkin
Given 用户今日已在 plan_id + day 下打卡
When 用户再次尝试打卡
Then 返回业务码 E_CHECKIN_DUPLICATE
And 提示"今日已打卡"
```

### Scenario: 打卡天数不连续被拦截（M4-FR-01）
```gherkin
Given 用户尝试在 day 不在 [1,21] 范围打卡
When 用户点击打卡
Then 返回业务码 E_CHECKIN_DAY_INVALID
And 提示"打卡天数不连续"
```

---

## Feature: 三档柔性话术

### Scenario: 完成打卡后显示温柔鼓励（M4-FR-02）
```gherkin
Given 用户今日已打卡
When 打卡完成
Then 显示"今天辛苦了，{nickname}。我们明天见。"
And 话术不包含"真的棒"（在 ack-forbidden 列表）
And 话术从 30 条随机池选 1 条
```

### Scenario: 连续 2 日未打卡显示抱抱话术（M4-FR-02）
```gherkin
Given 用户连续 2 日未打卡
When 系统在 19:00 检测到连续未打卡
Then 发送推送"想休息一天也可以，先把今天的你抱抱。我们慢慢来。"
And 显示抱抱卡入口
```

### Scenario: 今日未打卡 19:00 推送温柔话术（M4-FR-02）
```gherkin
Given 用户当日 19:00 前未打卡
When 系统检测到未打卡
Then 发送推送"今天累了就休息，明天的你还在这里。"
```

---

## Feature: 进度环

### Background
```gherkin
Background:
  Given 用户已激活 21 天方案
```

### Scenario: 进度环仅自己可见（M4-FR-03）
```gherkin
Given 用户查看进度环
Then 进度环仅当前用户可见
And 无排行榜、无对比数据
And 不可见其他用户进度
```

### Scenario: 进度环可补合（M4-FR-03）
```gherkin
Given 用户前一天未打卡
When 用户今天完成打卡
Then 进度环显示补合后的进度
And 不显示红色警告
And 使用柔和配色（Apple Watch 风格）
```

### Scenario: 进度环颜色为柔和色（M4-FR-03）
```gherkin
Given 用户查看进度环
Then 环形进度颜色为 #A8C5B5（柔和薄荷绿）
And 不使用红色
```

---

## Feature: 打卡日历

### Background
```gherkin
Background:
  Given 用户已激活 21 天方案
```

### Scenario: 获取打卡日历（M4-FR-04）
```gherkin
Given 用户请求 GET /api/v1/checkins/calendar
When 系统处理请求
Then 返回 total_days=21
And 返回 completed_days / current_streak / fragments
And 返回 calendar[] 含 day / status / date
And status ∈ [completed, missed, pending]
And 返回 progress_ring.percentage
```

### Scenario: 打卡日历跨天显示（M4-FR-04）
```gherkin
Given 用户已完成部分打卡
When 用户查看打卡日历
Then completed 状态显示为薄荷绿
And missed 状态显示为浅灰色
And 今日高亮显示
```

---

## Feature: 推送送达

### Scenario: 每日 8:00 推送必须送达（M4-FR-05）
```gherkin
Given 到达每日 8:00 CST
When 系统发送推送
Then 推送送达率 ≥ 95%（三通道加权）
And 超时 10 分钟触发报警
```

### Scenario: 邮件兜底送达率 ≥ 98%（M4-FR-05）
```gherkin
Given 主推送通道（wx/apns/fcm/hms）不可用
When 系统发送通知
Then 邮件兜底送达率 ≥ 98%
And 使用阿里云 DirectMail
```

### Scenario: 推送发送失败但打卡仍成功（M4-FR-05）
```gherkin
Given 4 端推送 + 邮件兜底全失败
When 用户打卡
Then 打卡记录仍成功写入
And 返回业务码 E_NOTIFICATION_SEND_FAILED（warning）
And 不阻塞打卡流程
```
