# TDS-M6: 广场社区 - 验收标准

> **版本**: V1.0
> **状态**: Draft
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`

---

## Feature: 动态发布

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

## Feature: 审核流

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

## Feature: 合规巡检

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

## Feature: 动态列表

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

## Feature: 分享功能

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
