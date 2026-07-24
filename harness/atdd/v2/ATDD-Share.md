# ATDD-Share: 分享卡

> **版本**: V1.1
> **状态**: Draft
> **对应模块**: M10
> **对应 TDS**: `docs/architecture/TDS/TDS-M10-share-card.md`
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`

---

## 一、抱抱卡生成

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
  And 用户 streak_days 达到 7/14/21
```

### Scenario: 第 7 天自动出现抱抱卡入口（M10-FR-01）
```gherkin
Given 用户 streak_days 达到 7
And 当天打卡已完成
When 打卡完成
Then 系统显示抱抱卡入口弹窗
And 用户可点击生成抱抱卡
```

### Scenario: 第 14 天自动出现抱抱卡入口（M10-FR-01）
```gherkin
Given 用户 streak_days 达到 14
And 当天打卡已完成
When 打卡完成
Then 系统显示抱抱卡入口弹窗
And 用户可点击生成抱抱卡
```

### Scenario: 第 21 天方案完成抱抱卡（M10-FR-01）
```gherkin
Given 用户 streak_days 达到 21
And 当天打卡已完成
When 打卡完成
Then 系统显示抱抱卡入口弹窗
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
And 海报包含鼓励话术（来自 ACK 池 30 条）
And 海报包含小程序码/APP 二维码
And 海报包含 Selfwell 品牌标识
```

---

## 二、合规约束

### Background
```gherkin
Background:
  Given 任意天数的抱抱卡已生成
```

### Scenario: 海报文案不含数字评判禁用词（M10-FR-03）
```gherkin
Given 抱抱卡已生成
When 系统校验文案
Then 不含禁用词（详见 docs/data/recall-forbidden-words.yaml numeric_judge 分组）
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

### Scenario: 海报 URL 有效期 7 天（CDN 缓存）（M10-FR-02）
```gherkin
Given 抱抱卡已生成
When 系统返回 URL
Then CDN 缓存有效期 = 7 天
And 用户可随时重新生成新海报
And expires_at 字段仅供参考
```

---

## 三、分享功能

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
And APP 端不支持此功能
```

### Scenario: APP 端可分享至微信好友（M10-FR-04）
```gherkin
Given 用户在 APP 端
When 用户点击分享按钮
Then 可通过 share_plus 分享至微信好友
And 分享文本不包含天数数字
And 分享文本不包含禁用词
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

## 四、资格检查

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
And 提示"再走 {n} 天就有惊喜"
```

### Scenario: plan 不属于当前用户被拒绝（M10-FR-02）
```gherkin
Given 用户传入 plan_id 不属于当前用户
When 用户尝试生成抱抱卡
Then 返回业务码 E_SHARE_PLAN_NOT_FOUND
And 不生成海报
```

---

## 五、错误处理

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

---

## 六、引用说明

### 相关定义
- 合规红线：详见 [ATDD-Shared.md §三](../ATDD-Shared.md#三合规红线)
- ACK禁用词：详见 [ATDD-Shared.md §三.2](../ATDD-Shared.md#三合规红线)
- 错误码定义：详见 [ATDD-Shared.md §四](../ATDD-Shared.md#四错误码字典)

---

## 七、修订历史

| 日期 | 版本 | 改动 |
|------|------|------|
| 2026-07-21 | V1.0 | 初次创建 |
| 2026-07-24 | V1.1 | 1. 触发条件改为 streak_days（实际打卡天数）<br>2. 入口触发时机改为打卡完成后立即显示弹窗<br>3. 禁用词引用外部词表 recall-forbidden-words.yaml<br>4. URL 有效期区分 CDN 缓存 vs 业务永久有效<br>5. 分享入口文案移除"坚持"禁用词<br>6. 未达标提示文案改为"再走 {n} 天就有惊喜"<br>7. ACK 命名统一为"ACK 池"<br>8. 表情包分享明确为小程序端专属 |
