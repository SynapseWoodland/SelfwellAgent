# ATDD-Journey: 用户旅程覆盖

> **版本**: V1.0
> **状态**: Draft
> **用途**: 覆盖跨模块用户旅程，补充单模块ATDD缺失的场景
> **依赖 TDS**: `docs/architecture/TDS/TDS-M5-persona-chat.md`（用户旅程中 M5 对话状态）

---

## 一、冷启动旅程（M1 + M5）

### Feature: 新用户冷启动

### Background
```gherkin
Background:
  Given 用户首次打开小程序
  And 用户未登录（无有效JWT）
```

### Scenario: 新用户首次登录走draft路径
```gherkin
Given 用户未注册（openid_mp / unionid 均不在 user 表）
When 小程序调用 POST /api/v1/auth/wx-login 传入 code
Then 后端调用 jscode2session 获取 openid_mp
And 后端创建新用户，status='draft'
And user 表新增 1 条记录
And 返回 is_new_user=true
And 返回 user_status='draft'
And 返回 JWT token
```

### Scenario: 草稿用户进入P03a看到引导
```gherkin
Given 用户 status='draft'
When 用户进入 P03a 智能管家
Then 入口卡 🔍 智能分析：副文案 "上传 3 张照片，生成你的养护参考"
And 入口卡 📖 心情日记：副文案 "想记录今天的感受吗？"
And 入口卡 💬 问过去的自己：副文案 "好奇几个月的你吗？"
And AI 基线问候 "欢迎来到 Selfwell，有什么想聊的吗？"
```

### Scenario: 草稿用户完善档案后立即转正
```gherkin
Given 草稿用户持有有效 JWT
When 用户 POST /api/v1/users/profile 传入 5 个必填字段
Then user_status 立即转为 'active'
And 跳过 24h 等待期
And 返回 user_status='active'
And 入口卡状态刷新
```

---

## 二、诊断旅程（M2 + M5）

### Feature: 完整诊断旅程

### Background
```gherkin
Background:
  Given 用户已登录（status='active'）
  And 用户档案完整（5个必填字段已填写）
  And 用户未在7天内完成过智能分析
```

### Scenario: 用户从P03a引导进入诊断（M5→M2）
```gherkin
Given 用户在 P03a
When 用户输入"我想分析肩颈"
Then SmartRouter 分类为 guide
And ModuleDispatcher 派发到 M2 智能分析
And AI 回复引导用户上传照片
And primary_intent='guide'
```

### Scenario: 用户通过入口卡进入诊断
```gherkin
Given 用户在 P03a
When 用户点击 🔍 智能分析入口卡
Then 跳转到诊断上传页
And 入口卡副文案变为 "补档案，完成分析" + ⭐薄荷绿描边
```

### Scenario: 诊断完成后入口卡状态更新（M2→M5）
```gherkin
Given 用户完成智能分析（报告生成成功）
And 用户进入 P03a
When 诊断状态已同步
Then 🔍 智能分析：副文案 "查看报告 →" + ⭐薄荷绿描边
And 方案生成入口出现
And AI 回复 "报告已生成，要看看吗？"
```

### Scenario: 诊断完成后引导生成方案（M2→M3）
```gherkin
Given 用户完成诊断，获得报告
When 用户点击 "生成 21 天方案"
Then 跳转到方案生成流程
And 使用诊断报告的 distinct 部位
And 方案与诊断关联
```

---

## 三、方案旅程（M3 + M4 + M5）

### Feature: 完整方案旅程

### Background
```gherkin
Background:
  Given 用户已完成智能分析，获得 distinct 部位数 N
  And 用户持有有效 JWT
```

### Scenario: 生成21天方案
```gherkin
Given 用户已完成 M2 distinct，得到 N 个部位（N ∈ {1, 2, 3}）
When 用户点击"生成 21 天方案"
Then 系统生成 N 个视频（每个部位对应 1 个视频）
And 每天任务 = N 个视频（循环播放）
And 21 天内每天任务相同
And plan_status='queued'
```

### Scenario: 方案激活后首页展示
```gherkin
Given 用户完成方案生成
When 用户点击"开始 21 天"
Then 跳转至首页（P02）
And 首页今日任务卡片显示第 1 天视频
And 进度环显示 day=1/21
And plan_status='active'
```

### Scenario: 每日打卡流程
```gherkin
Given 用户已激活 21 天方案
And 用户已完成今日视频跟练
When 用户点击"已完成打卡"
Then 打卡成功
And 用户碎片 +1（不设递增系数）
And 用户连续天数 +1
And 显示打卡成功话术（禁用"真的棒"）
```

### Scenario: 打卡后方案入口卡状态（M4→M5）
```gherkin
Given 用户完成今日打卡
When 用户进入 P03a
Then 入口卡 💬 问过去的自己：副文案可能更新
And AI 可引用今日打卡状态
```

### Scenario: 方案完成后引导分享（M4→M10）
```gherkin
Given 用户累计打卡满 7/14/21 天
And 当天打卡已完成
When 用户进入首页
Then 显示"分享你的坚持"入口
And 用户可点击生成抱抱卡
```

---

## 四、反馈旅程（M7 + M5 + M8）

### Feature: 完整反馈旅程

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
  And 用户已完成至少1次feedback
```

### Scenario: 用户提交心情日记（M7→M5）
```gherkin
Given 用户在 P03a 点 📖 心情日记入口卡
When 用户在 P08a 输入 "今天感觉不错"
And 用户点 [保存]
Then 系统写入 feedback（type=mood_text, text_content="今天感觉不错"）
And AI 回复 ≤ 30 字温柔确认（来自 ACK_POOL）
And feedback.ai_ack_id 关联 ai_messages.id
And 7天未feedback判定重置
```

### Scenario: 用户通过soft-tip补一组照片（M8→M7）
```gherkin
Given 用户进入 M8 回忆，发现无照片
When 用户点 [补一组]
Then 跳转 P08a 编辑器（提示"这是一段以前的回忆"）
And 写入 feedback.type=period_photo
And photo_url / body_part 必填
And feedback.ai_ack_id 关联
```

### Scenario: 7天未feedback触发Persona切换（M7→M5）
```gherkin
Given 用户连续 7 天未上传 feedback
When 用户进入 P03a
Then AI persona_state 切换为 'slight_hug'
And AI 基线问候为 "感觉你最近没怎么分享，我随时都在。"
And AI 回复触发 soft-tip 引导
```

---

## 五、回忆旅程（M8 + M5 + M7）

### Feature: 完整回忆旅程

### Background
```gherkin
Background:
  Given 用户已完成方案
  And 用户已完成 Day 7/14/21 打卡
```

### Scenario: Day 7 主动推送回忆气泡（M8→M5）
```gherkin
Given 用户注册已满 7 天
And 用户连续打卡满 7 天
When Celery Beat 扫表触发 auto_day7
Then 服务通知推送 + P03a 主页出现回忆气泡
And 气泡文案 "我们已经一起走了 7 天。要不要看看 7 天前的自己？"
And 入口卡 💬 问过去的自己：副文案更新为 "查看对话 →"
```

### Scenario: 用户点回忆入口进入M8
```gherkin
Given 用户在 P03a 点 💬 问过去的自己入口卡
When 用户点击
Then 系统触发 user_query
And AI 回复 ≤ 5 秒（P95 召回纯文字）
And 展示历史缩略图
```

### Scenario: 回忆场景无数据时展示soft-tip（M8→M7）
```gherkin
Given 用户从未上传过 feedback
When 用户点 💬 入口卡
Then AI 展示 soft-tip 气泡
And 3 按钮均可点击：
  - [补一组] → 跳转 P08a 提交 period_photo
  - [就这样聊] → 留在 P03a 对话
  - [取消] → 回到 P03a 主页
```

### Scenario: 回忆内容不含评判性语句（M8合规）
```gherkin
Given 用户收到回忆内容
When 系统校验内容
Then 不含 "比之前好/差"
And 不含 "进步了/改善了/变好了"
And 不含 "颜值/好看/瘦"
And 不含 "你坚持了 X 天真棒"
```

---

## 六、方案结束后旅程（M3 + M4 + M5）

### Feature: 21天方案结束后的用户旅程

### Background
```gherkin
Background:
  Given 用户已完成 21 天方案（全部打卡完成）
  And plan_status='completed'
```

### Scenario: 方案结束后P03a入口卡状态（M3→M5）
```gherkin
Given 用户已完成21天方案
When 用户进入 P03a
Then 🔍 智能分析：副文案 "再次分析？"
And 💬 问过去的自己：副文案 "查看对话 →" + ⭐薄荷绿描边
And AI 基线问候可引用已完成方案
```

### Scenario: 方案结束后用户询问接下来怎么办
```gherkin
Given 用户已完成21天方案
When 用户输入"21 天之后怎么办"
Then AI 温柔回应"你已经坚持了 21 天！之后可以继续每天打卡，保持这个好习惯"
And 不承诺具体效果
And 鼓励持续参与
And 引导查看里程碑或分享
```

### Scenario: 方案结束后引导新方案（M3→M5）
```gherkin
Given 用户已完成21天方案
And 方案已过期（超过30天未重新生成）
When 用户进入 P03a
Then AI 提示"上次方案已结束，要不要开始新的21天？"
And 引导重新诊断或生成方案
```

---

## 七、诊断过期旅程（M2 + M3 + M5）

### Feature: 诊断过期后的用户旅程

### Background
```gherkin
Background:
  Given 用户上一次诊断已超过 30 天
  And 用户有进行中的方案（基于旧诊断生成）
```

### Scenario: 诊断过期后用户询问报告（M5→M2）
```gherkin
Given 用户上一次诊断已超过 30 天
When 用户询问诊断结果
Then AI 提示"上次分析已经是 30 天前了，要不要重新分析一下？"
And 引导用户重新上传照片进行诊断
```

### Scenario: 诊断过期后方案关联提示（M5→M3）
```gherkin
Given 用户有方案（基于30天前诊断）
When 用户询问方案
Then AI 可提示"这是基于较早的分析生成的方案，如有需要可以重新分析获得更准确的建议"
And 不强制要求重新诊断
```

---

## 八、错误恢复旅程

### Feature: 各类错误后的恢复路径

### Background
```gherkin
Background:
  Given 用户在使用过程中遇到各类错误
```

### Scenario: LLM失败后的恢复
```gherkin
Given LLM 服务不可用
When 用户发起智能分析
Then 系统切换到 BACKUP_MULTI_MODEL（轻量多模态）
And 记录降级日志（llm_error=true, tier=1）
And 报告标记 fallback=true
```

### Scenario: 连续LLM失败锁定后解锁
```gherkin
Given 智能分析功能因连续2次LLM失败被锁定
When 锁定时间超过30分钟
Then 系统自动解锁
And 自动重试1次
And 重试成功则恢复正常，重试失败则保持锁定
```

### Scenario: 推送失败但打卡仍成功
```gherkin
Given 4 端推送 + 邮件兜底全失败
When 用户打卡
Then 打卡记录仍成功写入
And push_records 标记失败
And 不阻塞打卡流程
```

---

## 九、跨日/跨时区旅程

### Feature: 跨日边界处理

### Background
```gherkin
Background:
  Given 北京时间跨日边界（23:59:59 → 00:00:00）
```

### Scenario: 23:59 CST 打卡计入当天
```gherkin
Given 用户在 CST 23:59:59 打卡
When 系统记录打卡
Then 打卡计入当天
And 进度环更新
And 不触发次日打卡流程
```

### Scenario: 00:00 CST 打卡计入新一天
```gherkin
Given 用户在 CST 00:00:00 打卡
When 系统记录打卡
Then 打卡计入次日
And 进度环更新
And 打卡天数 +1
```

### Scenario: 时区切换不影响业务日期
```gherkin
Given 用户设备时区 = Asia/Tokyo (UTC+9)
When 用户查看打卡日历
Then 显示北京时间（UTC+8）
And 不使用设备本地时区
And 业务日期与北京时间一致
```

---

## 十、修订历史

| 日期 | 版本 | 改动 | 来源 |
|------|------|------|------|
| 2026-07-21 | V1.0 | 初次创建，覆盖跨模块用户旅程 | ATDD整合分析 |
