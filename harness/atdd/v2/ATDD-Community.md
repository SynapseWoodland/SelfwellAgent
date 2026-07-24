# ATDD-Community: 广场社区

> **版本**: V1.0
> **状态**: Draft
> **对应模块**: M6
> **对应 TDS**: `docs/architecture/TDS/TDS-M6-plaza-community.md`
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`

---

## 一、动态发布

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
  And 用户已完成今日打卡
```

### Scenario: 用户成功发布动态（M6-FR-01）
```gherkin
Given 用户已完成今日打卡
And 用户进入广场页
When 用户点击"发布"
And 输入内容（≤ 200 字）
And 上传图片（≤ 9 张）
Then 动态进入待审核队列
And status='pending'
And 显示"发布成功，等待审核"
And estimated_wait_time='1-2 小时'
```

### Scenario: 内容包含敏感词被拦截（M6-FR-01）
```gherkin
Given 用户输入内容包含医疗词（治疗/治愈/处方）
Or 用户输入内容包含医美词（瘦脸/割双眼皮/玻尿酸）
Or 用户输入内容包含效果承诺（会变白/会变小/保证瘦）
Or 用户输入内容包含颜值打分（打分/评分/几分）
Or 用户输入内容包含容貌比较（比XX好看/更美）
When 用户点击发布
Then 显示"我们换个表达试试？"友好提示
And 动态不被发布
And 返回业务码 E_COMPLIANCE_CONTENT_BLOCKED
```

### Scenario: 字数超限被拦截（M6-FR-01）
```gherkin
Given 用户输入内容超过 200 字
When 用户点击发布
Then 显示字数超限提示
And 不允许提交
And 返回业务码 E_COMMUNITY_CONTENT_TOO_LONG
```

### Scenario: 图片超过 9 张被拦截（M6-FR-01）
```gherkin
Given 用户上传图片数组长度 > 9
When 用户点击发布
Then 显示"图片最多上传 9 张"提示
And 不允许提交
And 返回业务码 E_COMMUNITY_IMAGES_TOO_MANY
```

### Scenario: 每天只能发布 1 条（M6-FR-01）
```gherkin
Given 用户今日已发布动态（status≠rejected）
When 用户再次点击发布
Then 显示"今日已发布过"
And 不允许再次发布
And 返回业务码 E_COMMUNITY_DAILY_LIMIT_USER
```

---

## 二、审核流

### Background
```gherkin
Background:
  Given 用户动态已发布并进入待审核队列
```

### Scenario: 动态发布后 1-2 小时上墙（M6-FR-02）
```gherkin
Given 用户动态通过人工审核
When 运营人工确认通过
Then 动态在 1-2 小时内上墙
And 95 分位 ≤ 4 小时
And status='approved'
```

### Scenario: 通过动态获得 AI 暖评（M6-FR-02）
```gherkin
Given 动态已上墙（status='approved'）
When 系统处理上墙
Then 从 30 条 AI 暖评话术池选 1 条
And ai_comment 字段写入选中的话术
And AI 暖评显示在动态下方
```

### Scenario: 通过动态获得官方评论（M6-FR-02）
```gherkin
Given 动态已上墙（status='approved'）
When 系统处理上墙
Then 从 30 条官方评论话术池选 1 条
And official_comment 字段写入选中的话术
And 官方评论显示在动态下方
```

### Scenario: 每日发布超 10 篇自动关功能（M6-FR-01）
```gherkin
Given 平台每日发布动态 ≥ 10 篇
When 用户尝试发布
Then 发帖功能自动关闭
And 显示"发帖功能已临时关闭"
And 返回业务码 E_COMMUNITY_DAILY_LIMIT_EXCEEDED
And 需运营介入恢复
```

---

## 三、合规巡检

### Background
```gherkin
Background:
  Given 平台每日新增动态
```

### Scenario: 敏感词拦截率 ≥ 99%（M6-FR-02）
```gherkin
Given 平台每日新增动态
When AI 关键词拦截执行
Then 拦截率 ≥ 99%
And 剩余 1% 靠人工兜底
```

### Scenario: 0 次出现颜值打分帖子（M6-FR-02）
```gherkin
Given 每日巡检执行
When 检测到任何帖子包含颜值打分内容
Then 自动告警
And 帖子进入人工复核
And 违规记录写入 audit_log
```

### Scenario: 0 次出现医疗引导帖子（M6-FR-02）
```gherkin
Given 每日巡检执行
When 检测到任何帖子包含医疗/医美引导
Then 自动告警
And 帖子立即下架
And status 改为 'rejected'
```

### Scenario: 0 次出现容貌比较帖子（M6-FR-02）
```gherkin
Given 每日巡检执行
When 检测到任何帖子包含容貌比较内容
Then 自动告警
And 帖子进入人工复核
```

---

## 四、动态列表

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
```

### Scenario: 获取动态列表分页（M6-FR-03）
```gherkin
Given 用户请求 GET /api/v1/community/posts
When 系统处理请求
Then 返回 posts[] 含 id / user / content / images / ai_comment / official_comment / created_at
And 返回 pagination（limit / offset / total / has_next）
And 默认 limit=20，最大 50
```

### Scenario: 获取动态详情（M6-FR-03）
```gherkin
Given 用户请求 GET /api/v1/community/posts/{id}
When 系统处理请求
Then 返回动态详情
And 包含用户信息、图文内容、AI 暖评、官方评论
And status='approved' 时可见
```

### Scenario: 未登录用户查看动态（M6-FR-03）
```gherkin
Given 用户未登录（无 JWT）
When 用户尝试查看动态列表
Then 返回 HTTP 401
And 返回业务码 E_GENERAL_UNAUTHORIZED
```

---

## 五、分享功能

### Background
```gherkin
Background:
  Given 用户已获得抱抱卡（已完成 Day 7/14/21 打卡）
```

### Scenario: 分享卡分享至广场（M6-FR-04）
```gherkin
Given 用户持有抱抱卡
When 用户点击"分享到广场"
Then 抱抱卡进入发帖流程
And 合规文案校验通过
And 进入审核队列
```

### Scenario: 分享卡合规文案（M6-FR-04）
```gherkin
Given 用户尝试将抱抱卡分享至广场
When 系统校验分享内容
Then 内容不含"坚持/打卡/好棒/真的棒"等禁用词
And 内容不含效果承诺
And 通过后才可分享
```

---

## 六、活动中心

> 来源：原型 P09 广场页"活动"Tab

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
  And 用户已完成至少 1 天打卡
```

### Scenario: 查看活动列表（M6-FR-05）
```gherkin
Given 用户进入广场"活动"Tab
When 系统处理请求
Then 返回活动列表
And 包含：活动名称 / 参与人数 / 剩余天数 / 我的状态（参与中/未参与）
And 排序：进行中优先
And 已结束活动不展示
```

### Scenario: 参与活动（M6-FR-05）
```gherkin
Given 用户查看活动详情
When 点击"参与"按钮
Then 创建 user_activity 记录
And 活动卡片更新为"参与中"状态
And 返回业务码 E_COMMUNITY_ACTIVITY_JOINED
```

### Scenario: 活动展示我的参与天数（M6-FR-05）
```gherkin
Given 用户已参与活动
When 活动列表展示
Then 显示"Day N"标识（N = 用户参与天数）
And 参与天数从用户首次打卡算起
```

### Scenario: 21天挑战排名展示（M6-FR-05）
```gherkin
Given 用户参与 21 天挑战
When 用户进入活动详情
Then 显示当前排名（"第 N 名"）
And 显示已完成天数
And 显示还剩多少天
```

---

## 七、互动功能

> 来源：原型 P09 广场页卡片互动元素

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
  And 动态已上墙（status='approved'）
```

### Scenario: 查看动态卡片互动数据（M6-FR-06）
```gherkin
Given 动态已上墙
When 用户查看动态列表
Then 卡片显示：点赞数（♡N）
And 详情页显示：点赞数 + 评论数（♡N / 💬N）
```

### Scenario: 点赞功能（M6-FR-06）
```gherkin
Given 动态已上墙
And 用户未点赞该动态
When 用户点击 ♡
Then 点赞数 +1
And 记录 user_id + post_id 到 likes 表
And 返回业务码 E_COMMUNITY_LIKED
```

### Scenario: 取消点赞（M6-FR-06）
```gherkin
Given 用户已点赞该动态
When 用户再次点击 ♡
Then 点赞数 -1
And 删除 likes 表记录
And 返回业务码 E_COMMUNITY_UNLIKED
```

### Scenario: 查看评论列表（M6-FR-06）
```gherkin
Given 动态已上墙
When 用户点击动态卡片进入详情
Then 显示评论列表
And 包含：评论内容 / 用户昵称 / 发布时间
```

### Scenario: 发布评论（M6-FR-06）
```gherkin
Given 用户在动态详情页
When 输入评论（≤ 100 字）
And 点击发送
Then 评论进入待审核队列
And 评论数 +1
And 显示"评论待审核"
```

### Scenario: 评论包含敏感词被拦截（M6-FR-06）
```gherkin
Given 用户输入评论包含敏感词
When 用户点击发送
Then 显示"评论包含敏感词"
And 评论不被发布
And 返回业务码 E_COMPLIANCE_CONTENT_BLOCKED
```

### Scenario: 单用户每日评论上限（M6-FR-06）
```gherkin
Given 用户今日已评论 ≥ 5 条
When 用户尝试再次评论
Then 显示"今日评论次数已用完"
And 不允许发布
And 返回业务码 E_COMMUNITY_COMMENT_DAILY_LIMIT
```

---

## 八、发布流程 UI 交互

> 来源：原型 P09b 发帖页 + P09 广场"我的"Tab
> 前端原型：`docs/frontend-design/figma-pixso-spec/pages-v2/00-phone-prototype-v1.html` (节点 id: 15, 28, 29)

### Background
```gherkin
Background:
  Given 用户已完成今日打卡
  And 用户进入发布页面
```

### Scenario: 发布成功跳转"我的"Tab 并展示审核状态（M6-FR-01）
```gherkin
Given 用户点击发布
When 内容通过合规校验
Then 显示"发布成功，等待审核（预计 1-2 小时）"
And 跳转至广场"我的"Tab
And 显示该帖子 status='pending' + 审核中标识
And 不出现在"推荐"列表
```

### Scenario: 审核中帖子显示倒计时（M6-FR-01）
```gherkin
Given 帖子 status='pending'
When 用户在"我的"Tab 查看
Then 显示"审核中，预计剩余 X 小时"
And 超过 4 小时仍 pending 则显示"审核较慢，请稍候"
```

### Scenario: 审核通过通知用户（M6-FR-02）
```gherkin
Given 帖子通过审核变为 status='approved'
When 系统处理上墙
Then 发送站内通知给用户
And 通知内容"你的动态已上墙，获得 1 条暖心评论"
```

### Scenario: 审核拒绝通知用户（M6-FR-02）
```gherkin
Given 帖子被拒绝 status='rejected'
When 人工复核完成
Then 发送站内通知给用户
And 通知内容"抱歉，你的动态未通过审核，请换个方式表达"
And 显示拒绝原因（不含敏感词原文）
```

### Scenario: 帖子上墙后 AI 暖评展示（M6-FR-02）
```gherkin
Given 帖子 status='approved'
And 已写入 ai_comment
When 帖子展示在"推荐"列表
Then ai_comment 显示为虚线分隔的暖评气泡
And 样式：浅色背景 + 斜体字体
```

### Scenario: 新用户发帖入口引导（M6-FR-01）
```gherkin
Given 用户未完成诊断
When 用户进入广场页
Then 发帖按钮点击后显示引导"先完成诊断才能发帖"
And 跳转至诊断页面
```

---

## 九、引用说明

### 相关定义
- 合规红线：详见 [ATDD-Shared.md §三](../ATDD-Shared.md#三合规红线)
- ACK禁用词：详见 [ATDD-Shared.md §三.2](../ATDD-Shared.md#三合规红线)
- 错误码定义：详见 [ATDD-Shared.md §四](../ATDD-Shared.md#四错误码字典)

### 前端原型引用
- 广场页：原型 P09（节点 id: 15）
- 发帖页：原型 P09b（节点 id: 28）
- 新用户广场：原型 P09a（节点 id: 29）

---

## 十、修订历史

| 日期 | 版本 | 改动 |
|------|------|------|
| 2026-07-21 | V1.1 | 新增 §六活动中心 / §七互动功能 / §八发布流程UI交互 |
| 2026-07-21 | V1.0 | 初次创建 |
