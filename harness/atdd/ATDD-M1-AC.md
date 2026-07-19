# TDS-M1: 微信登录 - 验收标准

> **版本**: V1.0
> **状态**: Draft
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`

---

## Feature: 微信 OAuth 登录

### Background
```gherkin
Background:
  Given 用户已打开 Selfwell 小程序
  And 用户未登录（无有效 JWT）
```

### Scenario: 新用户首次登录走 draft 路径（M1-FR-01, AC-M1-01）
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

### Scenario: 小程序 unionid 打通跨端复用（M1-FR-03, AC-M1-02）
```gherkin
Given 用户已在 APP 端注册，unionid='U_001'，openid_app='A_001'
When 用户在小程序端登录，jscode2session 返回 openid_mp='M_001'
And 后端解密 encryptedData 拿到 unionid='U_001'
Then 后端不创建新用户，关联到现有 user_id
And openid_mp 被写入 user 表
And 返回该用户的当前 user_status
And 返回 JWT token
And 返回 is_new_user=false
```

### Scenario: 草稿用户 24 小时后自动转正（M1-FR-06, AC-M1-03）
```gherkin
Given 用户在 24h 前注册，status='draft'，last_active_at 在 24h 内被更新
When cron job 执行（每日 00:05 UTC）
Then 该用户 status 转为 'active'
And 记录状态变更日志
```

### Scenario: 首登档案补全后立即转正（M1-FR-04, AC-M1-04）
```gherkin
Given 草稿用户持有有效 JWT
When 用户 POST /api/v1/users/profile 传入 5 个必填字段
  | age_range  | focus_parts          | intensity | preferred_time | sitting_hours |
  | 23-28      | [face, shoulder_neck] | 适中      | 晚             | 4-8h         |
Then user_status 立即转为 'active'
And 跳过 24h 等待期
And 返回 user_status='active'
```

### Scenario: unionid 不打通时独立账号（M1-FR-03, AC-M1-05）
```gherkin
Given 小程序用户 A 未授权 unionid，openid_mp='A_MP'
And APP 端用户 B 也未授权 unionid，openid_app='B_APP'
When A 和 B 分别登录
Then A 和 B 在 user 表里各占 1 行
And 后续登录互不影响
```

### Scenario: 跨端登录更新末次 platform（M1-FR-03）
```gherkin
Given 用户首次在小程序端登录，platform='wx_mp'
When 用户切换至 APP 端登录，client='ios'
Then 该用户的 platform 更新为 'ios'
And openid_app 被写入 user 表
```

---

## Feature: 推送 Token 注册

### Scenario: 首次登录默认推送渠道（M1-FR-05）
```gherkin
Given 新用户完成登录（status='draft'）
When user 表创建完成
Then push_channel 默认值：微信小程序 → 'wx_subscribe'，iOS → 'apns'，Android → 'fcm'
And email 渠道默认开启
```

### Scenario: 推送 Token 注册（M1-FR-05）
```gherkin
Given 已登录用户持有有效 JWT
When 用户 POST /api/v1/users/push-token 传入 push_token 和 push_channel
Then push_token 被写入 user 表
And 返回 code=0
```

---

## Feature: 错误处理

### Scenario: 无效 code 返回认证失败（M1-FR-01）
```gherkin
Given 用户调用 POST /api/v1/auth/wx-login
When 传入的 code 已失效或非法
Then 返回 HTTP 401
And 返回业务码 E_AUTH_CODE_INVALID
And 提示"登录失败，请重试"
```

### Scenario: rate limit 限流（M1-FR-01）
```gherkin
Given 同一 IP 在 60 秒内发起 ≥ 10 次登录请求
When 发起第 11 次登录请求
Then 返回 HTTP 429
And 返回业务码 E_GENERAL_RATE_LIMIT
And 提示"操作过于频繁，请稍后再试"
```

---

## Feature: 合规约束

### Scenario: 不收集额外敏感字段（M1-FR-04）
```gherkin
Given 用户完成微信登录
When 系统记录用户信息
Then 仅收集：nickname、avatar、age_range、focus_parts、intensity、preferred_time、sitting_hours
And 不收集身份证、地址等其他敏感信息
And 收集 email/phone 必须有单独"我同意"勾选
```
