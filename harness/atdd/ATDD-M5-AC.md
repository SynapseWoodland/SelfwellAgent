# TDS-M5: Persona对话 - 验收标准

> **版本**: V1.2
> **状态**: Draft
> **对应需求真源**: `docs/requirements/SELFWELL-MVP-SRS.md §3.5`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md` §1.4

---

## 意图分类规范

### 一级意图分类（6 个）

| 意图 | 描述 | 典型输入 | 处理方式 |
|------|------|----------|----------|
| `guide` | 功能引导，触发模块跳转 | "我要分析"、"跳转到打卡"、"开始诊断" | ModuleDispatcher 派发到对应模块 |
| `query` | 知识问答，查询诊断/方案/打卡状态 | "我的报告说了什么"、"今天练什么" | 查询对应数据源返回结果 |
| `share` | 情绪倾诉，吐槽/心情分享 | "今天好累"、"心情不好" | 温柔倾听 + ACK 回复 |
| `recall` | 主动回忆，与过去自己对话 | "问过去的自己"、"看看一周前的我" | 触发 M8 Recall Flow |
| `medical` | 医疗咨询，触发合规红线 | "怎么治疗颈椎病"、"需要吃什么药" | 永远拒答，温柔引导咨询专业医生 |
| `other` | 兜底，无法识别的意图 | "那个..."、"乱七八糟的" | 温柔询问澄清或提供入口卡 |

### 上下文 Topic 设计（追问处理）

追问不新建意图，靠 **Session Context** 桥接：

```
Session Context {
  last_intent: "query",           // 上一次意图
  last_topic: "diagnosis",        // diagnosis | plan | checkin | general
  last_entity: {                  // 实体槽位
    report_id: "xxx",
    day: 7,
    part: "shoulder_neck"
  },
  turn_count: 5,                  // 连续对话轮数
  topic_stack: ["diagnosis", "plan"]  // 话题历史栈
}
```

### 追问路由逻辑

| 用户追问 | Context.last_topic | 实际行为 |
|----------|-------------------|----------|
| "那肩颈呢" | diagnosis | 直接查肩颈指标 |
| "我的方案呢" | plan | 查询方案数据 |
| "今天打卡了吗" | checkin | 查询打卡状态 |
| "那另一个呢" | 歧义 | 询问澄清 |

### 意图识别优先级

```
1. medical (医疗词命中) → 直接拒答
2. recall (回忆关键词命中) → 触发 Recall
3. guide (功能引导词命中) → 模块跳转
4. query (查询词命中) → 查询数据
5. share (情绪词命中) → 倾听回复
6. other → 兜底处理
```

---

## Feature: 智能管家对话主页

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
Then 3 入口卡（🔍智能分析 / 📖心情日记 / 💬问过去的自己）全部展示
And 入口卡点击后跳转到对应页面
And 退出再进入，入口卡仍然存在（不消失）
```

### Scenario: guide 意图触发模块跳转（M5-FR-02）
```gherkin
Given 用户输入"我想分析肩颈"
When SmartRouter 分类为 guide
Then ModuleDispatcher 派发到 M2 智能分析
And AI 回复引导用户上传照片
And primary_intent='guide'
```

### Scenario: medical 意图永远拒答（M5-FR-02）
```gherkin
Given 用户输入"怎么治疗颈椎病"
When SmartRouter 命中医疗关键词
Then AI 回复委婉拒绝
And 回复不含任何医疗建议
And primary_intent='medical'
And 记录 ai_messages.trigger='medical'
```

### Scenario: share 意图走温柔倾听（M5-FR-02）
```gherkin
Given 用户输入"今天心情好复杂"
When SmartRouter 识别为 share（情绪关键词）
Then AI 回复温柔倾听："我听到了，慢慢说，我在这里。"
And 回复符合 Persona 温柔风格
And primary_intent='share'
And 记录 ai_messages.trigger='emotional_share'
```

---

## Feature: 3 入口卡状态

### Background
```gherkin
Background:
  Given 用户持有有效 JWT
```

### Scenario: 未开始状态（M5-FR-01）
```gherkin
Given 用户刚完成登录，未做智能分析
When 用户进入 P03a
Then 🔍 智能分析：副文案 "上传 3 张照片，生成你的养护参考"
And 📖 心情日记：副文案 "想记录今天的感受吗？"
And 💬 问过去的自己：副文案 "好奇几个月的你吗？"
```

### Scenario: 进行中状态（M5-FR-01）
```gherkin
Given 用户已开始智能分析但未完成
When 用户进入 P03a
Then 🔍 智能分析：副文案 "补档案，完成分析" + ⭐薄荷绿描边
And 📖 心情日记：副文案 "想记录今天的感受吗？"
```

### Scenario: 已完成状态（M5-FR-01）
```gherkin
Given 用户已完成智能分析 + 21 天方案
When 用户进入 P03a
Then 🔍 智能分析：副文案 "查看报告 →" + ⭐薄荷绿描边
And 💬 问过去的自己：副文案 "查看对话 →" + ⭐薄荷绿描边
```

### Scenario: 7 天未互动状态（M5-FR-01）
```gherkin
Given 用户连续 7 天未上传 feedback
When 用户进入 P03a
Then 📖 心情日记：副文案 "最近都没分享，要不要随便说点什么？"
And AI persona_state 切换为 'slight_hug'
```

---

## Feature: Persona 温柔约束

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

### Scenario: Persona 状态切换（M5-FR-04）
```gherkin
Given 用户连续 7 天无 feedback
When 用户进入 P03a
Then AI persona_state 切换为 'slight_hug'
And AI 基线问候为 "感觉你最近没怎么分享，我随时都在。"
And AI 回复触发 soft-tip 引导
```

---

## Feature: Day N 主动推回忆气泡

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

### Scenario: AI 不在用户未进 P03a 时弹出（M5-FR-03）
```gherkin
Given 用户在 P02 首页 / P06 广场 / P11 我的
Then P03a 不会主动推送任何气泡
And 客户端埋点验证 0 次意外弹出
```

---

## Feature: 会话管理

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

## Feature: 合规红线

### Scenario: LLM 调用 4 级降级链全失败（M5-FR-02）
```gherkin
Given LLM 服务不可用
And 规则引擎不可用
When 用户发送消息
Then 返回温柔兜底回复
And 记录 ai_messages.trigger='llm_error'
And 返回业务码 E_ASSISTANT_LLM_ERROR
```

---

## Feature: 诊断结果对话

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

## Feature: 21 天方案对话

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

### Scenario: 用户询问方案进度（M5-FR-08）
```gherkin
Given 用户已完成 7 天打卡
When 用户输入"我完成多少了"
Then AI 回复"你已经坚持了 7 天，很棒！"
And 提及已完成任务数量（不提及百分比或分数）
And 引导继续坚持
```

---

## Feature: 多轮对话

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
Then AI 询问"你是想分析什么？我可以帮你分析肩颈照片、回顾方案进度，或者聊聊今天的心情～"
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

## Feature: 诊断与方案联合对话

### Background
```gherkin
Background:
  Given 用户已完成诊断和方案生成
  And 用户持有有效 JWT
```

### Scenario: 用户询问诊断与方案关联（M5-FR-10）
```gherkin
Given 用户询问方案内容
When 用户输入"这个方案是根据什么制定的"
Then AI 解释"根据你的诊断报告，我们针对肩颈疲劳等问题制定了 21 天方案"
And 引用诊断和方案数据的关联
And 保持温柔非技术性语言
And 记录 ai_messages.context='diagnosis_plan_relation'
```

### Scenario: 用户对比诊断与当前状态（M5-FR-10）
```gherkin
Given 用户已完成 7 天打卡
When 用户输入"我觉得比之前好一点了"
Then AI 温柔回应用户感受
And 不确认或否认用户自我评估
And 可引导"坚持每天打卡，你可以更清楚地感受变化"
And 记录 ai_messages.trigger='progress_comparison'
```

### Scenario: 用户询问方案结束后的计划（M5-FR-10）
```gherkin
Given 用户已完成 21 天方案
When 用户输入"21 天之后怎么办"
Then AI 温柔回应"你已经坚持了 21 天！之后可以继续每天打卡，保持这个好习惯"
And 不承诺具体效果
And 鼓励持续参与
And 引导查看里程碑或分享
```

---

## Feature: 新建会话（M5-FR-11，PRD V1.3 §1.4.1）

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
And 不影响记忆体系（短期/中期/长期记忆保留）
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

## Feature: 查看会话历史（M5-FR-12，PRD V1.3 §1.4.2）

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

## Feature: 语音识别输入（M5-FR-13，PRD V1.3 §1.4.3）

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
When 用户点击右侧「🎤」麦克风图标
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
Then 文字消息走相同意图分类（guide/query/share/recall/medical/other）
And 走相同 L1 输入拦截
And 走相同 Persona 状态机
And 触发相同 ACK 池
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
Then 输入框右侧「🎤」图标隐藏
And 仅展示文字输入
And 不显示降级提示
```
