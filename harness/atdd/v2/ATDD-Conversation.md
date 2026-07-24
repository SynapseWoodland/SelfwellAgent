# ATDD-Conversation: 智能管家对话

> **版本**: V1.4
> **状态**: Draft
> **对应模块**: M5
> **对应 TDS**: `docs/architecture/TDS/TDS-M5-persona-chat.md`
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md §3.5`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md §1.4`
>
> **设计依据**：
> - 意图定义真源：[docs/architecture/agents/assistant/assistant-intent-classification.md](../../architecture/agents/assistant/assistant-intent-classification.md)
> - 路由规则真源：[docs/architecture/agents/assistant/assistant-topic-routing.md](../../architecture/agents/assistant/assistant-topic-routing.md)
> - Persona 状态机真源：[docs/architecture/agents/assistant/assistant-persona.md](../../architecture/agents/assistant/assistant-persona.md)

---

## 一、意图分类规范

> **V1.4 架构变更**：意图（Intent）与话题（Topic）分离为两个正交维度。Intent 区分**对话姿态**（5个），Topic 区分**业务域**（6个）。此设计将 `recall_ack` / `feedback_create` / `feedback_ack` 从独立意图降为 Topic 子状态，减少 LLM 分类错误率。

### 1.1 意图层：6 个（区分对话姿态）

| 意图 | 描述 | 典型输入 | 处理方式 |
|------|------|----------|----------|
| `query` | 知识问答，查询诊断/方案/打卡状态 | "我的报告说了什么"、"今天练什么" | 查询对应数据源返回结果 |
| `share` | 情绪倾诉，吐槽/心情分享 | "今天好累"、"那些天写的好真实" | 温柔倾听 + ACK 回复 |
| `command` | 功能指令，触发模块跳转或提交 | "我要分析"、"记录一下心情"、"跳转到打卡" | ModuleDispatcher 派发到对应模块（guide + feedback_create 合并） |
| `identity` | 身份介绍、能力说明、业务边界 | "你是谁"、"你能干嘛"、"今天天气怎么样" | 身份介绍 + 能力说明 + 温柔引导 |
| `medical` | 医疗咨询，触发合规红线 | "怎么治疗颈椎病"、"需要吃什么药" | 永远拒答，温柔引导咨询专业医生 |
| `other` | 兜底，无法识别的意图 | "那个..."、"乱七八糟的" | 温柔询问澄清或提供入口卡 |

### 1.2 话题层：6 个（区分业务域，携带于 Context）

| Topic | 描述 | 典型触发 | 关联子模块 |
|--------|------|----------|------------|
| `general` | 一般对话 | 闲聊、寒暄 | — |
| `diagnosis` | 诊断/报告域 | 询问报告内容 | M2 |
| `plan` | 方案/任务域 | 询问方案内容 | M4 |
| `checkin` | 打卡域 | 询问打卡状态 | M4 |
| `recall` | 回忆域 | 点击 ◷ / 问过去的自己 | M8 |
| `feedback` | 心情日记域 | 点击 ✎ / 记录心情 | M7 |

### 1.3 组合示例

`recall_ack` 和 `feedback_ack` 不是独立意图，而是 `share + topic=recall` 和 `share + topic=feedback` 的组合：

| 用户输入 | Intent | Topic | 处理差异 |
|----------|--------|-------|----------|
| "今天好累" | `share` | `general` | 通用倾听 + ACK 池 |
| "那些天写的好真实" | `share` | `recall` | 回忆内容 ACK + 不评判 feedback 质量 |
| "刚才的心情收到了" | `share` | `feedback` | 心情日记 ACK + 不触发 LLM |
| "我要分析" | `command` | `diagnosis` | ModuleDispatcher → M2 |
| "记录一下今天的心情" | `command` | `feedback` | ModuleDispatcher → M7 |
| "跳转到打卡" | `command` | `checkin` | ModuleDispatcher → M4 |

### 1.4 Session Context（Intent + Topic 双维度）

```
Session Context {
  last_intent:  "share",           // query | share | command | identity | medical | other
  last_topic:   "recall",          // general | diagnosis | plan | checkin | recall | feedback
  last_entity:  {                  // 实体槽位
    report_id: "xxx",
    day: 7,
    part: "shoulder_neck"
  },
  turn_count:   5,                 // 连续对话轮数
  topic_stack:  ["diagnosis", "plan"]  // 话题历史栈
}
```

### 1.5 追问路由逻辑

| 用户追问 | Context.last_topic | 实际行为 |
|----------|-------------------|----------|
| "那肩颈呢" | diagnosis | 直接查肩颈指标 |
| "我的方案呢" | plan | 查询方案数据 |
| "今天打卡了吗" | checkin | 查询打卡状态 |
| "那些天写的真感人" | recall | share + recall → 回忆内容 ACK |
| "刚才的心情收到了" | feedback | share + feedback → 心情日记 ACK |
| "那另一个呢" | 歧义 | 询问澄清 |

### 1.6 意图识别优先级

```
1. medical（医疗词命中）→ 直接拒答
2. identity 关键词命中 → intent=identity
3. recall 关键词命中 → intent=command, topic=recall
4. feedback_create 关键词命中 → intent=command, topic=feedback
5. guide 关键词命中 → intent=command, topic=diagnosis
6. query（查询词命中）→ intent=query, topic 由 Context.last_topic 或 LLM 补充
7. share（情绪词命中）→ intent=share, topic 由 Context.last_topic 或 LLM 补充
8. other → 兜底处理
```

> **说明**：priorities 2~3 合并了原 V1.2 的 `recall` / `feedback_create` 独立意图。识别关键词命中后直接设 topic，LLM 仅在关键词未命中时补充 topic。

---

## 二、智能管家对话主页

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
  And 用户点击底部 Tab "智能管家"
```

### Scenario: 进入 P03a 主页 < 1 秒（M5-FR-01）
```gherkin
Given 用户点击底部 Tab "智能管家"
When 页面加载
Then 系统在 1 秒内展示 P03a 骨架（顶栏 + 对话流 + 入口卡 + 输入框）
And AI 基线问候气泡已展示
```

### Scenario: 3 入口卡持久显示（M5-FR-01）
```gherkin
Given 用户进入 P03a
Then 3 入口卡全部展示：
  | 入口卡 | 描述 |
  | 智能分析 ◎ | 跳转 M2 智能分析 |
  | 心情日记 ✎ | 跳转 M7 心情日记 |
  | 问问过去 ◷ | 触发 M8 主动回忆 |
And 入口卡点击后跳转到对应页面
And 退出再进入，入口卡仍然存在（不消失）
And 输入框始终可见（「直接输入」是输入框，不是独立入口卡）
```

> **说明**：「直接输入」是第 4 个入口卡（PRD §1.4 定义），AI 对话输入框始终可见，不需要点击触发。

---

## 三、identity 意图场景

### Background
```gherkin
Background:
  Given 用户持有有效 JWT
  And 用户进入 P03a 智能管家
```

### Scenario: 用户问"你是谁"（identity intent）
```gherkin
Given 用户输入 "你是谁"
When 意图识别
Then intent=identity, topic=general
And AI 回复身份介绍话术
And 提供功能入口引导
And 记录 ai_messages.intent='identity'
```

### Scenario: 用户问"你能干嘛"（identity intent）
```gherkin
Given 用户输入 "你能干嘛"
When 意图识别
Then intent=identity, topic=general
And AI 回复能力介绍话术
And 引导用户使用核心功能
And 记录 ai_messages.intent='identity'
```

### Scenario: 用户问天气（业务边界场景）
```gherkin
Given 用户输入 "今天天气怎么样"
When 意图识别
Then intent=identity, topic=general
And AI 回复边界引导话术
And 提供入口卡引导
And 记录 ai_messages.intent='identity', boundary='weather'
```

### Scenario: 用户问日期（业务边界场景）
```gherkin
Given 用户输入 "今天是几月几号"
When 意图识别
Then intent=identity, topic=general
And AI 回复边界引导话术
And 提供入口卡引导
And 记录 ai_messages.intent='identity', boundary='date'
```

### Scenario: 用户问数学计算（业务边界场景）
```gherkin
Given 用户输入 "帮我算算 2+3 等于多少"
When 意图识别
Then intent=identity, topic=general
And AI 回复边界引导话术
And 提供入口卡引导
And 记录 ai_messages.intent='identity', boundary='calculation'
```

### Scenario: 用户问非业务问题（业务边界场景）
```gherkin
Given 用户输入 "特朗普是谁"
When 意图识别
Then intent=identity, topic=general
And AI 回复边界引导话术
And 提供入口卡引导
And 记录 ai_messages.intent='identity', boundary='non_business'
```

### Scenario: 用户问"你是小愈同学吗"（身份确认）
```gherkin
Given 用户输入 "你是小愈同学吗"
When 意图识别
Then intent=identity, topic=general
And AI 回复身份确认话术
And 记录 ai_messages.intent='identity'
```

### Scenario: 用户问"你是真人吗"（身份确认）
```gherkin
Given 用户输入 "你是真人吗"
When 意图识别
Then intent=identity, topic=general
And AI 回复身份确认话术
And 记录 ai_messages.intent='identity'
```

### Scenario: 用户问"怎么用你"（能力介绍）
```gherkin
Given 用户输入 "怎么用你"
When 意图识别
Then intent=identity, topic=general
And AI 回复能力介绍话术
And 引导用户使用核心功能
And 记录 ai_messages.intent='identity'
```

> **说明**：identity intent 的完整定义详见 [assistant-intent-classification.md](../../docs/architecture/agents/assistant/assistant-intent-classification.md#_六identity-意图)

---

## 四、入口卡状态

### Background
```gherkin
Background:
  Given 用户持有有效 JWT
```

### Scenario: 未开始状态（M5-FR-01）
```gherkin
Given 用户刚完成登录，未做智能分析
When 用户进入 P03a
Then ◎ 智能分析：副文案 "上传 3 张照片，生成你的养护参考"
And ✎ 心情日记：副文案 "想记录今天的感受吗？"
And ◷ 问问过去：副文案 "好奇几个月的你吗？"
```

### Scenario: 进行中状态（M5-FR-01）
```gherkin
Given 用户已开始智能分析但未完成
When 用户进入 P03a
Then ◎ 智能分析：副文案 "补档案，完成分析" + ⭐薄荷绿描边
And ✎ 心情日记：副文案 "想记录今天的感受吗？"
```

### Scenario: 已完成状态（M5-FR-01）
```gherkin
Given 用户已完成智能分析 + 21 天方案
When 用户进入 P03a
Then ◎ 智能分析：副文案 "查看报告 →" + ⭐薄荷绿描边
And ◷ 问问过去：副文案 "查看对话 →" + ⭐薄荷绿描边
```

### Scenario: 7 天未互动状态（M5-FR-01）
```gherkin
Given 用户连续 7 天未上传 feedback（mood_text/mood_photo/period_photo/plan_compare_photo）
When 用户进入 P03a
Then ✎ 心情日记：副文案 "最近都没分享，要不要随便说点什么？"
And AI persona_state 切换为 'slight_hug'
```

> **说明**：feedback 定义详见 [ATDD-Shared.md §二](../ATDD-Shared.md#二feedback-定义唯一真源m7m5m8共享)

---

## 五、Persona 温柔约束

> **状态机真源**：SRS §3.5.4 + ATDD-Shared.md §六。本节 Gherkin 与两者对齐。
>
> **状态机**：
> ```
> warm (默认)
>    ↓ 用户连续 7 天无 feedback
> slight_hug ("感觉你最近没怎么分享，我随时都在")
>    ↓ 用户主动交互
> warm
>    ↓ 触发医疗/医美关键词
> medical_guarded (一次触发，回到 warm)
>    ↓
> neutral (闲聊/不知道说什么)
> ```

### Scenario: AI 不催促用户打卡（M5-FR-03）
```gherkin
Given 用户连续 3 天未打卡
When 用户进入 P03a
Then AI 不说 "你怎么还没打卡"
And AI 不说 "今天要记得打卡哦"
And AI 不出现任何催促性语句
```

### Scenario: AI 不打分/评判美丑（M5-FR-03）
```gherkin
Given 用户上传了反馈照片
When AI 回应
Then 不出现 "你打了 80 分"
And 不出现 "你的皮肤变好了"
And 不出现 "颜值/好看/瘦/美丽"
And 不出现 "进步/改善/效果"
```

### Scenario: AI 不提数字成就（M5-FR-03）
```gherkin
Given 用户连续打卡 7 天
When 用户进入 P03a
Then AI 不说 "你坚持了 7 天"
And 不说 "你进步了"
And 不出现 "分数/排名/满分/100分"
```

### Scenario: Persona warm → slight_hug（M5-FR-04）
```gherkin
Given 用户连续 7 天无 feedback
When 用户进入 P03a
Then AI persona_state 切换为 'slight_hug'
And AI 基线问候为 "感觉你最近没怎么分享，我随时都在。"
And AI 回复触发 soft-tip 引导心情日记
```

### Scenario: Persona slight_hug → warm（M5-FR-04）
```gherkin
Given AI persona_state 为 'slight_hug'
When 用户完成任意打卡或提交 feedback
Then AI persona_state 切换为 'warm'
And 基线问候恢复正常
```

### Scenario: Persona warm → medical_guarded（M5-FR-04）
```gherkin
Given AI persona_state 为 'warm'
When 用户输入命中医疗/医美关键词
Then AI persona_state 切换为 'medical_guarded'
And AI 回复委婉拒答并引导咨询专业医师
And 记录 persona_state='medical_guarded', from_state='warm', trigger='medical_keyword'
```

### Scenario: Persona medical_guarded → warm（M5-FR-04）
```gherkin
Given AI persona_state 为 'medical_guarded'
When 用户换话题后再次进入 P03a
Then AI persona_state 切换为 'warm'
And 记录 persona_state='warm', from_state='medical_guarded', trigger='topic_change'
```

### Scenario: Persona neutral 态基线问候（M5-FR-04）
```gherkin
Given AI persona_state 为 'warm'
When 用户输入闲聊/无法识别意图
Then AI persona_state 切换为 'neutral'
And AI 基线问候为 "嗯嗯，我在听。"
And AI 不带情绪倾向，不主动引导话题
And 记录 persona_state='neutral', from_state='warm', trigger='unknown_intent'
```

### Scenario: 基线问候 · 档位(a)未开始（M5-FR-04）
```gherkin
Given 用户未做诊断
When 用户进入 P03a
Then AI 基线问候从档位(a)选取
And 文案示例 "早上好，我是小愈。今天想做什么？"
And 该档位来自 greeting-pool.yaml，不走 LLM
```

### Scenario: 基线问候 · 档位(b)已诊断+今日打卡完成（M5-FR-04）
```gherkin
Given 用户已完成诊断
And 用户今日已打卡
When 用户进入 P03a
Then AI 基线问候从档位(b)选取
And 文案示例 "今天练完了，真的可以。我们明天见。"
And 该档位来自 greeting-pool.yaml，不走 LLM
```

### Scenario: 基线问候 · 档位(c)今日未打卡（M5-FR-04）
```gherkin
Given 用户已完成诊断
And 用户今日未打卡
When 用户进入 P03a
Then AI 基线问候从档位(c)选取
And 文案示例 "今天累了就休息，明天的你还在这里。"
And 该档位来自 greeting-pool.yaml，不走 LLM
```

### Scenario: 基线问候 · 档位(d)连续≥2天未打卡（M5-FR-04）
```gherkin
Given 用户连续 2 天及以上未打卡
When 用户进入 P03a
Then AI 基线问候从档位(d)选取
And 文案示例 "想休息一天也可以，先把今天的你抱抱。我们慢慢来。"
And 该档位来自 greeting-pool.yaml，不走 LLM
And persona_state 保持 warm（d档问候≠slight_hug触发）
```

> **说明**：基线问候模板池真源为 `docs/data/greeting-pool.yaml`（30条，按档位分组）。Persona状态机定义详见 [ATDD-Shared.md §六](../ATDD-Shared.md#六persona-状态机唯一真源m5专用但被其他模块引用)

---

## 六、Day N 主动推回忆气泡

### Background
```gherkin
Background:
  Given 用户已完成 Day 7 方案
  And 用户进入 P03a
```

### Scenario: Day 7 主动推回忆气泡（M5-FR-05）
```gherkin
Given 用户已完成 Day 7 方案
When 用户进入 P03a
Then AI 主动推送回忆气泡
And 气泡文案 "我们已经一起走了 7 天。要不要看看 7 天前的自己？"
And 气泡触发 recall_flow
```

### Scenario: Day 14 主动推回忆气泡（M5-FR-05）
```gherkin
Given 用户已完成 Day 14 方案
When 用户进入 P03a
Then AI 主动推送回忆气泡
And 气泡文案 "14 天前的你，有些话想说给你听。要看看吗？"
And 气泡触发 recall_flow
```

### Scenario: Day 21 主动推回忆气泡（M5-FR-05）
```gherkin
Given 用户已完成 Day 21 方案
When 用户进入 P03a
Then AI 主动推送回忆气泡
And 气泡文案 "21 天，我们一起走到了这里。要不要回头看看？"
And 气泡触发 recall_flow
```

### Scenario: Recall 触发频率限流（M5-FR-05）
```gherkin
Given 用户在 24 小时内已触发 5 次 Recall（主动回忆）
When 用户再次点击 ◷ 入口卡
Then 返回业务码 E_ASSISTANT_RATE_LIMIT
And 提示"今天回忆次数已用完，明天再来吧~"
And 不触发 Recall Flow
And 记录限流日志（recall_attempt, rate_limited=true）
```

> **说明**：Day N 触发规则详见 [ATDD-Shared.md §一.4](../ATDD-Shared.md#一用户状态枚举)；Recall Safety 三层防线详见 [ATDD-Shared.md §三](../ATDD-Shared.md#三合规红线)；触发频率限流 CSR-6 详见 [PRD §1.6](../PRD/Selfwell-PRD-V1.1.md#1.6-主动回忆-day-7-14-21)。

### Scenario: AI 不在用户未进 P03a 时弹出（M5-FR-03）
```gherkin
Given 用户在 P09 广场 / P11 我的主页
Then P03a 不会主动推送任何气泡
And 客户端埋点验证 0 次意外弹出
```

---

## 七、会话管理

### Background
```gherkin
Background:
  Given 用户持有有效 JWT
```

### Scenario: 30 分钟无交互关闭会话（M5-FR-06）
```gherkin
Given 用户在 P03a 有 open session
And 用户 30 分钟无交互
When 用户再次发送消息
Then 系统提示"会话已超时"
And 需要新建会话
```

### Scenario: 5 分钟内相同输入返回缓存（M5-FR-06）
```gherkin
Given 用户在 5 分钟内发送相同消息
When 用户再次发送
Then 直接返回缓存 AI 回复
And 不触发 LLM 调用
```

### Scenario: 日对话量上限 500 次（M5-FR-02）
```gherkin
Given 用户日对话量已达 500 次
When 用户尝试发送消息
Then 返回业务码 E_ASSISTANT_RATE_LIMIT
And 提示"今日对话次数已达上限"
```

---

## 八、诊断结果对话

### Background
```gherkin
Background:
  Given 用户已完成智能诊断并获得报告
  And 用户持有有效 JWT
```

### Scenario: 用户询问诊断报告内容（M5-FR-07）
```gherkin
Given 用户完成诊断后进入 P03a
When 用户输入"我的报告说了什么"
Then AI 基于诊断报告生成回答
And 回答引用具体报告数据（如"肩颈疲劳指数"）
And 回复符合 Persona 温柔风格
And 记录 ai_messages.context='diagnosis_qa'
```

### Scenario: 用户追问诊断细节（M5-FR-07）
```gherkin
Given 用户刚询问"我的报告说了什么"
And AI 已返回诊断摘要
When 用户输入"肩颈疲劳是什么意思"
Then AI 进一步解释"肩颈疲劳"指标含义
And 不出现医疗建议或诊断
And 保持温柔非评判风格
```

### Scenario: 用户对诊断结果表示担忧（M5-FR-07）
```gherkin
Given 用户询问诊断结果
When 用户输入"这代表我很严重吗"
Then AI 温柔安抚情绪
And 不确认或否认诊断结果
And 引导用户"这份报告仅供参考，如有疑虑建议咨询专业医生"
And 记录 ai_messages.trigger='emotional_support'
```

### Scenario: 诊断结果已过期（M5-FR-07）
```gherkin
Given 用户上一次诊断已超过 30 天
When 用户询问诊断结果
Then AI 提示"上次分析已经是 30 天前了，要不要重新分析一下？"
And 引导用户重新上传照片进行诊断
```

---

## 九、21 天方案对话

### Background
```gherkin
Background:
  Given 用户已完成 21 天方案生成
  And 用户持有有效 JWT
```

### Scenario: 用户询问方案内容（M5-FR-08）
```gherkin
Given 用户完成方案生成后进入 P03a
When 用户输入"我的 21 天计划是什么"
Then AI 基于方案数据生成回答
And 回答包含今日任务、本周重点、阶段目标
And 回复符合 Persona 温柔鼓励风格
And 记录 ai_messages.context='plan_qa'
```

### Scenario: 用户追问方案细节（M5-FR-08）
```gherkin
Given 用户刚询问"我的计划是什么"
And AI 已返回方案摘要
When 用户输入"为什么今天要练肩颈"
Then AI 解释"根据你的诊断结果，肩颈是重点关注区域"
And 引用诊断报告中相关指标
```

### Scenario: 用户询问方案调整（M5-FR-08）
```gherkin
Given 用户询问方案内容
When 用户输入"我今天太累了，可以跳过吗"
Then AI 理解用户疲劳状态
And 温柔回应"当然可以休息一天，明天继续也没关系"
And 不强制要求用户完成任务
And 记录 ai_messages.trigger='plan_adjustment'
```

### Scenario: 用户询问方案进度 - 问天数（M5-FR-08）
```gherkin
Given 用户已完成 7 天打卡
When 用户输入"我打卡几天了"或"坚持几天了"
Then AI 回复"你已经打卡 7 天了"
And 不提及百分比或分数
And 不出现"坚持/棒/进步/效果"等评判词
And 引导继续坚持
```

### Scenario: 用户询问方案进度 - 问表现（M5-FR-08）
```gherkin
Given 用户已完成 7 天打卡
When 用户输入"我表现怎么样"或"我完成多少了"
Then AI 回复"你已经打卡有一段时间了，很棒！"（不提具体天数）
And 不提及百分比或分数
And 不出现"坚持/棒/进步/效果/分数/排名"等评判词
```

> **说明**：区分"问天数"（客观事实可说数字）与"问表现"（温柔鼓励不提数字），与 M5-FR-03 的绝对禁止一致。详见 [ATDD-Shared.md §三](../ATDD-Shared.md#三合规红线)

### Scenario: 用户询问诊断与方案关联（M5-FR-08）
```gherkin
Given 用户已完成诊断 + 21 天方案
When 用户输入"我的报告和方案有什么关系"
Then AI 解释"根据你的诊断报告，我们针对肩颈疲劳等问题制定了 21 天方案"
And 引用诊断报告中相关指标
And 回复符合 Persona 温柔鼓励风格
```

### Scenario: 用户对比诊断与当前状态（M5-FR-08）
```gherkin
Given 用户已完成诊断 + 21 天方案
When 用户输入"我觉得比之前好一点了"
Then AI 温柔回应用户的感受
And 不提前后变化/改善/进步等评判词
And 记录 ai_messages.trigger='self_comparison'
```

### Scenario: 用户询问方案结束后的计划（M5-FR-08）
```gherkin
Given 用户已完成 21 天方案
When 用户输入"21 天之后怎么办"
Then AI 温柔回应"21 天是一段很棒的旅程。之后可以继续每天打卡，保持这个节奏"
And 不提"坚持/进步/改善"等评判词
And 引导继续陪伴
```

---

## 十、多轮对话

### Background
```gherkin
Background:
  Given 用户在 P03a 有 open session
  And 用户持有有效 JWT
```

### Scenario: 连续追问场景（M5-FR-09）
```gherkin
Given 用户发送"我的报告说了什么"
And AI 返回诊断摘要
When 用户连续追问"那肩颈呢"、"肩颈疲劳怎么改善"、"按摩有用吗"
Then AI 保持上下文连贯理解
And 依次回答每个问题
And 不因连续追问产生上下文混淆
And 每条回复记录独立的 ai_messages
```

### Scenario: 追问跨主题场景（M5-FR-09）
```gherkin
Given 用户询问"我的报告说了什么"
And AI 返回诊断摘要
When 用户输入"那我的 21 天计划呢"
Then AI 理解用户切换话题
And 基于方案数据回答新问题
And 保持对话连贯性
And 记录 ai_messages.topic_change='diagnosis_to_plan'
```

### Scenario: 澄清场景 - 用户表述模糊（M5-FR-09）
```gherkin
Given 用户输入"那个"
When SmartRouter 无法理解意图
Then AI 温柔询问"你在说哪个呢？可以说得更具体一点吗？"
And 提供入口卡引导
And primary_intent='other'
And context.clarification_needed=true
```

### Scenario: 澄清场景 - 歧义理解确认（M5-FR-09）
```gherkin
Given 用户输入"我想分析"
When SmartRouter 无法确定"分析"指向（诊断分析/方案回顾/情绪分析）
Then AI 询问"你是想分析什么？我可以帮你分析肩颈照片、回顾方案进度，或者聊聊今天的心情~"
And 提供明确选项
And primary_intent='other'
And context.disambiguation=true
```

### Scenario: 多轮对话上下文记忆（M5-FR-09）
```gherkin
Given 用户连续对话 5 轮以上
When 用户输入"和之前说的一样"
Then AI 理解"之前"指向上下文
And 结合最近对话内容理解指代
And 给出连贯回复
And 不要求用户重复之前内容
```

### Scenario: 多轮对话上下文上限（M5-FR-09）
```gherkin
Given 用户连续对话超过 20 轮
When 用户继续发送消息
Then AI 触发上下文压缩
And 保留关键信息（诊断结果、方案进度、最近话题）
And 对话继续流畅进行
And 记录 ai_messages.context_truncated=true
```

### Scenario: 对话打断恢复场景（M5-FR-09）
```gherkin
Given 用户发起一个问题（如"我的报告说了什么"）
When AI 正在生成回复中用户发送新消息（如"等等，先看另一个"）
Then 系统中断上一回复生成
And 基于新消息生成回复
And 不产生冲突或混乱的回复
And 记录 ai_messages.interrupted=true
```

---

## 十一、新建会话

### Background
```gherkin
Background:
  Given 用户在 P03a 存在 open session
  And 用户持有有效 JWT
```

### Scenario: + 按钮显示与触发（M5-FR-11）
```gherkin
Given 用户在 P03a 有 open session
When 用户进入 P03a
Then 顶栏右上角「+」图标可见
When 用户点击「+」按钮
Then 弹出二次确认对话框，文案"想换个话题聊聊?"
And 提供"确认"和"取消"两个选项
```

### Scenario: 确认新建会话（M5-FR-11）
```gherkin
Given 用户点击「+」并弹出确认框
When 用户点击"确认"
Then 系统关闭当前 open session
And 清空当前会话上下文（context_window）
And 回到 P03a 首屏基线问候
And 历史会话列表中仍保留该会话记录
And 短期记忆清除，中期/长期记忆保留
And persona_state 保持不变
```

### Scenario: 取消新建会话（M5-FR-11）
```gherkin
Given 用户点击「+」并弹出确认框
When 用户点击"取消"
Then 对话框关闭，回到原 open session
And 会话上下文保持不变
And AI 上下文连续
```

### Scenario: 首屏无 open session 时不显示 + （M5-FR-11）
```gherkin
Given 用户首次进入 P03a，无 open session
When 用户进入 P03a
Then 顶栏右上角「+」图标不显示
And 直接展示基线问候
```

### Scenario: 30 分钟内新建会话频率限制（M5-FR-11）
```gherkin
Given 用户在 30 分钟内已新建会话 3 次
When 用户再次点击「+」
Then 按钮置灰禁用
And 提示"先聊一会儿再说吧~"
And 记录新建会话频次到 redis（TTL 30 分钟）
```

---

## 十二、查看会话历史

### Background
```gherkin
Background:
  Given 用户持有有效 JWT
  And 用户至少有 1 个历史会话
```

### Scenario: 入口与列表展示（M5-FR-12）
```gherkin
Given 用户进入 P03a
When 用户点击历史会话入口（顶栏左侧「≡」或长按顶栏）
Then 跳转到 P03a-History 页面
And 展示历史会话列表，每项含：标题（首条消息前 15 字）+ 时间（CST）+ 消息数
And 列表按 last_active_at DESC 排序
```

### Scenario: 历史会话 API 契约（M5-FR-12）
```gherkin
Given 用户请求历史会话列表
When 调用 GET /api/v1/assistant/sessions/history?page=1&size=20
Then 返回 sessions 数组：[{id, title, last_active_at, message_count, status: 'active'|'archived'}]
And 总数 total
And 分页参数 page / size
```

### Scenario: 加载历史会话上下文（M5-FR-12）
```gherkin
Given 用户在历史列表点击某条会话
When 用户点击会话项
Then 系统加载该会话的完整消息记录（GET /api/v1/assistant/sessions/{id}）
And 跳转到 P03a 对话流
And 上下文恢复至该会话的最新状态
And AI 保持对话连贯
```

### Scenario: 30 天保留策略（M5-FR-12）
```gherkin
Given 用户某会话的最后活跃时间距今 > 30 天
When 用户查看历史列表
Then 该会话置灰显示
And 文案"已归档"
And 点击提示"该对话已超出保留期限"
```

### Scenario: 历史不计入日对话上限（M5-FR-12）
```gherkin
Given 用户日对话量已达 500 次
When 用户点击历史会话并浏览消息
Then 不返回 E_ASSISTANT_RATE_LIMIT
And 历史会话浏览不计入日对话上限
And 仅"发送消息"动作计入 500 次限额
```

### Scenario: 会话标题合规脱敏（M5-FR-12）
```gherkin
Given 用户某会话首条消息包含医疗关键词（如"治疗痤疮"）
When 用户查看历史列表
Then 标题自动脱敏为合规文案（如"皮肤相关"）
And 过滤规则来自 docs/data/recall-forbidden-words.yaml
And 不出现"治疗/瘦了/好看/改善"等敏感词
```

### Scenario: 会话标题合规脱敏 API（G5-FR-12）
```gherkin
Given GET /api/v1/assistant/sessions/history
When 返回 sessions 数组
Then 每条 title 字段经合规过滤
And 医疗/外貌词被替换为中性词
And 过滤后 title 不含 ATDD-Shared §3.2 禁用词
```

### Scenario: 新建会话 API（M5-FR-11）
```gherkin
Given 用户点击「+」并确认
When 调用 POST /api/v1/assistant/sessions/new
Then 返回新会话 ID（id, title=null, status='active', created_at）
And 旧 open session 自动关闭（status → 'archived'）
And 新会话立即可写消息
```

### Scenario: 关闭指定会话 API（M5-FR-11）
```gherkin
Given 用户在 P03a 有 open session
When 调用 POST /api/v1/assistant/sessions/{id}/close
Then 该会话 status 变为 'archived'
And 会话上下文保留（30 天后可查）
And persona_state 保持不变
And 返回 {success: true}
```

### Scenario: 获取活跃会话 API（M5-FR-06）
```gherkin
Given 用户在 P03a 有 open session
When 调用 GET /api/v1/assistant/sessions/active
Then 返回当前活跃会话（id, title, created_at, last_active_at, message_count）
And 若无 open session 则返回 null（不报错）
```

### Scenario: 入口卡状态 API（M5-FR-01）
```gherkin
Given 用户持有有效 JWT
When 调用 GET /api/v1/assistant/entry-cards
Then 返回 3 个入口卡状态：
  | card_id | status | subtitle |
  | diagnosis | none/in_progress/completed/expired | 动态文案 |
  | mood_diary | none/active | 动态文案 |
  | recall | none/available | 动态文案 |
And 根据 diagnosis_status / plan_status / feedback_status 动态计算
And 输入框始终可见（不作为独立入口卡）
```

### Scenario: 获取智能分析 SSE 流 API（M5-FR-07）
```gherkin
Given 用户发起智能分析
When 调用 GET /api/v1/assistant/smart_analyze/stream
Then SSE 流按顺序推送：connected → analyzing_photos → calling_vision_llm → summarizing → calling_text_llm → done
And 每 15 秒推送心跳事件
And P95 总耗时 ≤ 20s
And 失败时推送 fallback/error 事件
```

### Scenario: 语音上传 API（M5-FR-13）
```gherkin
Given 用户完成录音并发送
When 调用 POST /api/v1/assistant/voice/upload（multipart/form-data，audio 文件）
Then 返回 {text: "识别文字", audio_url: "可播放URL"}
And 识别失败时返回 {text: null, error: "识别失败"}
And 语音文件 7 天后自动删除
```

### Scenario: 获取语音文件 API（M5-FR-13）
```gherkin
Given 用户在历史会话中点击含语音的消息
When 调用 GET /api/v1/assistant/voice/audio?message_id=xxx
Then 返回语音文件流（audio/mp3 或 audio/wav）
And 无权限用户（跨用户）返回 403
```

### Scenario: 归档会话点击后 API（M5-FR-12）
```gherkin
Given 用户某会话的最后活跃时间距今 > 30 天
When 用户点击该会话
Then 调用 GET /api/v1/assistant/sessions/{id}
And 返回业务码 E_ASSISTANT_SESSION_EXPIRED
And 前端提示"该对话已超出保留期限"
```

### Scenario: 单用户 50 个会话上限 API（M5-FR-12）
```gherkin
Given 用户已有 50 个活跃会话（status='active'）
When 用户新建第 51 个会话
Then POST /api/v1/assistant/sessions/new 返回成功
And 最旧会话自动归档（status → 'archived'）
And 列表仍展示最近 50 个活跃会话
```

### Scenario: 单用户 50 个会话上限（M5-FR-12）
```gherkin
Given 用户已有 50 个历史会话
When 用户新建第 51 个会话
Then 最旧的会话自动归档
And 列表仍展示最近 50 个活跃会话
And 归档会话仅可在"已归档"分组查看
```

### Scenario: 无历史会话空态（M5-FR-12）
```gherkin
Given 用户无任何历史会话
When 用户进入 P03a-History
Then 显示空态："还没有对话记录，从下面的入口卡开始吧~"
And 提供"返回首页"按钮
```

---

## 十三、语音识别输入

### Background
```gherkin
Background:
  Given 用户在 P03a
  And 用户已授权麦克风权限
  And 用户持有有效 JWT
```

### Scenario: 入口与状态机（M5-FR-13）
```gherkin
Given 用户在 P03a 输入框
When 用户点击右侧麦克风图标
Then 切换至 recording 状态
And 顶部提示"小满正在听..."
And 展示实时波形动画
And 录音时长开始计数
```

### Scenario: 松开发送语音（M5-FR-13）
```gherkin
Given 用户处于 recording 状态
When 用户松开麦克风按钮
Then 切换至 processing 状态
And 调用 /api/v1/assistant/voice/upload 上传语音文件
And 识别成功后切换至 done 状态
And 自动填充文字到输入框
And 用户可编辑后发送
```

### Scenario: 取消录音（M5-FR-13）
```gherkin
Given 用户处于 recording 状态
When 用户点击"取消"按钮
Then 切换至 cancel 状态
And 删除本地录音
And 回到 idle 状态
And 不上传语音文件
```

### Scenario: 60 秒自动超时（M5-FR-13）
```gherkin
Given 用户录音时长达到 60 秒
When 录音自动结束
Then 切换至 processing 状态
And 自动上传已识别部分
And 提示"录音超时，已发送前 60 秒"
```

### Scenario: 识别失败兜底（M5-FR-13）
```gherkin
Given 用户处于 processing 状态
When 语音识别 API 返回失败
Then 切换至 done 状态
And toast 提示"我没听清，你可以打字告诉我~"
And 不填充文字到输入框
And 录音文件删除
```

### Scenario: 麦克风权限被拒（M5-FR-13）
```gherkin
Given 用户首次点击麦克风
When 系统检测到麦克风权限被拒
Then toast 提示"需要麦克风权限才能语音哦"
And 提供"去设置"按钮
And 引导到系统设置页面
```

### Scenario: 隐私合规 - 必须显式提示（M5-FR-13，红线 V-1）
```gherkin
Given 用户处于 recording 状态
When 任意时刻查询录音状态
Then 顶部必须显示"小满正在听..."提示
And 录音指示器可见
And 不允许后台静默录音
```

### Scenario: 隐私合规 - 后台停止录音（M5-FR-13，红线 V-2）
```gherkin
Given 用户处于 recording 状态
When 用户切换到后台（home 键 / 切其他 App）
Then 录音立即停止
And 切换至 cancel 状态
And 删除已录制片段
And 回到 idle 状态
```

### Scenario: 语音转文字后意图分类（M5-FR-13）
```gherkin
Given 用户语音识别成功
When 用户点击"发送"
Then 文字消息走相同意图分类（query/share/command/medical/other）
And 走相同 L1 输入拦截
And 走相同 Persona 状态机
And 走相同 Topic 补充逻辑
```

### Scenario: 语音文件 7 天后清除（M5-FR-13）
```gherkin
Given 用户某语音消息已保存 7 天
When 系统后台清理任务运行
Then 删除该语音文件
And 消息记录保留文字部分
And audio_url 字段置 null
```

### Scenario: 录音时长 < 0.5 秒视为误触（M5-FR-13）
```gherkin
Given 用户点击麦克风
When 用户在 0.5 秒内松开
Then 视为误触，不上传
And 直接回到 idle 状态
And 不提示错误
```

### Scenario: 语音输入不支持端降级（M5-FR-13）
```gherkin
Given 用户使用的客户端不支持语音 API
When 用户进入 P03a
Then 输入框右侧麦克风图标隐藏
And 仅展示文字输入
And 不显示降级提示
```

---

## 十四、合规红线

### Scenario: LLM 调用 4 级降级链全失败（M5-FR-02）
```gherkin
Given LLM 服务不可用
And 规则引擎不可用
When 用户发送消息
Then 返回温柔兜底回复
And 记录 ai_messages.trigger='llm_error'
And 返回业务码 E_ASSISTANT_LLM_ERROR
And 承诺"24 小时内人工跟进"
And 记录人工跟进工单（pending_human_followup=true, user_id, created_at）
```

> **说明**：降级链详见 [ATDD-Shared.md §五.1](../ATDD-Shared.md#五降级策略唯一真源m2m5m8共享)。P4 Fallback ACK 模板 ≥ 30 条，详见 [ATDD-Shared.md §七](../ATDD-Shared.md#七ack-话术池规范)。

---

## 十五、语音合规（引用 M14）

### Background
```gherkin
Background:
  Given 用户通过语音输入内容（M5-FR-13）
```

### Scenario: V-1 永不静默录音（M5-FR-13）
```gherkin
Given 用户按住麦克风录音
When 录音开始
Then 必须显示"小满正在听..."提示框
And 禁止在提示框显示前就开始录音
```

### Scenario: V-2 永不后台录音（M5-FR-13）
```gherkin
Given 用户在录音过程中切换 App 到后台
When 检测到应用进入后台
Then 立即停止录音
And 不上传未完成的录音片段
```

### Scenario: V-3 永不上传非主动录音（M5-FR-13）
```gherkin
Given 用户未主动发送语音
When 检查上传队列
Then 不存在非用户主动触发的录音上传
And 每次上传必须有用户点击发送动作
```

### Scenario: V-4 语音走相同 LLM 合规四层（M5-FR-13）
```gherkin
Given 用户发送语音
When 语音识别完成
Then 识别文本进入 L1 输入拦截（关键词 + 微信 sec）
And LLM 输出走 L2~L4 合规层
And 语音文件 7 天后自动删除
```

### Scenario: 语音输入触发 L-Crisis 升级（M5-FR-13 + M14 合规）
```gherkin
Given 用户通过语音输入内容
When 语音识别完成
And 识别文本命中 L-Crisis 关键词（自杀/自伤/活着的意义等）
Then AI 立即停止所有交互
And 展示危机响应卡（全国心理援助热线：400-161-9995）
And 不存储该段对话内容（ai_messages 表 content 字段置 null）
And 记录合规审计日志（trigger=L-Crisis, channel=voice, user_id, ts）
And 不触发 LLM 调用
And 不触发 ACK 池
And 记录人工跟进工单
```

### Scenario: 语音输入触发 L-Serious 升级（M5-FR-13 + M14 合规）
```gherkin
Given 用户通过语音输入内容
When 语音识别完成
And 识别文本命中 L-Serious 关键词（持续抑郁/无助/绝望等，无明确触发事件）
Then AI 暂停提供建议
And 展示温柔倾听话术 + 专业心理援助资源
And 记录合规审计日志（trigger=L-Serious, channel=voice）
And 不触发 LLM 生成建议
```

> **说明**：L-Crisis / L-Serious / L-Medical 分级详见 [ATDD-Shared.md §三](../ATDD-Shared.md#三合规红线) + [PRD §3.5](../PRD/Selfwell-PRD-V1.1.md#35-心理健康危机识别与升级)。

---

## 十六、引用说明

### 相关定义
- 入口卡状态枚举：详见 [ATDD-Shared.md §一.5](../ATDD-Shared.md#一用户状态枚举)
- Persona状态机：详见 [ATDD-Shared.md §六](../ATDD-Shared.md#六persona-状态机唯一真源m5专用但被其他模块引用)
- feedback定义：详见 [ATDD-Shared.md §二](../ATDD-Shared.md#二feedback-定义唯一真源m7m5m8共享)
- 合规红线：详见 [ATDD-Shared.md §三](../ATDD-Shared.md#三合规红线)
- 错误码定义：详见 [ATDD-Shared.md §四](../ATDD-Shared.md#四错误码字典)
- 用户旅程：详见 [ATDD-Journey.md](../ATDD-Journey.md)
- 语音合规红线：详见 [ATDD-Compliance.md §语音合规](#)
- 危机词表管理：详见 [TDS-M14-compliance.md §6](../architecture/TDS/TDS-M14-compliance.md#6-危机词表管理)

---

## 十七、修订历史

| 日期 | 版本 | 改动 | 来源 |
|------|------|------|------|
| 2026-07-22 | V1.6 | 新增设计真源引用：§一意图分类引用 assistant-intent-classification.md；§三 identity 场景引用 assistant-overview.md | 文档引用体系改造 |
| 2026-07-21 | V1.0 | 初次创建 | |
| 2026-07-21 | V1.1 | 修复M5-FR-08与M5-FR-03矛盾（不提具体天数） | |
| 2026-07-22 | V1.2 | 新增 identity intent（6个意图）+ identity 意图场景章节（三） | |
| 2026-07-22 | V1.3 | 新增 identity ATDD 场景（身份介绍、能力说明、业务边界） | |
| 2026-07-21 | V1.2 | 新增§十四语音合规V-1~V-4；补充合规引用 | 审查ATDD-Compliance缺口 |
| 2026-07-22 | V1.5 | **全面文档对齐修复**：1. §二：入口卡4→3张（「直接输入」改为输入框本身，非独立卡）2. §四：Persona状态机完整重建（新增warm→slight_hug/medical_guarded退出/状态图说明）3. §四：新增基线问候4档场景（档位a/b/c/d）4. §八：新增诊断与方案联合对话3个场景（询问关联/对比状态/结束后计划）5. §十一：entry-cards API返回改为3张卡 | 三端文档差距分析+用户确认（Q1-Q10全面修复）|
| 2026-07-22 | V1.4 | §一：意图分类重构——Intent(5个)与Topic(6个)分离，移除recall_ack/feedback_create/feedback_ack独立意图，合并为command/share+topic组合；§一：新增1.2 Topic层、1.3组合示例、1.5组合示例；§一：1.6意图识别优先级更新 | 架构优化：减少LLM分类错误率 |
| 2026-07-22 | V1.3 | 1. §一：6类意图→8类（新增recall_ack/feedback_create/feedback_ack）<br>2. §二：补充4入口卡（新增直接输入）<br>3. §四：新增neutral态基线问候<br>4. §五：新增Day14/21回忆气泡+频率限流<br>5. §八：区分"问天数"与"问表现"两个场景<br>6. §十一：补充完整API Gherkin（sessions/new/close/active/entry-cards/voice等）<br>7. §十三：4级降级链补充24h人工跟进承诺<br>8. §十四：新增语音L-Crisis/L-Serious危机词升级场景 | ATDD-SRS差距分析+用户确认（区分场景+双PR同步）|
