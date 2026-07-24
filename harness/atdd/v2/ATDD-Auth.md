# ATDD-Auth: 认证与用户管理

> **版本**: V1.1
> **状态**: Draft
> **对应模块**: M1
> **对应 TDS**: `docs/architecture/TDS/TDS-M1-wechat-login.md`
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`
> **最后更新**: 2026-07-21（V1.1 补充隐私协议、年龄闸门、unionid冲突、手机号登录场景）

---

## 零、隐私协议前置

### Background
```gherkin
Background:
  Given 用户首次启动 Selfwell 小程序/App
  And 用户尚未同意隐私协议
```

### Scenario: 隐私协议强制前置，新用户必须同意（M1-FR-04）
```gherkin
Given 用户首次启动 Selfwell
When 系统展示隐私协议弹窗
Then 用户必须点击"同意并继续"才能继续流程
And 不同意则退出小程序/App
```

### Scenario: 隐私协议版本更新后重新弹窗（M1-FR-04）
```gherkin
Given 用户已同意旧版隐私协议 v1.0
When 隐私协议升级到 v1.1
Then 首次启动时重新弹出 v1.1 版本要求确认
And 用户需重新点击"同意"才能继续
```

---

## 一、微信 OAuth 登录

### Background
```gherkin
Background:
  Given 用户已打开 Selfwell 小程序
  And 用户未登录（无有效 JWT）
  And 用户已同意隐私协议
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
And 返回 JWT token（有效期 7 天）
```

### Scenario: 小程序 unionid 打通跨端复用（M1-FR-03, AC-M1-02）
```gherkin
Given 用户已在 APP 端注册，unionid='U_001'，openid_app='A_001'
When 用户在小程序端登录，jscode2session 返回 openid_mp='M_001'
And 后端解密 encryptedData 拿到 unionid='U_001'
Then 后端不创建新用户，关联到现有 user_id
And openid_mp 被写入 user 表
And 返回该用户的当前 user_status
And 返回 JWT token（有效期 7 天）
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

### Scenario: unionid 冲突时提示用户联系客服（M1-FR-03）
```gherkin
Given 小程序用户 A 有独立账户（无 unionid），openid_mp='A_MP'
And APP 端用户 B 有独立账户（无 unionid），openid_app='B_APP'
When 用户 B 首次登录小程序并获取到 unionid='U_001'
And 该 unionid 关联到用户 A 的小程序账户
Then 检测到 unionid 冲突
And 返回 HTTP 409
And 返回业务码 E_AUTH_UNIONID_CONFLICT
And 提示"检测到账号冲突，请联系客服合并"
```

---

## 二、年龄闸门

### Scenario: 未满 18 岁用户被阻断注册（M1-FR-04）
```gherkin
Given 用户尝试登录
When 后端校验用户年龄 < 18 岁
Then 返回 HTTP 403
And 返回业务码 E_USER_AGE_BELOW_MINIMUM
And 提示"抱歉，Selfwell 仅对 18 岁以上用户开放"
```

### Scenario: 年龄闸门校验时机（M1-FR-04）
```gherkin
Given 用户调用 POST /api/v1/auth/wx-login
When 用户出生日期或 age_range 计算结果 < 18 岁
Then 后端返回年龄校验失败
And 前端引导用户输入正确出生年月
```

---

## 三、推送 Token 注册

### Scenario: 首次登录默认推送渠道（M1-FR-05）
```gherkin
Given 新用户完成登录（status='draft'）
When user 表创建完成
Then push_channel 默认值：微信小程序 → 'wx_subscribe'，iOS → 'apns'，Android → 'fcm'，HarmonyOS → 'hms'
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

## 四、错误处理

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

## 五、手机号登录回退（APP 端）

### Scenario: APP 端微信登录失败后自动切换手机号（M1-FR-02）
```gherkin
Given 用户在 APP 端微信登录失败（errcode ≠ 0）
When 系统自动切换手机号 OTP 登录流程
Then 用户收到短信验证码
When 用户输入正确验证码
Then 后端创建/关联用户并返回 JWT（有效期 7 天）
And 返回 is_new_user=true/false
```

### Scenario: 手机号已被占用（M1-FR-02）
```gherkin
Given 用户使用手机号登录
When 该手机号已在系统注册
Then 返回 HTTP 409
And 返回业务码 E_AUTH_PHONE_ALREADY_REGISTERED
And 提示"该手机号已注册，请直接登录"
```

### Scenario: 手机号验证码错误（M1-FR-02）
```gherkin
Given 用户输入手机号验证码
When 验证码错误或已过期
Then 返回 HTTP 401
And 返回业务码 E_AUTH_CODE_INVALID
And 提示"验证码错误或已过期，请重新获取"
```

### Scenario: 手机号登录 rate limit（M1-FR-02）
```gherkin
Given 同一手机号在 60 秒内发起 ≥ 5 次验证码请求
When 发起第 6 次请求
Then 返回 HTTP 429
And 返回业务码 E_GENERAL_RATE_LIMIT
And 提示"操作过于频繁，请稍后再试"
```

---

## 六、合规约束

### Scenario: 不收集额外敏感字段（M1-FR-04）
```gherkin
Given 用户完成微信登录
When 系统记录用户信息
Then 仅收集：nickname、avatar、age_range、focus_parts、intensity、preferred_time、sitting_hours
And 不收集身份证、地址等其他敏感信息
And 收集 email/phone 必须有单独"我同意"勾选
```

### Scenario: JWT 有效期 7 天（M1-FR-01）
```gherkin
Given 用户登录成功
When 后端返回 JWT token
Then JWT 有效期为 7 天（604800 秒）
And 前端通过 wx.checkSession() 检查登录态
And token 过期后静默刷新
```

### Scenario: 久坐时长枚举值规范（M1-FR-04）
```gherkin
Given 用户设置久坐时长
When 用户选择久坐档位
Then 枚举值使用英文代码：'lt4h'（<4小时）、'4to8h'（4-8小时）、'8to12h'（8-12小时）、'gt12h'（>12小时）
And 前端显示中文文案，API 传输英文代码
```

---

## 七、引用说明

### 相关定义
- 用户状态枚举：详见 [ATDD-Shared.md §一.1](../ATDD-Shared.md#一用户状态枚举)
- 错误码定义：详见 [ATDD-Shared.md §四](../ATDD-Shared.md#四错误码字典)
- 合规红线：详见 [ATDD-Shared.md §三](../ATDD-Shared.md#三合规红线)
- 枚举值规范：详见 [ATDD-Shared.md §五](../ATDD-Shared.md#五枚举值规范)

### 字段枚举值对照表

| 字段 | ATDD 场景用值 | 数据库/API 值 | 前端显示 |
|------|-------------|--------------|---------|
| `sitting_hours` | `lt4h` / `4to8h` / `8to12h` / `gt12h` | 同左 | 4小时以下 / 4-8小时 / 8-12小时 / 12小时以上 |
| `age_range` | `18-22` / `23-28` / `29-35` / `36-45` / `45+` | 同左 | 同左 |
| `intensity` | `轻柔` / `适中` / `进阶` | 同左 | 同左 |
| `preferred_time` | `早` / `中` / `晚` / `不固定` | 同左 | 同左 |
| `status` | `draft` / `active` / `churned` | 同左 | 草稿 / 正式 / 流失 |

---

## 八、修订历史

| 日期 | 版本 | 改动 |
|------|------|------|
| 2026-07-21 | V1.1 | 补充隐私协议前置场景（§零）；补充年龄闸门校验（§二）；补充 unionid 冲突处理（§一）；补充手机号登录回退（§五）；明确 JWT 有效期 7 天（§六）；补充久坐时长枚举值规范（§六） |
| 2026-07-21 | V1.0 | 初次创建 |
