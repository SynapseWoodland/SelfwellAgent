# ATDD-Push: 推送调度

> **版本**: V1.0
> **状态**: Draft
> **对应模块**: M13
> **对应 TDS**: `docs/architecture/TDS/TDS-M13-push-scheduler.md`
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`

---

## 一、定时推送任务

### Background
```gherkin
Background:
  Given 用户已登录并开启推送权限
  And 用户持有有效 push_token
```

### Scenario: 每日早 8:00 打卡提醒推送（M13-FR-01）
```gherkin
Given 到达每日 8:00 CST
When APScheduler 执行 push_daily_checkin
Then 向所有活跃用户发送打卡提醒推送
And 使用微信服务通知通道（wx_subscribe）
And 邮件兜底送达率 ≥ 98%
```

### Scenario: 推送 8:00 后 10 分钟未送达即报警（M13-FR-01）
```gherkin
Given 8:00 CST 推送任务执行
When 8:10 CST 检测到推送未送达
Then 触发超时报警（邮件 + IM）
And 记录 push_records.status='timeout'
And 运营介入处理
```

### Scenario: Day 7/14/21 主动回忆推送（M13-FR-01）
```gherkin
Given 用户注册已满 N 天（7/14/21）
And 用户已连续打卡满 N 天
When APScheduler 执行 push_day{N}_recall
Then 发送主动回忆通知
And 内容包含回顾邀请
And 附带小程序码
```

### Scenario: 连续 3 日未打卡关心推送（M13-FR-01）
```gherkin
Given 用户连续 3 日未打卡
When APScheduler 执行 send_streak_care（每日 9:00 CST）
Then 发送关心推送
And 内容为柔和话术（"今天累了就休息，明天的你还在这里。"）
```

---

## 二、推送通道

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
```

### Scenario: 微信小程序端走订阅消息（M13-FR-02）
```gherkin
Given 用户在微信小程序端
And 用户已授权订阅消息
When 系统发送推送
Then 通道为 wx_subscribe（wx.requestSubscribeMessage）
And 模板 ID 符合微信规范
```

### Scenario: iOS 端走 APNs（M13-FR-02）
```gherkin
Given 用户在 iOS 端
And 用户已注册 push_token
When 系统发送推送
Then 通道为 apns（firebase_messaging）
And payload 符合 APNs 规范
```

### Scenario: Android 端走 FCM（M13-FR-02）
```gherkin
Given 用户在 Android 端
And 用户已注册 push_token
When 系统发送推送
Then 通道为 fcm（firebase_messaging）
And payload 符合 FCM 规范
```

### Scenario: HarmonyOS 端走 HMS（M13-FR-02）
```gherkin
Given 用户在 HarmonyOS 端
And 用户已注册 push_token
When 系统发送推送
Then 通道为 hms（HMS Core Push Kit）
And payload 符合 HMS 规范
```

### Scenario: 全端邮件兜底（M13-FR-02）
```gherkin
Given 主推送通道不可用
When 系统发送通知
Then 邮件兜底送达率 ≥ 98%
And 使用阿里云 DirectMail
And 月免费额度 2000 封
```

---

## 三、DND（勿扰时段）

### Background
```gherkin
Background:
  Given 用户设置了 DND 时段（如 22:00~08:00）
```

### Scenario: DND 时段内推送抑制（M13-FR-03）
```gherkin
Given 用户设置 DND 22:00~08:00
And 推送时间落在 22:00~08:00
When 系统处理推送
Then 推送抑制
And 不立即发送
```

### Scenario: DND 结束后顺延补发（M13-FR-03）
```gherkin
Given 用户设置 DND 22:00~08:00
And 推送应于 7:00 发送但被 DND 抑制
When 8:00 DND 结束
Then 推送顺延补发
And 不堆积多条
And 仅补发 1 条
```

### Scenario: DND 跨 22:00 节点处理（M13-FR-03）
```gherkin
Given 推送应于 21:00 发送
And 用户 DND 为 22:00~08:00
When 21:00 时
Then 推送正常发送（不在 DND 内）

Given 推送应于 22:30 发送
And 用户 DND 为 22:00~08:00
When 22:30 时
Then 推送抑制，次日 9:00 补发
```

---

## 四、推送订阅管理

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
```

### Scenario: 用户可设置推送偏好（M13-FR-04）
```gherkin
Given 用户请求 PUT /api/v1/push/settings
When 用户设置推送开关（方案提醒 / 主动回忆 / 社区互动 / 活动推送）
Then 4 类推送各自独立开关
And 设置写入 user_push_preferences 表
And 返回更新成功
```

### Scenario: 用户可获取推送设置（M13-FR-04）
```gherkin
Given 用户请求 GET /api/v1/push/settings
When 系统处理请求
Then 返回当前 4 类推送的开关状态
And 包含推送通道信息
And 返回 DND 时段设置
```

### Scenario: 微信服务通知需用户授权订阅（M13-FR-04）
```gherkin
Given 用户首次进入推送设置
When 系统检测到未订阅
Then 引导用户授权订阅消息
And 使用 wx.requestSubscribeMessage
And 授权结果记录到 push_channel
```

---

## 五、降级策略

### Background
```gherkin
Background:
  Given 推送任务执行中
```

### Scenario: 微信服务通知发送失败重试（M13-FR-05）
```gherkin
Given 微信服务通知发送失败
When 系统记录 push_records.status='failed'
Then 重试 3 次（间隔 5 分钟）
And 3 次全失败后标记失败
And 不阻塞其他推送
```

### Scenario: 用户未订阅不重试（M13-FR-05）
```gherkin
Given 用户未订阅微信服务通知
When 系统尝试发送
Then 标记 push_records.status='not_subscribed'
And 不触发重试
And 降级为邮件兜底
```

### Scenario: 推送记录可追溯（M13-FR-05）
```gherkin
Given 推送任务执行完成
When 系统记录
Then 写入 push_records 表（user_id / push_type / status / sent_at / delivered_at）
And 记录用于送达率统计
```

---

## 六、推送送达率

### Background
```gherkin
Background:
  Given 推送任务统计周期为日
```

### Scenario: 三通道加权综合送达率 ≥ 95%（M13-FR-02）
```gherkin
Given 推送任务统计
When 计算送达率
Then 三通道加权综合送达率 ≥ 95%
And 权重：wx/apns/fcm/hms 为主，email 为兜底
And 超出阈值触发告警
```

### Scenario: 推送发送失败但打卡成功（M13-FR-05）
```gherkin
Given 4 端推送 + 邮件兜底全失败
When 用户打卡
Then 打卡记录仍成功写入
And push_records 标记失败
And 不阻塞打卡流程
```

---

## 七、APScheduler Job 配置

### Background
```gherkin
Background:
  Given APScheduler 已配置
```

### Scenario: push_daily_checkin cron 配置（M13-FR-01）
```gherkin
Given APScheduler 配置
When job_id='push_daily_checkin'
Then cron 表达式为每日 8:00 CST
And 时区 Asia/Shanghai
And misfire_grace_time=300
```

### Scenario: push_day{N}_recall date 配置（M13-FR-01）
```gherkin
Given 用户注册时间为 T
When 到达 T+N 天 8:00 CST
Then trigger date 执行 push_day{N}_recall
And 仅执行一次
```

### Scenario: send_streak_care cron 配置（M13-FR-01）
```gherkin
Given APScheduler 配置
When job_id='send_streak_care'
Then cron 表达式为每日 9:00 CST
And 时区 Asia/Shanghai
And 扫描连续 3 日未打卡用户
```

---

## 八、错误处理

### Scenario: push_token 缺失不发送（M13-FR-02）
```gherkin
Given 用户 push_token 为空
When 系统尝试发送推送
Then 跳过发送
And 记录 push_records.status='no_token'
And 不报错
```

### Scenario: 推送任务并发控制（M13-FR-05）
```gherkin
Given 推送任务量大
When 并发执行推送
Then Worker 并发数受控
And Redis 队列限流
And 不超出 LLM 月预算
```

---

## 九、引用说明

### 相关定义
- 降级策略：详见 [ATDD-Shared.md §五.3](../ATDD-Shared.md#五降级策略唯一真源m2m5m8共享)
- 错误码定义：详见 [ATDD-Shared.md §四](../ATDD-Shared.md#四错误码字典)

---

## 十、修订历史

| 日期 | 版本 | 改动 |
|------|------|------|
| 2026-07-21 | V1.0 | 初次创建 |
