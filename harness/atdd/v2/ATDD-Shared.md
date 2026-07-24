# ATDD-Shared: 跨域共享定义（唯一真源）

> **版本**: V1.4
> **状态**: Draft
> **用途**: 所有 ATDD 模块文档必须引用本文件，删除重复定义
> **依赖 TDS**: `docs/architecture/TDS/TDS-M5-persona-chat.md`（Persona 状态机）

---

## 一、用户状态枚举（唯一真源）

### 1.1 用户生命周期状态

| 状态 | 定义 | 触发条件 | 影响 |
|------|------|---------|------|
| `draft` | 草稿用户 | 首次登录未完善档案 | 只能完善档案，无法使用核心功能 |
| `active` | 激活用户 | 完善档案/24h后自动转正 | 全部功能可用 |
| `inactive` | 沉默用户 | 30天未登录 | 部分功能限制 |
| `deactivated` | 注销用户 | 用户主动注销+15天冷静期 | 全部功能关闭 |

**真源自**：
- M1: 登录 → draft/active 状态
- M5: 入口卡状态依赖用户状态

### 1.2 诊断状态

| 状态 | 定义 | 触发条件 | 影响 |
|------|------|---------|------|
| `none` | 未诊断 | 用户从未做诊断 | 入口卡提示上传照片 |
| `queued` | 诊断排队中 | 用户发起诊断，等待处理 | 显示分析中状态 |
| `processing` | 分析中 | SSE流已开始 | 等待结果推送 |
| `completed` | 诊断完成 | SSE流结束，报告生成 | 可查看报告/生成方案 |
| `expired` | 诊断过期 | 上一次诊断超过30天 | 提示重新诊断 |

**真源自**：
- M2: 诊断全流程
- M5: 入口卡状态（diagnosis_status）

### 1.3 方案状态（V1.5 修订：新增 generating 状态 + 过期触发条件细化）

| 状态 | 定义 | 触发条件 | 影响 |
|------|------|---------|------|
| `none` | 无方案 | 用户从未生成方案 | 入口卡提示生成 |
| `generating` | 方案生成中 | 用户点击生成方案，等待 LLM 生成完成 | 显示生成中状态（transient） |
| `queued` | 已生成未激活 | 方案生成完成，等待用户激活 | 显示摘要，用户可点「从今天开始」或「先看完整方案」 |
| `active` | 方案进行中 | 用户点击「从今天开始」激活 | 每日任务生效 |
| `completed` | 方案完成 | 21天打卡全部完成 | 显示抱抱卡入口，30天后自动过期 |
| `expired` | 方案过期 | completed 态 30 天后未重新生成；或 active 态 started_at + 30 天未完成 | 提示重新生成 |

> **V1.5 修订说明**：
> - `generating`（V1.4 新增）：生成中（transient，等待 LLM 返回）
> - `queued`（V1.4 修订语义）：已生成未激活（persisted，用户可激活）
> - `active`（V1.5 新增过期规则）：started_at + 30 天未完成 → expired
> - `completed`（V1.5 新增过期规则）：completed_at + 30 天 → expired

**真源自**：
- M3: 方案生成与生命周期
- M5: 入口卡状态（plan_status）

### 1.4 打卡状态

| 状态 | 定义 | 触发条件 |
|------|------|---------|
| `none` | 无打卡记录 | 用户从未打卡 |
| `partial` | 部分打卡 | 完成部分天数 |
| `active` | 方案进行中 | 方案激活且在21天周期内 |
| `completed` | 方案完成 | 21天打卡全部完成 |

**真源自**：
- M4: 打卡与进度环
- M8: Day7/14/21 回忆触发依赖打卡天数

### 1.5 对话会话状态

| 状态 | 定义 | 触发条件 |
|------|------|---------|
| `none` | 无会话 | 用户从未发起对话 |
| `active` | 会话进行中 | 有 open session |
| `archived` | 会话归档 | 超过30天无交互 |
| `expired` | 会话超时 | 30分钟无交互后用户发送消息 |

**真源自**：
- M5: 会话管理（新建/历史/超时）

---

## 二、feedback 定义（唯一真源，M7/M5/M8共享）

### 2.1 feedback 类型枚举

| type | 定义 | 是否计入7天未feedback | 示例 |
|------|------|----------------------|------|
| `mood_text` | 心情文字反馈 | ✅ 是 | "今天感觉不错" |
| `mood_photo` | 心情照片反馈 | ✅ 是 | 上传1张照片 |
| `period_photo` | 补一组照片 | ✅ 是 | [补一组]入口提交 |
| `plan_compare_photo` | 方案对比照片 | ✅ 是 | [补一组]提交，带body_part |

### 2.2 feedback 不包含

| 不计入的类型 | 原因 |
|-------------|------|
| 诊断照片（M2上传的3张） | 诊断专用，不算feedback |
| 打卡动作本身 | 打卡≠feedback，可附带feedback |
| 时光相册照片 | 独立模块，不影响7天未feedback判定 |

### 2.3 7天未feedback判定

**判定公式**：
```
7天未feedback = 当前时间 - MAX(feedback.created_at) > 7天
```

**判定逻辑**：
1. 统计该用户所有 `feedback.created_at`
2. 取最新的时间戳
3. 如果距离当前时间超过7天整，则触发 `slight_hug` 状态
4. 计数周期：按自然天计算（UTC 00:00:00 为起点）

**边界说明**：
- 打卡（checkins 表）**不算作** feedback
- 打卡时附带提交的 feedback 才计入
- 诊断照片（M2）、时光相册照片**不算作** feedback

**判定实现（M5服务层）**：
```python
async def is_7_days_no_feedback(user_id: str) -> bool:
    latest_feedback = await feedback_repo.get_latest(user_id)
    if latest_feedback is None:
        # 从未提交过feedback，按7天未feedback处理
        return True
    days_since = (datetime.now(timezone.utc) - latest_feedback.created_at).days
    return days_since >= 7
```

**真源自**：
- M5: Persona 状态切换（slight_hug 触发）
- M7: feedback_service 白名单

---

## 三、合规红线（唯一真源，M5/M6/M7/M8/M10/M14共享）

### 3.1 6条绝对红线

| # | 红线名称 | 禁用词示例 | 替换文案 |
|---|---------|-----------|----------|
| C-1 | 医疗表述 | 治疗/治愈/医生/处方/病症/病 | 养护方向/生活方式建议 |
| C-2 | 效果承诺 | 会变白/会瘦/会提升/保证/肯定有效 | 建议/可以尝试 |
| C-3 | 前后对比 | 比之前好/差/进步了/改善了/变好了 | 你的感受很重要 |
| C-4 | 数字量化 | BMI/体重/三围/分数/排名/100分 | 不量化用户身体数据 |
| C-5 | 颜值评判 | 颜值/好看/美丽/漂亮/外貌 | 不评判用户外表 |
| C-6 | 强推打卡 | 必须坚持/一定要打卡/真的棒 | 今天做了就很棒 |

### 3.2 ACK 禁用词池

```
坚持/打卡/好棒/进步/改善/变好/效果/变美/变白/变瘦/
分数/排名/颜值/打败/超过/满分/100分/治疗/医美/
瘦/减/白/好看/真的棒/更美/比XX好看
```

**真源自**：
- M7: ACK话术池合规检查
- M8: Recall安全约束
- M10: 抱抱卡合规文案
- M14: 合规红线实现

### 3.3 合规执行层级

| 层级 | 名称 | 触发时机 | 执行方式 |
|------|------|---------|---------|
| L1 | 输入拦截 | 用户输入时 | 关键词扫描 + 微信sec API |
| L2 | LLM约束 | AI生成时 | System Prompt硬编码 + JSON Schema + temperature |
| L3 | 输出网关 | 流式输出时 | 逐chunk关键词检查 + 采样LLM分类 |
| L4 | 异步复审 | 发布后 | 关键词→采样LLM→人工队列 |

**真源自**：
- M14: 合规四层纵深
- M2: 诊断合规红线
- M5: 对话医疗拒答

---

## 四、错误码字典（唯一真源，跨模块）

### 4.1 错误码前缀

| 前缀 | 模块 | HTTP状态码范围 |
|------|------|--------------|
| `E_AUTH_*` | M1 认证 | 401/403 |
| `E_DIAGNOSIS_*` | M2 诊断 | 400/404/413 |
| `E_PLAN_*` | M3 方案 | 400/404/409 |
| `E_CHECKIN_*` | M4 打卡 | 400/409 |
| `E_ASSISTANT_*` | M5 对话 | 400/429/500 |
| `E_COMMUNITY_*` | M6 社区 | 400/403 |
| `E_FEEDBACK_*` | M7 反馈 | 400 |
| `E_SHARE_*` | M10 分享 | 400/500 |
| `E_NOTIFICATION_*` | M13 推送 | - |
| `E_GENERAL_*` | 通用 | 通用 |

### 4.2 核心错误码定义

| 错误码 | HTTP | 描述 | 提示文案 |
|--------|------|------|---------|
| `E_AUTH_CODE_INVALID` | 401 | 微信code失效/验证码错误 | "登录失败，请重试" / "验证码错误或已过期，请重新获取" |
| `E_AUTH_TOKEN_EXPIRED` | 401 | JWT过期 | "登录已过期，请重新登录" |
| `E_AUTH_UNIONID_CONFLICT` | 409 | unionid冲突（两独立账号） | "检测到账号冲突，请联系客服合并" |
| `E_AUTH_PHONE_ALREADY_REGISTERED` | 409 | 手机号已被注册 | "该手机号已注册，请直接登录" |
| `E_USER_AGE_BELOW_MINIMUM` | 403 | 用户年龄<18岁 | "抱歉，Selfwell 仅对 18 岁以上用户开放" |
| `E_GENERAL_RATE_LIMIT` | 429 | 通用限流 | "操作过于频繁，请稍后再试" |
| `E_ASSISTANT_RATE_LIMIT` | 429 | 日对话500次上限 | "今日对话次数已达上限" |
| `E_DIAGNOSIS_RATE_LIMIT` | 429 | 日诊断超预算 | "今日分析次数已达上限，请明天再来" |
| `E_DIAGNOSIS_INVALID_INPUT` | 400 | 照片数量/尺寸不合规 | "请上传1-3张照片" |
| `E_PLAN_ALREADY_EXISTS` | 409 | 已有活跃方案 | "已有进行中的方案" |
| `E_CHECKIN_DUPLICATE` | 409 | 今日已打卡 | "今日已打卡" |
| `E_CHECKIN_DAY_INVALID` | 400 | day ∉ [1, plan.current_day] | "打卡天数不连续（可补合）" |
| `E_CHECKIN_FEELING_TOO_LONG` | 400 | 感想超过 50 字 | "感想超过 50 字" |
| `E_CHECKIN_EDIT_WINDOW_EXPIRED` | 400 | 超过 30 分钟编辑窗口 | "已超过 30 分钟编辑窗口" |
| `E_CHECKIN_NOT_FOUND` | 404 | 打卡记录不存在或非本人 | "打卡记录不存在" |
| `E_COMPLIANCE_CONTENT_BLOCKED` | 400 | 合规拦截 | "我们换个表达试试？" |
| `E_ASSISTANT_FORBIDDEN_CALLER` | 403 | 白名单外调用 | - |
| `E_COMMUNITY_CONTENT_TOO_LONG` | 400 | 动态内容超过200字 | "内容超过200字" |
| `E_COMMUNITY_IMAGES_TOO_MANY` | 400 | 图片超过9张 | "图片最多上传9张" |
| `E_COMMUNITY_DAILY_LIMIT_USER` | 400 | 单用户每日1条动态上限 | "今日已发布过动态" |
| `E_COMMUNITY_DAILY_LIMIT_EXCEEDED` | 400 | 全平台每日10条动态上限 | "发帖功能已临时关闭" |
| `E_COMMUNITY_POST_NOT_FOUND` | 404 | 动态不存在 | "动态不存在" |
| `E_COMMUNITY_LIKED` | 200 | 点赞成功 | - |
| `E_COMMUNITY_UNLIKED` | 200 | 取消点赞 | - |
| `E_COMMUNITY_COMMENT_TOO_LONG` | 400 | 评论超过100字 | "评论超过100字" |
| `E_COMMUNITY_COMMENT_DAILY_LIMIT` | 400 | 单用户每日5条评论上限 | "今日评论次数已用完" |
| `E_COMMUNITY_ACTIVITY_NOT_FOUND` | 404 | 活动不存在 | "活动不存在" |
| `E_COMMUNITY_ACTIVITY_ALREADY_JOINED` | 409 | 重复参与活动 | "已参与此活动" |

**真源自**：所有模块的错误处理章节

---

## 五、降级策略（唯一真源，M2/M5/M8共享）

### 5.1 LLM 降级链

```
Tier 1: PRIMARY_MULTI_MODEL (P95 ≤ 15s)
    ↓ 失败（超时30s或HTTP 500）
Tier 2: BACKUP_MULTI_MODEL (P95 ≤ 20s)
    ↓ 失败
Tier 3: RULE_ENGINE (P95 ≤ 2s)
    ↓ 失败
Tier 4: SAFE_FALLBACK_ACK (P95 ≤ 1s) + 24h人工跟进
```

**真源自**：
- M2: LLM降级链
- M5: 合规红线降级
- M8: Recall安全兜底

### 5.2 连续失败锁定机制

| 条件 | 行为 | 时长 |
|------|------|------|
| 连续2次LLM调用失败 | 锁定智能分析入口 | 30分钟 |
| 锁定期间 | 不自动重试，用户操作被拦截 | - |
| 锁定超时后 | 自动解锁并重试1次 | - |
| 重试仍失败 | 保持锁定 + 发送告警（邮件+IM） | - |

**真源自**：
- M2: 连续2次LLM失败锁定

### 5.3 推送降级链

```
主通道: wx_subscribe / apns / fcm / hms
    ↓ 失败
重试: 3次（间隔5分钟）
    ↓ 3次全失败
兜底: 邮件（阿里云DirectMail，送达率≥98%）
```

**真源自**：
- M13: 推送降级策略

---

## 六、Persona 状态机（唯一真源，M5专用但被其他模块引用）

### 6.1 四态定义

| 状态 | 触发条件 | 基线问候 |
|------|---------|---------|
| `warm` | 默认/友好管家型 | "有什么想聊的吗？我在这里~" |
| `neutral` | 医疗关键词命中 | 保持中性，不带情绪倾向 |
| `slight_hug` | 连续7天无feedback | "感觉你最近没怎么分享，我随时都在。" |
| `medical_guarded` | 诊断/症状词命中（一次性） | 温柔引导咨询专业医生，之后回到warm |

### 6.2 状态转换规则

```
user_msg + 7天无feedback
    ↓
┌────────► slight_hug ──────────► warm
│    ↑                            ↑
│    │ user_msg                   │ user_msg
│    │                            │
│    warm ◄──────────────────────► neutral
│    │                            │
│    │ trigger medical             │
│    ▼                            │
│ medical_guarded ─────────────────┘
│    │
└────┘ once (回到 warm)
```

### 6.3 硬约束

1. **必经 SessionLifecycleManager**：业务节点必须通过 `persona_service.request_transition()`
2. **`medical_guarded` 一次性**：触发后必须回 warm，不允许停留
3. **转换必日志**：审计日志含 `from`/`to`/`user_id`/`ts`/`trigger`
4. **状态切换频次告警**：日均切换 > 3次即告警
5. **会话级而非消息级**：`persona_state` 是 session 级属性

**真源自**：
- M5: Persona温柔约束
- M5: Persona状态切换

---

## 七、ACK 话术池规范

### 7.1 数量要求

| 池类型 | 数量要求 | 来源 |
|--------|---------|------|
| ACK_POOL | ≥ 30条 | 打卡后温柔鼓励 |
| AI_WARM_POOL | ≥ 30条 | 社区动态暖评 |
| OFFICIAL_COMMENT_POOL | ≥ 30条 | 官方评论 |
| SAFE_FALLBACK_POOL | ≥ 30条 | 医疗拒答/安全兜底 |

### 7.2 格式要求

| 要求 | 规范 |
|------|------|
| 字数 | ≤ 30字 |
| 语气 | 温柔、非评判 |
| 禁用词 | 见 §3.2 ACK禁用词池 |

### 7.3 合规检查

```gherkin
Scenario: ACK模板合规检查
Given 运营新增1条ACK模板
When CI跑 _check_ack_safe 测试
Then 命中任意 ACK_FORBIDDEN_TOKENS 的模板被拒绝
And 合规模板才可入库
```

**真源自**：
- M7: 30条ACK模板合规检查
- M6: AI暖评池
- M14: 合规红线

---

## 十、枚举值规范（唯一真源，跨模块）

### 10.1 久坐时长（sitting_hours）

| API/数据库值 | 前端显示值 | ATDD 场景用值 |
|-------------|-----------|--------------|
| `lt4h` | 4小时以下 | `lt4h` |
| `4to8h` | 4-8小时 | `4to8h` |
| `8to12h` | 8-12小时 | `8to12h` |
| `gt12h` | 12小时以上 | `gt12h` |

**真源自**：M1 §3.1.3 / data-dictionary.md V2.0

### 10.2 年龄段（age_range）

| API/数据库值 | ATDD 场景用值 |
|-------------|--------------|
| `18-22` | `18-22` |
| `23-28` | `23-28` |
| `29-35` | `29-35` |
| `36-45` | `36-45` |
| `45+` | `45+` |

**真源自**：M1 §3.1.3 / data-dictionary.md V2.0

### 10.3 强度偏好（intensity）

| API/数据库值 | ATDD 场景用值 |
|-------------|--------------|
| `轻柔` | `轻柔` |
| `适中` | `适中` |
| `进阶` | `进阶` |

**真源自**：M1 §3.1.3 / data-dictionary.md V2.0

### 10.4 训练时段（preferred_time）

| API/数据库值 | ATDD 场景用值 |
|-------------|--------------|
| `早` | `早` |
| `中` | `中` |
| `晚` | `晚` |
| `不固定` | `不固定` |

**真源自**：M1 §3.1.3 / data-dictionary.md V2.0

### 10.5 用户状态（user_status）

| 状态值 | ATDD 场景用值 | 定义 |
|--------|-------------|------|
| `draft` | `draft` | 草稿用户 |
| `active` | `active` | 激活用户 |
| `churned` | `churned` | 流失用户 |

**真源自**：M1 §3.1.3 / ATDD-Shared.md §一.1

---

## 十一、引用规范

### 8.1 正确引用方式

```markdown
## X.XXX 相关定义

### 状态定义
详见 [ATDD-Shared.md §一](../v2/ATDD-Shared.md#一用户状态枚举)

### 合规红线
详见 [ATDD-Shared.md §三](../v2/ATDD-Shared.md#三合规红线)

### 错误码
详见 [ATDD-Shared.md §四](../v2/ATDD-Shared.md#四错误码字典)
```

### 8.2 禁止行为

- ❌ 在其他 ATDD 文档中重写 §一~§七 的内容
- ❌ 在代码中硬编码与 §三 冲突的合规规则
- ❌ 在其他文档中定义与 §二 冲突的 feedback 定义

### 8.3 修订规则

| 修订类型 | 审批流程 | 版本更新 |
|---------|---------|---------|
| 新增枚举值 | ATDD Owner 评审 | Patch版本 |
| 修改语义 | 全量回归测试 | Major版本 |
| 删除枚举值 | 废弃+迁移期 | Major版本 |

---

## 九、修订历史

| 日期 | 版本 | 改动 | 来源 |
|------|------|------|------|
| 2026-07-22 | V1.3 | 补充 M4 打卡错误码（E_CHECKIN_DAY_INVALID / FEELING_TOO_LONG / EDIT_WINDOW_EXPIRED / NOT_FOUND） | ATDD-Checkin V1.4 |
| 2026-07-21 | V1.2 | 补充 M1 认证错误码（E_AUTH_UNIONID_CONFLICT/E_AUTH_PHONE_ALREADY_REGISTERED/E_USER_AGE_BELOW_MINIMUM）；新增 §十 枚举值规范 | ATDD-Auth §七 |
| 2026-07-21 | V1.1 | 补充 M6 社区错误码（E_COMMUNITY_* 共10个） | ATDD-Community §七/§八 |
| 2026-07-21 | V1.0 | 初次创建，整合M1-M14重复定义 | ATDD整合分析 |
