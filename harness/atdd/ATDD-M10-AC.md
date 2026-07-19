# TDS-M10: 分享卡 - 验收标准

> **版本**: V1.0
> **状态**: Draft
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`

---

## Feature: 抱抱卡生成

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
  And 用户累计打卡满 7/14/21 天
```

### Scenario: 第 7 天自动出现抱抱卡入口（M10-FR-01）
```gherkin
Given 用户累计打卡 7 天
And 当天打卡已完成
When 用户进入首页
Then 首页显示"分享你的坚持"入口
And 用户可点击生成抱抱卡
```

### Scenario: 第 14 天自动出现抱抱卡入口（M10-FR-01）
```gherkin
Given 用户累计打卡 14 天
And 当天打卡已完成
When 用户进入首页
Then 首页显示"分享你的坚持"入口
And 用户可点击生成抱抱卡
```

### Scenario: 第 21 天方案完成抱抱卡（M10-FR-01）
```gherkin
Given 用户累计打卡 21 天
And 当天打卡已完成
When 用户进入首页
Then 首页显示"方案完成"抱抱卡入口
And 用户可点击生成抱抱卡
```

### Scenario: 海报生成耗时 ≤ 3 秒（M10-FR-02）
```gherkin
Given 用户点击生成抱抱卡
When 系统处理海报生成
Then 响应时间 P95 ≤ 3 秒
And 返回海报 URL
```

### Scenario: 海报包含必要元素（M10-FR-02）
```gherkin
Given 抱抱卡已生成
When 用户查看海报
Then 海报包含累计天数（"和你走过的 {n} 天" / "和你一起 · 第 {n} 天"）
And 海报包含鼓励话术（来自 ACK_POOL 30 条池）
And 海报包含小程序码/APP 二维码
And 海报包含 Selfwell 品牌标识
```

---

## Feature: 合规约束

### Background
```gherkin
Background:
  Given 任意天数的抱抱卡已生成
```

### Scenario: 海报文案不含数字评判禁用词（M10-FR-03）
```gherkin
Given 抱抱卡已生成
When 系统校验文案
Then 不含：坚持 / 进步 / 改善 / 变好 / 真的棒 / 打卡 / 好棒 / 分数 / 排名 / 颜值 / 好看
And 天数仅以"和你走过的 {n} 天" 形式呈现
And 不出现"已坚持 {n} 天"
And 字面命中 CI 拦截，红牌拒绝
```

### Scenario: 海报不含效果承诺（M10-FR-03）
```gherkin
Given 抱抱卡已生成
When 系统校验文案
Then 不包含任何效果承诺（会变白/会瘦/会提升/保证）
And 不包含医疗/医美词汇
And 不包含颜值打分
```

### Scenario: 海报模板预置合规（M10-FR-03）
```gherkin
Given 抱抱卡生成
When 系统选择模板
Then 使用预置合规模板（hug_card_7.png / hug_card_14.png / hug_card_21.png）
And 模板不包含任何禁用词
And 合规团队人工审核通过
```

### Scenario: 海报 URL 有效期 7 天（M10-FR-02）
```gherkin
Given 抱抱卡已生成
When 系统返回 URL
Then expires_at = created_at + 7 天
And 过期后需重新生成
```

---

## Feature: 分享功能

### Background
```gherkin
Background:
  Given 用户已生成抱抱卡
  And 用户持有海报 URL
```

### Scenario: 小程序端可分享至朋友圈（M10-FR-04）
```gherkin
Given 用户在小程序端
And 用户持有海报
When 用户点击分享按钮
Then 可通过 onShareAppMessage 分享至朋友圈
And title='我愿意慢慢来'
And path='/pages/index/index'
```

### Scenario: 小程序端可转发表情包（M10-FR-04）
```gherkin
Given 用户在小程序端
When 用户点击"转发表情包"
Then 可通过 shareElement 转为表情包分享
And 表情包含 Selfwell 品牌水印
```

### Scenario: APP 端可分享至微信好友（M10-FR-04）
```gherkin
Given 用户在 APP 端
When 用户点击分享按钮
Then 可通过 share_plus 分享至微信好友
And 分享文本包含 hashtag #Selfwell
```

### Scenario: APP 端可分享至朋友圈（M10-FR-04）
```gherkin
Given 用户在 APP 端
When 用户长按海报
Then 可识别二维码分享至朋友圈
And 二维码为小程序码/APP 下载码
```

### Scenario: APP 端分享文本合规（M10-FR-04）
```gherkin
Given 用户在 APP 端分享
When 系统组装分享文本
Then 文本不含禁用词（坚持/好棒/打卡/效果）
And 文本不含数字评判
And 文本仅含"和你走过的 {n} 天"形式
```

---

## Feature: 资格检查

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
```

### Scenario: 检查用户是否有资格获取抱抱卡（M10-FR-01）
```gherkin
Given 用户请求 GET /api/v1/share/poster/eligible
When 系统校验资格
Then 返回 eligible=true/false
And 返回 next_trigger_days
And 返回 current_days
And 返回 days_until_trigger
```

### Scenario: 未达标用户不能生成抱抱卡（M10-FR-01）
```gherkin
Given 用户累计打卡 5 天（未达 7/14/21）
When 用户尝试 POST /api/v1/share/poster
Then 返回业务码 E_SHARE_ELIGIBLE_NOT_MET
And 提示"还差 {n} 天解锁抱抱卡"
```

### Scenario: plan 不属于当前用户被拒绝（M10-FR-02）
```gherkin
Given 用户传入 plan_id 不属于当前用户
When 用户尝试生成抱抱卡
Then 返回业务码 E_SHARE_PLAN_NOT_FOUND
And 不生成海报
```

---

## Feature: 错误处理

### Scenario: 海报渲染失败（M10-FR-02）
```gherkin
Given 海报渲染过程发生错误（字体下载失败 / 图片解码失败）
When 用户请求生成抱抱卡
Then 返回业务码 E_SHARE_RENDER_FAILED
And 提示"海报生成失败，请稍后再试"
And 记录错误日志
```

### Scenario: template 不在 3 种枚举内（M10-FR-02）
```gherkin
Given 用户传入 template='invalid'
When 用户尝试生成抱抱卡
Then 返回业务码 E_SHARE_TEMPLATE_INVALID
And 提示可选模板：hug_card / progress / achievement
```

### Scenario: 抱抱卡生成防重（M10-FR-02）
```gherkin
Given 用户已生成当天抱抱卡
When 用户再次请求生成
Then 返回已有抱抱卡 URL
And 不重复生成
And expires_at 不变
```
