# TDS-M12: 时区处理 - 验收标准

> **版本**: V2.0
> **状态**: Draft
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`
>
> **架构变更说明**: V2.0 从"固定北京时间"改为"数据库 UTC + 前端当地时间"
> - 数据库统一存 UTC（全球唯一基准）
> - 前端根据用户时区显示当地时间（用户体验最佳）
> - 与业界最佳实践（字节跳动/TikTok/微信海外版）一致

---

## Feature: 全链路时区架构

### Background
```gherkin
Background:
  Given 数据库时间列类型为 TIMESTAMPTZ（PostgreSQL）
  And 内部统一存储 UTC 时间（+00:00）
  And API 返回 ISO 8601 字符串（+00:00）
  And 前端根据 user.timezone 显示当地时间
  And 未设置时区的用户默认 Asia/Shanghai
```

### Scenario: DB 层存储 UTC（M12-FR-01）
```gherkin
Given 数据库时间列类型为 TIMESTAMPTZ
When 后端写入时间数据
Then 内部存储为 UTC（+00:00）
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

### Scenario: 前端根据用户时区显示当地时间（M12-FR-03）
```gherkin
Given 前端收到 API 返回 "2026-07-14T08:30:00+00:00"
And 用户时区为 Asia/Shanghai（UTC+8）
When 前端格式化显示
Then 显示 16:30（北京时间）
```

### Scenario: 中国用户时区显示北京时间（M12-FR-03）
```gherkin
Given API 返回 "2026-07-14T08:30:00+00:00"
And 用户时区 user.timezone = "Asia/Shanghai"
When 前端调用 formatLocalTime()
Then 显示 "16:30"（北京时间，UTC+8）
And 不是 UTC 时间的 08:30
```

### Scenario: 日本用户时区显示东京时间（M12-FR-03）
```gherkin
Given API 返回 "2026-07-14T08:30:00+00:00"
And 用户时区 user.timezone = "Asia/Tokyo"
When 前端调用 formatLocalTime()
Then 显示 "17:30"（东京时间，UTC+9）
And 不是北京时间的 16:30
```

### Scenario: 美国用户时区显示纽约时间（M12-FR-03）
```gherkin
Given API 返回 "2026-07-14T08:30:00+00:00"
And 用户时区 user.timezone = "America/New_York"
When 前端调用 formatLocalTime()
Then 显示 "04:30"（纽约时间，UTC-4，夏令时）
And 不是 UTC 时间的 08:30
```

### Scenario: 未设置时区用户默认北京时间（M12-FR-03）
```gherkin
Given 用户首次使用 App
And user.timezone 字段为空
When 前端格式化时间
Then 默认使用 Asia/Shanghai 时区
And 显示北京时间
```

---

## Feature: 用户时区管理

### Background
```gherkin
Background:
  Given 用户首次打开 App 时记录设备时区
  And 用户可在设置页手动修改时区
```

### Scenario: 首次登录自动获取设备时区（M12-FR-03）
```gherkin
Given 用户首次登录 App
When M1 登录成功
Then 后端从请求头 X-Timezone 或前端传递的 timezone 参数获取设备时区
And 存入 user.timezone 字段（默认 "Asia/Shanghai"）
And 用户设置页面显示当前时区
```

### Scenario: 用户修改时区（M12-FR-03）
```gherkin
Given 用户在设置页面
When 用户选择时区 "Asia/Tokyo"
Then 更新 user.timezone = "Asia/Tokyo"
And 所有时间显示立即切换为东京时间
And 已显示的历史时间需要刷新才能更新
```

### Scenario: 时区字段数据结构（M12-FR-03）
```gherkin
Given 用户表 users
When 设计表结构
Then 包含 timezone 字段 VARCHAR(50) DEFAULT 'Asia/Shanghai'
And 支持 IANA 时区标识符（Asia/Shanghai, Asia/Tokyo, America/New_York 等）
```

---

## Feature: 统一时间工具

### Background
```gherkin
Background:
  Given 前端使用 utils/time.ts
  And 前端从 user.timezone 读取用户时区
```

### Scenario: formatLocalTime 正确输出 HH:mm（M12-FR-04）
```gherkin
Given 输入 "2026-07-14T08:30:00+00:00"
And 用户时区 = Asia/Shanghai
When 调用 formatLocalTime()
Then 返回 "16:30"（北京时间）
And 正确处理 UTC+8 时差
```

### Scenario: formatLocalTime 受设备时区影响（M12-FR-04）
```gherkin
Given 输入 "2026-07-14T08:30:00+00:00"
And 用户时区 = Asia/Tokyo
When 调用 formatLocalTime()
Then 返回 "17:30"（东京时间）
And 正确处理 UTC+9 时差
```

### Scenario: formatChatTime 正确区分今天/昨天（M12-FR-04）
```gherkin
Given 消息时间为今天当地时间 23:30
And 用户时区 = Asia/Shanghai
When 调用 formatChatTime()
Then 返回 "23:30"

Given 消息时间为昨天当地时间 22:00
When 调用 formatChatTime()
Then 返回 "昨天 22:00"
```

### Scenario: formatChatTime 跨年显示完整日期（M12-FR-04）
```gherkin
Given 消息时间为去年 12-31 当地时间 23:30
When 调用 formatChatTime()
Then 返回 "2025-12-31 23:30"
And 包含完整年份
```

### Scenario: todayInUserTZ 返回用户当地当天日期（M12-FR-04）
```gherkin
Given 用户时区 = Asia/Tokyo
When 调用 todayInUserTZ()
Then 返回东京当天日期（yyyy-mm-dd）
And 不是 UTC 当天日期
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
And 提示改用 todayInUserTZ()
```

---

## Feature: 智能管家聊天气泡时间戳

### Background
```gherkin
Background:
  Given 用户在 P03a 智能管家对话页
  And 用户时区从 user.timezone 读取
```

### Scenario: 聊天气泡显示 HH:mm 时间戳（M12-FR-06）
```gherkin
Given 用户发送消息
When 消息渲染
Then 气泡下方显示消息时间戳（HH:mm）
And 字号 11px，颜色 #999
And 位置居中或左对齐
And 使用 formatLocalTime() 格式化
```

### Scenario: 跨日消息显示昨天时间（M12-FR-06）
```gherkin
Given 消息为昨天当地时间 18:00 发送
When 消息渲染
Then 显示 "昨天 18:00"
And 基于用户时区判断"昨天"
```

### Scenario: 跨年消息显示完整日期时间（M12-FR-06）
```gherkin
Given 消息为去年 12-31 当地时间 15:00 发送
When 消息渲染
Then 显示 "2025-12-31 15:00"
```

### Scenario: SSE start 事件包含 UTC 时间（M12-FR-06）
```gherkin
Given 后端推送 SSE start 事件
When 事件构造
Then payload 包含 created_at: datetime.now(timezone.utc).isoformat()
And 前端写入 ChatTurn.createdAt
```

### Scenario: 历史 sessions 回填时间戳（M12-FR-06）
```gherkin
Given 用户拉取历史 sessions 消息列表
When GET /assistant/sessions/{id}/messages
Then 消息列表包含 created_at 字段（UTC ISO）
And 前端根据 user.timezone 转换为当地时间显示
And 时间戳正确渲染
```

---

## Feature: 后端时区安全规范

### Background
```gherkin
Background:
  Given OpenAPI V1.1.0 已定义
  And Python >= 3.12
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
When 代码中调用 datetime.now()
Then ruff 自定义规则捕获
And CI 失败
And 提示使用 datetime.now(timezone.utc)
```

### Scenario: 后端禁止使用 datetime.utcnow()（M12-FR-01）
```gherkin
Given 后端代码
When 代码中调用 datetime.utcnow()
Then ruff 自定义规则捕获
And CI 失败
And 提示使用 datetime.now(timezone.utc)
```

### Scenario: 后端推荐使用 ZoneInfo（M12-FR-01）
```gherkin
Given 后端需要时区转换
When 实现时间逻辑
Then 推荐使用 from zoneinfo import ZoneInfo
And 避免使用 pytz（已弃用）
And 示例：
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# 获取 UTC 时间
utc_now = datetime.now(timezone.utc)

# 转换为用户当地时间
user_tz = ZoneInfo("Asia/Shanghai")
local_time = utc_now.astimezone(user_tz)
"""
```

---

## Feature: 跨日边界正确性

### Background
```gherkin
Background:
  Given 用户时区为 Asia/Shanghai
  And 北京时间跨日边界（23:59:59 → 00:00:00）
```

### Scenario: 23:59:59 当地时间显示为今天（M12-FR-04）
```gherkin
Given 消息时间为今天当地时间 23:59:59
When 调用 formatChatTime()
Then 返回 "23:59"
And 判断为今天
```

### Scenario: 00:00:00 当地时间显示为今天（M12-FR-04）
```gherkin
Given 消息时间为当地时间 00:00:00（次日）
When 调用 formatChatTime()
Then 返回 "00:00"
And 判断为今天
```

### Scenario: todayInUserTZ 跨日边界正确（M12-FR-04）
```gherkin
Given 用户时区 = Asia/Shanghai
And 北京时间 2026-07-14 23:59
When 调用 todayInUserTZ()
Then 返回 "2026-07-14"

Given 北京时间 00:00（次日）
When 调用 todayInUserTZ()
Then 返回 "2026-07-15"
```

### Scenario: 不同时区的跨日边界（M12-FR-04）
```gherkin
Given 用户时区 = Asia/Tokyo
And 东京时间 2026-07-14 23:59
When 调用 todayInUserTZ()
Then 返回 "2026-07-14"

Given 东京时间 00:00（次日）
When 调用 todayInUserTZ()
Then 返回 "2026-07-15"
```

---

## Feature: 视觉基线守护

### Background
```gherkin
Background:
  Given 用户时区 = Asia/Shanghai
```

### Scenario: 中国用户聊天页显示北京时间（M12-FR-03）
```gherkin
Given 用户时区 = Asia/Shanghai
When 用户进入 P03a 聊天页
Then 视觉基线截图显示 16:30（北京时间）
```

### Scenario: 日本用户聊天页显示东京时间（M12-FR-03）
```gherkin
Given 用户时区 = Asia/Tokyo
When 用户进入 P03a 聊天页
Then 视觉基线截图显示 17:30（东京时间）
```

### Scenario: 美国用户聊天页显示纽约时间（M12-FR-03）
```gherkin
Given 用户时区 = America/New_York
When 用户进入 P03a 聊天页
Then 视觉基线截图显示 04:30（纽约时间，夏令时）
```

### Scenario: 视觉基线测试 case 新增（M12-FR-06）
```gherkin
Given 视觉基线测试套件
When 测试更新
Then 新增 case: 15j-assistant-home-chat-timestamp
And 新增 case: timestamp-asia-tokyo（东京时区）
And 新增 case: timestamp-america-new-york（纽约时区）
And 测试覆盖气泡时间戳样式和各时区显示
```

---

## Feature: 推送时间调度（关联 M13）

### Background
```gherkin
Background:
  Given M13 推送使用用户当地时间 8:00
  And 后端调度需转换为 UTC 时间
```

### Scenario: 推送调度转换为 UTC（M12-FR-01）
```gherkin
Given 用户时区 = Asia/Shanghai
And 用户设置推送时间为当地时间 08:00
When APScheduler 计算调度时间
Then 转换为 UTC 时间 00:00（次日）
And 数据库记录 UTC 时间
And 推送按 UTC 时间触发
```

### Scenario: 日本用户推送调度（M12-FR-01）
```gherkin
Given 用户时区 = Asia/Tokyo
And 用户设置推送时间为当地时间 08:00
When APScheduler 计算调度时间
Then 转换为 UTC 时间 23:00（前一天）
And 数据库记录 UTC 时间
```

---

## Feature: 数据库迁移（可选，出海时执行）

### Background
```gherkin
Background:
  Given 历史数据存的是北京时间（UTC+8 的 UTC 表示）
  And 需要迁移到真正的 UTC
```

### Scenario: 历史数据时区迁移（M12-FR-01）
```gherkin
Given 数据库现有 created_at 存的是北京时间
When 执行迁移脚本
Then 所有时间字段 +8 小时转换为真正的 UTC
And 迁移前后数据一致性验证
And 迁移后回滚脚本可用
```

---

## Appendix: IANA 时区标识符参考

| 地区 | IANA 时区标识符 | UTC 偏移 | 夏令时 |
|------|-----------------|----------|--------|
| 北京 | Asia/Shanghai | +8 | 无 |
| 上海 | Asia/Shanghai | +8 | 无 |
| 香港 | Asia/Hong_Kong | +8 | 无 |
| 台北 | Asia/Taipei | +8 | 无 |
| 东京 | Asia/Tokyo | +9 | 无 |
| 首尔 | Asia/Seoul | +9 | 无 |
| 新加坡 | Asia/Singapore | +8 | 无 |
| 纽约 | America/New_York | -5/-4 | 有 |
| 洛杉矶 | America/Los_Angeles | -8/-7 | 有 |
| 伦敦 | Europe/London | +0/+1 | 有 |
| 巴黎 | Europe/Paris | +1/+2 | 有 |
| 悉尼 | Australia/Sydney | +10/+11 | 有 |

> **注意**: Python 使用 `zoneinfo.ZoneInfo`，前端小程序使用 `moment-timezone` 或 `date-fns-tz`
