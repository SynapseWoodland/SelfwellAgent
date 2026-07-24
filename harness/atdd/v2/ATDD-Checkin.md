# ATDD-Checkin: 每日打卡

> **版本**: V1.4
> **状态**: Draft
> **对应模块**: M4
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`
> **对应 TDS**: `docs/architecture/TDS/TDS-M4-checkin-loop.md`

---

## 一、每日打卡

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
And plan.current_day 已推进到当天 CST 自然日
When 用户点击"今日打卡"
Then 打卡成功
And 用户碎片 +1（不设递增系数）
And 用户连续天数 streak_days 计算（前一天未打卡则 streak_days=1，否则 +1）
And plan.current_day 不变（按方案自然日走，与打卡无关）
And 显示打卡成功话术（禁用"真的棒"）
And 返回打卡记录（id / fragments / streak_days / current_day）
```

**双轨字段说明**（PRD §1.3 已锁）：
- `plan.current_day` —— 按方案自然日推进，与是否打卡无关，用于进度环展示
- `streak_days` —— 从第 1 个打卡日起算，前一天未打卡即归 1，用于副文案/激励
- 补合场景下 streak 不补（仅 checkin.is_supplemental=true，streak 逻辑不变）

### Scenario: 打卡操作步骤 ≤ 2 步（M4-FR-01）

```gherkin
Given 用户在首页
When 用户完成跟练
Then 点"今日打卡"即可完成打卡
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
Given 用户尝试在 day > plan.current_day 或 day < plan.current_day 时打卡
When 用户点击打卡
Then 返回业务码 E_CHECKIN_DAY_INVALID
And 提示"打卡天数不连续（可补合 day ∈ [1, plan.current_day]）"
```

**说明**：
- 允许 day ∈ [1, plan.current_day] 范围内补合（PRD §1.3 已锁"补合不补 streak"）
- 仅禁止 day > plan.current_day（未来日期不可打卡）和 day < 1
- plan.current_day 按方案自然日走（见 ATDD-Plan §四 Scenario 'plan.current_day 按方案自然日推进'）

### Scenario: 跳过视频直接打卡须等待 30 秒（M4-FR-06）

```gherkin
Given 用户在 P35 打卡页面
And 用户未观看当日视频
When 用户进入打卡页面
Then "完成打卡"按钮处于 disabled 状态
And 按钮显示倒计时文案 "打卡(还剩 30 秒)"
When 倒计时归 0
Then "完成打卡"按钮 enabled,文案变为 "完成打卡"
And 用户可点击打卡
```

**说明**（PRD §1.3 边缘情况已锁）：
- 鼓励看视频但不强制，可直接跳过视频打卡
- 30 秒倒计时由前端实现，不走后端校验
- 已看完视频的用户不显示倒计时，按钮默认 enabled

### Scenario: streak 中断后归 1 重算（M4-FR-01 配套）

```gherkin
Given 用户 Day 1 打卡（streak_days=1）
And 用户 Day 2 打卡（streak_days=2）
And 用户 Day 3 未打卡
When 用户 Day 4 打卡
Then streak_days=1（中断归 1，从 Day 4 重新起算）
And checkin[Day 4].is_supplemental=false（Day 4 是当天正常打卡，非补合）
```

### Scenario: 补合打卡不补 streak（M4-FR-01 配套）

```gherkin
Given 用户 Day 1 打卡（streak_days=1）
And 用户 Day 2/3 未打卡
When 用户 Day 4 点击"补合 Day 3"再点击"今日打卡"
Then checkin[Day 3].is_supplemental=true
And checkin[Day 4].is_supplemental=false
And streak_days=1（补卡只更新状态，不补 streak；Day 4 当天从 1 起算）
```

### Scenario: 30 分钟内可编辑心情（M4-FR-07）

```gherkin
Given 用户 5 分钟前完成打卡（含 feeling="今天肩膀放松了"）
When 用户在打卡完成页点击"编辑感想"
Then 系统允许更新 checkin.feeling
And 校验字数 ≤ 50 字
When 用户在打卡 35 分钟后尝试编辑感想
Then 返回业务码 E_CHECKIN_EDIT_WINDOW_EXPIRED
And 提示"已超过 30 分钟编辑窗口"
```

**说明**（PRD §1.3 边缘情况已锁）：
- 编辑窗口 = 打卡完成时刻起 30 分钟（仅 own + 30 min 内可编辑）
- 由后端 PATCH /api/v1/checkins/{id} 实现，物理层校验 user_id 匹配 + 时间窗口
- 超出窗口不提供编辑，避免历史打卡被频繁改动影响统计稳定性

---

## 二、三档柔性话术

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
When 系统在 Day 2 10:00 检测到连续未打卡
Then 发送推送"想休息一天也可以，先把今天的你抱抱。我们慢慢来。"
And 显示抱抱卡入口
```

**时序锚点**（PRD §1.3 边缘情况已锁）：
- Day 1 未打卡 → 19:00 推送（"今天累了就休息"）
- Day 2 未打卡 → 10:00 推送（"想休息一天也可以"）+ 显示抱抱卡入口
- Day 3+ 未打卡 → Persona slight_hug 态切换（轻量关心，不强推送）

### Scenario: 今日未打卡 Day 1 19:00 推送温柔话术（M4-FR-02）

```gherkin
Given 用户当日 19:00 前未打卡
When 系统在 19:00 检测到当日未打卡
Then 发送推送"今天累了就休息，明天的你还在这里。"
```

---

## 三、进度环

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

### Scenario: 跨用户访问日历返回 403（M4-FR-03 安全防护）

```gherkin
Given 用户 A 持有 JWT(user_id=A)
When 用户 A 请求 GET /api/v1/checkins/calendar
Then 返回用户 A 自己的 calendar 数据（user_id=A 过滤）
And 不包含任何 user_id=B 的数据

Given 用户 A 持有 JWT(user_id=A)
And URL path 显式包含 ?user_id=B（尝试越权）
When 用户 A 请求 GET /api/v1/checkins/calendar?user_id=B
Then 返回 HTTP 403 + 业务码 E_ASSISTANT_FORBIDDEN_CALLER
And 后端强制以 JWT.user_id 为准，忽略 URL 参数
```

**说明**：
- TDS-M4 §6.2 calendar 端点强制 `WHERE user_id = JWT.user_id` 过滤
- 由 Safety Gateway 在网关层校验 + 后端 Service 层二次校验
- L5 grep 兜底：跨用户访问 attempt 应 0 命中

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

## 四、打卡日历

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

## 五、推送送达

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
And push_records 标记失败
And 不阻塞打卡流程
```

### Scenario: Day 7/14/21 08:00 推送回忆气泡（M4-FR-08，M4→M8 联动）

```gherkin
Given 用户 plan.current_day 达到 7/14/21
And 用户当天已完成打卡
When 系统到达 Day N 08:00 CST
Then 推送回忆气泡 + 微信订阅消息
And 推送文案遵守 Recall Safety 三层防线（ADR-0017）
And 不出现"坚持 X 天""效果对比"等违规词
```

**说明**（PRD §1.9.2 + PRD §0 已锁）：
- 触发锚点：`active plan.started_at` 起算
- 条件：plan.current_day 达到 7/14/21 **且** 当天打卡完成
- 完整 Recall 规则见 [ATDD-Recall.md §一](../ATDD-Recall.md#一ai-主动触发day-n)
- M4 仅负责"判定是否触发"+ "发出推送任务",具体内容生成由 M8 服务处理

### Scenario: 社区审核结果实时推送（M4-FR-09，M4→M6 联动）

```gherkin
Given 用户在社区发帖后审核通过
When 审核状态变更（pending → approved）
Then 系统实时推送通知
And 推送文案使用 ACK 池（30 条 ≤ 30 字）
And 通道：微信订阅消息（小程序）/ FCM（App）
```

**说明**（PRD §1.9.2 已锁）：
- M4 推送模块统一编排（M13 Scheduler），打卡/回忆/社区三类推送共享通道
- 打卡推送失败不影响社区推送（推送任务独立调度）

---

## 六、打卡与其他模块的关系

### Scenario: 打卡不影响7天未feedback判定（M4→M5边界）

```gherkin
Given 用户今日已打卡
And 用户7天前提交过feedback，之后无任何feedback
When M5 检查7天未feedback状态
Then M5 仍判定为"7天未feedback"
And 打卡动作本身不算作feedback
```

**说明**：
- 打卡 ≠ feedback，两者独立
- 7天未feedback只看 feedback 表的 `created_at`，不查 checkins 表
- 判定公式：`当前时间 - MAX(feedback.created_at) > 7天`

### Scenario: 打卡感想与feedback无关（M4业务边界）

```gherkin
Given 用户完成视频跟练
When 用户点击打卡并填写感想
Then 打卡记录写入 checkins 表（含 feeling 字段）
And 打卡感想仅存储在 checkins.feeling，不写入 feedback 表
```

**说明**：
- 打卡感想存在 `checkins.feeling` 字段（最长50字）
- feedback 是独立的 M7 功能，type 包括 mood_text / mood_photo 等
- 两者数据模型完全独立，无关联

### Scenario: 打卡触发回忆气泡显示（M4→M8边界说明）

```gherkin
Given 用户 plan.current_day 达到 7/14/21
And 用户当天已完成打卡
When Celery Beat 定时触发 auto_day{N}
Then M8 服务发送推送 + P03a 主页出现回忆气泡
And 触发条件：plan.current_day 达到 N（**不要求连续打卡**）
```

**说明**（PRD §0 + PRD §1.8 已锁 + ATDD-Plan §四）：
- **触发方式是系统定时推送**，不是用户进入 P03a
- **触发条件是 plan.current_day 达到 7/14/21**，而非累计或连续打卡天数
- 打卡中断用户依然可获得抱抱卡（只是文案会温柔一些）
- 完整定义见 [ATDD-Recall.md §一](../ATDD-Recall.md#一ai-主动触发day-n)
- 抱抱卡文案规则见 PRD §1.8（禁用"坚持 X 天"，用"和你走过的 {n} 天"）

---

## 七、引用说明

### 相关定义

- 打卡状态枚举：详见 [ATDD-Shared.md §一.4](../ATDD-Shared.md#一用户状态枚举)
- feedback定义：详见 [ATDD-Shared.md §二](../ATDD-Shared.md#二feedback-定义唯一真源m7m5m8共享)
- ACK禁用词：详见 [ATDD-Shared.md §三.2](../ATDD-Shared.md#三合规红线)
- 错误码定义：详见 [ATDD-Shared.md §四](../ATDD-Shared.md#四错误码字典)
- 用户旅程：详见 [ATDD-Journey.md §三](../ATDD-Journey.md#三方案旅程)

---

## 八、修订历史

| 日期 | 版本 | 改动 |
| ---------- | ---- | -------------------- |
| 2026-07-21 | V1.0 | 初次创建，补充打卡与feedback关联 |
| 2026-07-21 | V1.1 | 修正错误设计：打卡≠feedback，两者独立，无需同步；M5判定只看feedback.created_at |
| 2026-07-21 | V1.3 | 修正回忆气泡场景：触发方式是Celery Beat定时推送（非用户进入）；条件是连续打卡（非累计） |
| 2026-07-22 | V1.4 | **架构评审对齐 12 项修复**：① day 校验改补合语义（Scenario 4）；② streak 双轨字段（Scenario 1）；③ 30s 倒计时（FR-06）；④ 30min 编辑心情（FR-07 + PATCH 端点）；⑤ 抱抱卡双轨触发（§六）；⑥ 推送覆盖 Day 7/14/21 + 社区审核（FR-08/09）；⑦ 19:00/10:00 时序锚点（§二）；⑧ 进度环越权防护（§三 Scenario 跨用户 403） |


