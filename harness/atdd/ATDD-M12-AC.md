# TDS-M12: 时区显示 - 验收标准

> **版本**: V1.0
> **状态**: Draft
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`

---

## Feature: 全链路时区统一

### Background
```gherkin
Background:
  Given 数据库存储 TIMESTAMPTZ（UTC）
  And API 返回 ISO 8601 字符串（+00:00）
  And 前端统一 Asia/Shanghai 显示
```

### Scenario: DB 层存储 UTC（M12-FR-01）
```gherkin
Given 数据库时间列类型为 TIMESTAMPTZ
When 后端写入时间数据
Then 内部存储为 UTC
And server_default = NOW() 也是 UTC
And 无任何本地时区时间写入
```

### Scenario: API 层透传 UTC ISO（M12-FR-02）
```gherkin
Given 后端有时间字段 created_at=2026-07-14T08:30:00 UTC
When API 序列化响应
Then 返回 ISO 8601 字符串 "2026-07-14T08:30:00+00:00"
And 不做 .astimezone() 二次转换
And 格式带 +00:00 UTC 标识
```

### Scenario: 前端所有时间格式化统一 Asia/Shanghai（M12-FR-03）
```gherkin
Given 前端收到 API 返回 "2026-07-14T08:30:00+00:00"
When 前端格式化显示
Then 统一走 utils/time.ts
And 设备切 Tokyo / LA 时显示不变（北京时间 16:30）
And 不使用设备本地时区
```

### Scenario: 设备时区为 Tokyo 时显示北京时间（M12-FR-03）
```gherkin
Given 设备时区 = Asia/Tokyo (UTC+9)
And 后端返回 "2026-07-14T08:30:00+00:00"
When 前端格式化
Then 显示 16:30（北京时间，UTC+8）
And 不是本地时间 17:30
```

### Scenario: 设备时区为 LA 时显示北京时间（M12-FR-03）
```gherkin
Given 设备时区 = America/Los_Angeles (UTC-7)
And 后端返回 "2026-07-14T08:30:00+00:00"
When 前端格式化
Then 显示次日 00:30（北京时间，UTC+8）
And 不是本地时间前一天 01:30
```

---

## Feature: 统一时间工具

### Background
```gherkin
Background:
  Given 前端使用 utils/time.ts
```

### Scenario: formatHM 正确输出 HH:mm（M12-FR-04）
```gherkin
Given 输入 "2026-07-14T08:30:00+00:00"
When 调用 formatHM()
Then 返回 "16:30"（Asia/Shanghai）
And 不受设备时区影响
```

### Scenario: formatChatTime 正确区分今天/昨天（M12-FR-04）
```gherkin
Given 消息时间为今天 CST 23:30
When 调用 formatChatTime()
Then 返回 "23:30"

Given 消息时间为昨天 CST 22:00
When 调用 formatChatTime()
Then 返回 "昨天 22:00"
```

### Scenario: formatChatTime 跨年显示完整日期（M12-FR-04）
```gherkin
Given 消息时间为去年 12-31 CST 23:30
When 调用 formatChatTime()
Then 返回 "2025-12-31 23:30"
And 包含完整年份
```

### Scenario: todayInCST 返回北京当天日期（M12-FR-04）
```gherkin
Given 设备时区 = Asia/Tokyo
When 调用 todayInCST()
Then 返回北京时间当天日期（yyyy-mm-dd）
And 不是东京当天日期
```

### Scenario: 前端禁止使用 getHours() 等本地方法（M12-FR-05）
```gherkin
Given 前端代码
When 代码中调用 new Date().getHours()
Then grep 规则捕获此违规
And CI 失败
And 提示改用 utils/time.ts
```

### Scenario: 前端禁止使用 toISOString().slice(0,10) 取业务日期（M12-FR-05）
```gherkin
Given 前端代码
When 代码中调用 toISOString().slice(0,10) 取业务日期
Then grep 规则捕获此违规
And CI 失败
And 提示改用 todayInCST()
```

---

## Feature: 智能管家聊天气泡时间戳

### Background
```gherkin
Background:
  Given 用户在 P03a 智能管家对话页
```

### Scenario: 聊天气泡显示 HH:mm 时间戳（M12-FR-06）
```gherkin
Given 用户发送消息
When 消息渲染
Then 气泡下方显示消息时间戳（HH:mm）
And 字号 11px，颜色 #999
And 位置居中或左对齐
```

### Scenario: 跨日消息显示昨天时间（M12-FR-06）
```gherkin
Given 消息为昨天 CST 18:00 发送
When 消息渲染
Then 显示 "昨天 18:00"
```

### Scenario: 跨年消息显示完整日期时间（M12-FR-06）
```gherkin
Given 消息为去年 12-31 CST 15:00 发送
When 消息渲染
Then 显示 "2025-12-31 15:00"
```

### Scenario: SSE start 事件包含 created_at（M12-FR-06）
```gherkin
Given 后端推送 SSE start 事件
When 事件构造
Then payload 包含 created_at: datetime.now(UTC).isoformat()
And 前端写入 ChatTurn.createdAt
```

### Scenario: 历史 sessions 回填时间戳（M12-FR-06）
```gherkin
Given 用户拉取历史 sessions 消息列表
When GET /assistant/sessions/{id}/messages
Then 消息列表包含 created_at 字段
And 前端回填 ChatTurn.createdAt
And 时间戳正确渲染
```

---

## Feature: 后端零改动（API 契约冻结）

### Background
```gherkin
Background:
  Given OpenAPI V1.1.0 已定义
```

### Scenario: API 契约不变（M12-FR-02）
```gherkin
Given OpenAPI schema 定义时间字段为 string（ISO 8601）
When 后端实现
Then 不改字段类型为 datetime
And 不改序列化格式
And API diff = 0
```

### Scenario: 后端禁止使用 datetime.now() 无参（M12-FR-01）
```gherkin
Given 后端代码
When 代码中调用 datetime.now() 无参
Then ruff 自定义规则捕获
And CI 失败
And 提示使用 datetime.now(UTC)
```

### Scenario: 后端禁止使用 datetime.utcnow()（M12-FR-01）
```gherkin
Given 后端代码
When 代码中调用 datetime.utcnow()
Then ruff 自定义规则捕获
And CI 失败
And 提示使用 datetime.now(UTC)
```

---

## Feature: 跨日边界正确性

### Background
```gherkin
Background:
  Given 北京时间跨日边界（23:59:59 → 00:00:00）
```

### Scenario: 23:59:59 CST 显示为今天（M12-FR-04）
```gherkin
Given 消息时间为 CST 23:59:59
When 调用 formatChatTime()
Then 返回 "23:59"
And 判断为今天
```

### Scenario: 00:00:00 CST 显示为今天（M12-FR-04）
```gherkin
Given 消息时间为 CST 00:00:00（次日）
When 调用 formatChatTime()
Then 返回 "00:00"
And 判断为今天
```

### Scenario: todayInCST 跨日边界正确（M12-FR-04）
```gherkin
Given 北京时间 2026-07-14 23:59
When 调用 todayInCST()
Then 返回 "2026-07-14"
And 北京时间 00:00（次日）
Then 返回 "2026-07-15"
```

---

## Feature: 视觉基线守护

### Background
```gherkin
Background:
  Given 设备时区切 Tokyo 和 LA 各跑一遍
```

### Scenario: 设备切 Tokyo 时聊天页显示北京时间（M12-FR-03）
```gherkin
Given 设备时区 = Asia/Tokyo
When 用户进入 P03a 聊天页
Then 视觉基线截图显示 16:30（北京时间）
And 与设备本地时间 17:30 不同
```

### Scenario: 设备切 LA 时聊天页显示北京时间（M12-FR-03）
```gherkin
Given 设备时区 = America/Los_Angeles
When 用户进入 P03a 聊天页
Then 视觉基线截图显示次日 00:30（北京时间）
And 与设备本地时间不同
```

### Scenario: 视觉基线测试 case 新增（M12-FR-06）
```gherkin
Given 视觉基线测试套件
When 测试更新
Then 新增 case: 15j-assistant-home-chat-timestamp
And 新增基线截图
And 测试覆盖气泡时间戳样式
```
