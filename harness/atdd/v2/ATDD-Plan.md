# ATDD-Plan: 21 天方案

> **版本**: V1.1
> **状态**: Draft
> **对应模块**: M3
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`
> **对应 TDS**: `docs/architecture/TDS/TDS-M3-21day-plan.md`
>
> **变更说明（V1.0 → V1.1）**:
> - 删 3 阶段表述：与 PRD §3.3 锁定的"21 天单循环"对齐（TDS/前端同步调整）
> - 补 `plan_days` 子表场景（PRD V1.1 §1.2 锁定）
> - 补 `plan.current_day` / `streak_days` 双轨规则（PRD §1.3 锁定）
> - 补 `lifecycle_stage` 联动（PRD §0.x.7 锁定 + M3-Q6 fix：跃迁公式改为 `completed_days_d1_to_d7 >= 5`）
> - 补 P03c 交付页路由 + 「从今天开始」激活语义（PRD V1.1 + 前端 15h）
> - 补 7 天缓存命中横幅（PRD §1.1 报告缓存 + 前端 G6 ATDD-M2-FR-02）
> - 补 LLM 月预算 ¥700 熔断场景（PRD §4.1）

---

## 一、21 天方案生成

### Background

```gherkin
Background:
  Given 用户已完成 M2 智能分析
  And distinct 部位数 N = 1 或 2 或 3
  And 用户持有有效 JWT
```

### Scenario: 基于 distinct 部位数生成 N 个视频，21 天循环（M3-FR-01）

```gherkin
Given 用户已完成 M2 distinct，得到 N 个部位（N ∈ {1, 2, 3}）
When 用户点击"生成 21 天方案"
Then 系统生成 N 个视频（每个部位对应 1 个视频）
And 每天任务 = N 个视频（循环播放）
And 21 天内每天任务相同
And plan_status='generating'（生成中，transient）
```

### Scenario: N=1 时每天仅 1 个任务（M3-FR-02）

```gherkin
Given M2 distinct 部位数 N=1
When 方案已生成
Then 每天仅有 1 个视频任务
And 21 天每天都是这同一个视频
And plan_status='active'
```

### Scenario: N=2 时每天 2 个任务（M3-FR-02）

```gherkin
Given M2 distinct 部位数 N=2
When 方案已生成
Then 每天有 2 个视频任务
And 21 天每天都是这 2 个视频
```

### Scenario: N=3 时每天 3 个任务（M3-FR-02）

```gherkin
Given M2 distinct 部位数 N=3
When 方案已生成
Then 每天有 3 个视频任务
And 21 天每天都是这 3 个视频
```

### Scenario: 方案生成后进入 P03c 交付页（M3-FR-01 新增）

```gherkin
Given 用户在 P03b 诊断报告过渡页
When 用户点击"生成我的 21 天方案"
And 系统生成方案完成（plan_status='generating' → 'queued'）
Then 跳转至 P03c 方案交付页
And 显示方案摘要（21 天 · N 个视频 · 视频池 ≥50 已匹配）
And 显示 5 天预览（前 5 天任务列表）
And 显示「从今天开始」+「先看完整方案」两个按钮
And plan_status='queued'（已生成未激活）
```

### Scenario: 用户点击「从今天开始」激活方案（M3-FR-01 新增）

```gherkin
Given 用户在 P03c 方案交付页
And plan_status='queued'（已生成未激活）
When 用户点击「从今天开始」按钮
Then plan_status 由 'queued' 变为 'active'
And plans.started_at 写入当前 CST 时间戳
And plans.current_day 初始化为 1
And 跳转至 P15b 今天 Tab
And 进度环显示 day=1/21
And 今日任务卡片显示 Day 1 视频
```

### Scenario: 用户点击「先看完整方案」跳日历（M3-FR-01 新增）

```gherkin
Given 用户在 P03c 方案交付页
When 用户点击「先看完整方案」按钮
Then 跳转至 P15f-plan-tabs-5state 页面
And 显示 5 态 Tab：今天 / 全部 21 天 / 本周 / ...
And 用户可点 Day 单元格查看当日任务详情
And 方案保持 'queued' 状态（用户未点「从今天开始」前 started_at 为 NULL）
```

---

## 二、视频匹配算法

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

### Scenario: 7 天缓存命中横幅（M3-FR-01 新增，前端 G6 ATDD-M2-FR-02）

```gherkin
Given 用户在 7 天内已完成 M2 诊断
And 报告缓存命中（cached=true）
When 用户进入 P03b 诊断报告过渡页
Then 页面顶部渲染"上次报告 · 缓存命中"横幅
And 副文案显示"7 天内不重复生成 · 不消耗 AI 额度"
And 用户可点"重新分析"按钮强制重新诊断
```

---

## 三、今日任务获取

### Background

```gherkin
Background:
  Given 用户已激活方案 plan_id='xxx'
  And 方案包含 N 个视频（N = distinct 部位数）
  And 当前日期为方案开始后第 N 天
```

### Scenario: 获取今日任务（M3-FR-04）

```gherkin
Given 用户已激活方案
When 用户 GET /api/v1/plans/today
Then 返回今日任务（day / tasks）
And tasks 包含 N 个视频（对应 N 个部位）
And tasks 包含 video_id / title / source / thumbnail / duration_sec / body_part
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

### Scenario: LLM 月预算超 ¥700 触发熔断（M3-FR-01 新增，PRD §4.1）

```gherkin
Given 当前 LLM 月累计成本已达 ¥700
When 用户请求生成方案
Then 返回业务码 E_PLAN_BUDGET_EXCEEDED
And 提示"本月方案生成额度已用完，下月自动恢复"
And 系统降级到基于档案标签的规则引擎方案（不调用 LLM）
```

---

## 四、方案状态同步与生命周期联动

### Background

```gherkin
Background:
  Given 用户激活方案 plan_id='xxx'
  And plans.started_at 已写入
  And plans.current_day 由方案自然日派生
  And user.lifecycle_stage ∈ {new, maturing, matured, retained}
```

### Scenario: 方案激活时初始化 started_at 与 current_day（M3-FR-01 新增）

```gherkin
Given 用户在 P03c 交付页点击「从今天开始」
When 系统更新 plan_status='active'
Then plans.started_at 写入当前 CST 时间戳
And plans.current_day = 1
And plans.lifecycle_stage 同步写入 'maturing'（由 user.lifecycle_stage 派生）
```

### Scenario: 方案进度与打卡连续天数独立计算（M3-FR-04 新增，PRD §1.3）

```gherkin
Given 用户 Day 1 打卡、Day 2 打卡、Day 3 未打卡、Day 4 打卡
When 用户进入 P15b 今天 Tab
Then 进度环显示 plan.current_day=4
And 副文案显示 streak_days=1（Day 3 中断归 1，从第 1 个打卡日起算）
And 抱抱卡**未**触发（current_day=4 未达 7）
```

### Scenario: plan.current_day 按方案自然日推进（M3-FR-04 新增）

```gherkin
Given plans.started_at = 2026-07-21T08:00:00+08:00
When 系统在 2026-07-22T00:00:00+08:00 跨日
Then plans.current_day 自动 +1（CST 日历日推进）
And 与用户是否打卡无关
And streak_days 独立计算（与当前 day 是否打卡不联动）
```

### Scenario: 方案生成触发 maturing 态（M3-FR-01 新增，PRD §0.x.7.2）

```gherkin
Given 用户 lifecycle_stage='new'
When 用户完成 M2 诊断 + 生成方案（plan_status='active'）
Then user.lifecycle_stage 自动变更为 'maturing'
And 仍走新用户稿视觉节点 M1-M14
And 30 天观察期开始计时
```

### Scenario: maturing 用户完成 ≥5 天跃迁 matured（M3-FR-01 新增，PRD §0.x.7.3 修订）

```gherkin
Given 用户 lifecycle_stage='maturing'
And plan.current_day ≥ 7
When completed_days_d1_to_d7 ≥ 5（7 天内完成 5 天及以上）
Then user.lifecycle_stage 变更为 'matured'
And 跃迁到老用户稿视觉节点
And M10 Day 7 抱抱卡解锁（前提：current_day=7 且当天打卡完成）
```

### Scenario: maturing 用户不触发 Day 7 抱抱卡（M3-FR-01 新增）

```gherkin
Given 用户 lifecycle_stage='maturing'
And plan.current_day = 7
And 用户当天打卡已完成
When 用户进入首页
Then 抱抱卡**不**自动颁发
And 提示文案"稳定陪伴后会有小惊喜哦"（避免量化天数，符合合规红线 C-3）
```

### Scenario: matured 用户触发 Day 7 抱抱卡（M3-FR-01 新增，PRD §1.8）

```gherkin
Given 用户 lifecycle_stage='matured'
And plan.current_day = 7
When 用户完成 Day 7 打卡
Then 系统自动颁发 Day 7 抱抱卡
And 跳转至 v2-compliant 合规抱抱卡页
And 文案使用「和你走过的 7 天」（禁用"坚持 X 天"）
```

### Scenario: 方案完成后状态更新（M3→M5）

```gherkin
Given 用户完成方案生成
When 方案激活
Then plan_status 更新为 'active'
And 同步到 ai_sessions.plan_status
And M5 入口卡状态可感知到变化
```

### Scenario: 方案全部完成后引导抱抱卡（M3→M10）

```gherkin
Given 用户累计打卡满 7/14/21 天
And 当天打卡已完成
When 用户进入首页
Then 显示"分享你的坚持"入口
And 用户可点击生成抱抱卡
```

### Scenario: 方案完成后状态更新（M3→M5）

```gherkin
Given 用户完成21天打卡
When 方案打卡全部完成
Then plan_status 更新为 'completed'
And 方案过期时间设为 completed_at + 30 天
And M5 可感知到方案已完成
```

### Scenario: completed 状态 30 天后自动过期（M3→M5 新增）

```gherkin
Given 用户方案 plan_status='completed'
And 当前时间 > completed_at + 30 天
When 系统定时检查
Then plan_status 由 'completed' 变为 'expired'
And 用户进入 P03a 时 AI 提示"上次方案已结束，要不要开始新的21天？"
```

### Scenario: 未完成方案 30 天后自动过期（M3→M5 新增，取代原"超过30天未重新生成"表述）

```gherkin
Given 用户方案 plan_status='active'
And plans.started_at 已写入
And 当前日期 > started_at + 30 天
And 用户未完成 21 天打卡
When 系统定时检查
Then plan_status 由 'active' 变为 'expired'
And 用户进入 P03a 时 AI 提示"上次方案已结束，要不要开始新的21天？"
And 引导重新诊断或生成方案
```

---

## 五、错误处理

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

---

## 六、引用说明

### 相关定义

- 方案状态枚举：详见 [ATDD-Shared.md §一.3](../ATDD-Shared.md#一3方案状态)
- 用户生命周期状态：详见 [ATDD-Shared.md §一.1](../ATDD-Shared.md#一1用户生命周期状态)
- 错误码定义：详见 [ATDD-Shared.md §四](../ATDD-Shared.md#四错误码字典)
- 用户旅程：详见 [ATDD-Journey.md §三](../ATDD-Journey.md#三方案旅程)
- 合规红线：详见 [ATDD-Shared.md §三](../ATDD-Shared.md#三合规红线)
- ACK 话术池：详见 [ATDD-Shared.md §七](../ATDD-Shared.md#七ack-话术池规范)
- LLM 降级链：详见 [ATDD-Shared.md §五.1](../ATDD-Shared.md#51-llm-降级链)

### 新增错误码（V1.1）

- `E_PLAN_BUDGET_EXCEEDED` — LLM 月预算超 ¥700 熔断（PRD §4.1）

---

## 七、修订历史

| 日期 | 版本 | 改动 |
|------|------|------|
| 2026-07-22 | V1.1 | 架构评审补全：① 补 P03c 交付页路由 3 条 Scenario；② 补 started_at / current_day / streak_days 双轨 3 条 Scenario；③ 补 lifecycle_stage 联动 4 条 Scenario；④ 补 7 天缓存命中 + LLM 月预算熔断 2 条 Scenario；⑤ 状态机修正（不含 abandoned）；⑥ 删 3 阶段描述与 PRD/TDS/前端对齐 |
| 2026-07-21 | V1.0 | 初次创建，补充方案状态同步场景 |