# TDS-M14: 合规 - 验收标准

> **版本**: V1.0
> **状态**: Draft
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`

---

## Feature: 合规四层纵深

### Background
```gherkin
Background:
  Given 用户输入内容（聊天 / 社区发帖 / 反馈）
  And AI 生成输出
```

### Scenario: L1 输入拦截 - 微信 sec 校验（M14-FR-01）
```gherkin
Given 用户发布内容
When L1 输入拦截执行
Then 调用微信内容安全 API 校验
And 命中违规返回拒绝
And 展示"内容无法发布"提示
```

### Scenario: L1 输入拦截 - 关键词扫描（M14-FR-01）
```gherkin
Given 用户输入包含医疗词（治疗/治愈/医生/处方/病症）
Or 用户输入包含效果承诺（会变白/会瘦/会提升/保证）
Or 用户输入包含体像评判（比之前好/进步了）
When L1 关键词扫描
Then 内容被拦截
And 替换/拒绝处理
```

### Scenario: L2 LLM 约束 - System Prompt 硬编码（M14-FR-02）
```gherkin
Given AI 模型调用
When System Prompt 组装
Then 合规红线 1:1 进入 Prompt
And 5 条合规红线（治疗/效果承诺/前后对比/数字量化/颜值打分）全部 hardcode
```

### Scenario: L2 LLM 约束 - JSON Schema 约束输出（M14-FR-02）
```gherkin
Given AI 模型调用
When 输出格式校验
Then JSON Schema 约束 LLM 输出格式
And 防止越界内容
```

### Scenario: L2 LLM 约束 - temperature 控制（M14-FR-02）
```gherkin
Given AI 模型调用
When 调用诊断模型
Then temperature=0.3（低随机性）
And 调用对话模型 temperature=0.7
And 调用分类模型 temperature=0.1
```

### Scenario: L3 输出网关 - 逐 chunk 关键词检查（M14-FR-03）
```gherkin
Given AI 流式输出
When 逐 chunk 推送
Then 实时扫描敏感词
And 命中即中断
And 触发降级
```

### Scenario: L3 输出网关 - 采样 LLM 安全分类（M14-FR-03）
```gherkin
Given AI 非流式回复
When 输出完成
Then 采样 LLM 安全分类（全量）
And 分类为 unsafe 则拒绝
And 记录 audit_log
```

### Scenario: L4 异步复审 - 社区内容三段式审核（M14-FR-04）
```gherkin
Given 用户发布社区动态
When 第一段：关键词扫描执行
Then 无违规词通过，有违规词拒绝

Given 第一段通过
When 第二段：采样 LLM 分类执行（< 5s）
Then LLM 判断 safe 则进入人工队列
And LLM 判断 unsafe 则拒绝

Given 第二段通过
When 第三段：人工复核执行
Then 人工确认通过则上墙
And 人工判定违规则拒绝
```

---

## Feature: 合规红线实现

### Background
```gherkin
Background:
  Given AI 输出内容
```

### Scenario: C-1 禁止医疗表述（M14-FR-05）
```gherkin
Given AI 输出
When 合规校验
Then 不出现"治疗/治愈/医生/处方/病症/病"
And 出现时替换为"养护方向/生活方式建议"
```

### Scenario: C-2 禁止效果承诺（M14-FR-05）
```gherkin
Given AI 输出
When 合规校验
Then 不出现"会变白/会变小/会提升/保证/肯定有效"
And 仅使用建议语气（"建议"/"可以尝试"）
```

### Scenario: C-3 禁止前后对比判断（M14-FR-05）
```gherkin
Given AI 输出
When 合规校验
Then 不出现"比之前好/差/进步了/改善了"
And 替换为"你的感受很重要"
```

### Scenario: C-4 禁止数字量化（M14-FR-05）
```gherkin
Given AI 输出
When 合规校验
Then 不出现"BMI/体重/三围"等数字量化
And 不量化用户身体数据
```

### Scenario: C-5 禁止颜值评判（M14-FR-05）
```gherkin
Given AI 输出
When 合规校验
Then 不出现"颜值/外貌/变漂亮/好看/美丽"
And 不评判用户外表
```

### Scenario: C-6 禁止强推打卡（M14-FR-05）
```gherkin
Given AI 输出
When 合规校验
Then 不出现"必须坚持/一定要打卡"
And 替换为"今天做了就很棒"
```

---

## Feature: 心理健康危机识别与升级

### Background
```gherkin
Background:
  Given 用户在对话中表达情绪
```

### Scenario: L-Crisis 自杀意念立即响应（M14-FR-06）
```gherkin
Given 用户表达自杀意念/自伤行为
When 危机识别触发
Then 停止 AI 交互
And 展示危机响应卡
And 显示危机热线（全国心理援助热线 400-161-9995）
And 记录 safety_audit_logs（不含对话内容）
```

### Scenario: L-Serious 严重情绪引导（M14-FR-06）
```gherkin
Given 用户表达持续抑郁/无助/绝望情绪且无明确触发事件
When 危机识别触发
Then 展示倾听话术
And 提供专业资源指引
And 引导寻求专业帮助
```

### Scenario: L-Medical 医疗急迫响应（M14-FR-06）
```gherkin
Given 用户表达急性心理症状（惊恐发作/解离等）
When 危机识别触发
Then 建议立即就医
And 提供急诊指引
And 展示危机热线
```

### Scenario: 危机数据不记录对话原文（M14-FR-06）
```gherkin
Given 危机事件触发
When safety_audit_logs 记录
Then 记录触发关键词
And 记录时间戳
And 记录用户 ID
And 不记录对话原文
```

### Scenario: 危机记录 90 天后删除（M14-FR-06）
```gherkin
Given safety_audit_logs 记录超过 90 天
When 定时清理任务执行
Then 记录永久删除
And 符合数据保留规范
```

---

## Feature: 审计日志

### Background
```gherkin
Background:
  Given 合规事件触发
```

### Scenario: safety_audit_logs 字段记录（M14-FR-07）
```gherkin
Given 合规事件触发（违规拦截 / 危机升级）
When 系统记录
Then 写入 safety_audit_logs 表
And 字段包含：id / user_id / event_type / trigger_keywords / created_at / action_taken
And 不含对话原文
```

### Scenario: sensitive_words 表管理（M14-FR-01）
```gherkin
Given 敏感词库更新
When 运营编辑 sensitive_words 表
Then 词库版本号更新
And 新增词汇立即生效
And 删除词汇不立即删除（有冷却期）
```

### Scenario: 违规率统计（M14-FR-07）
```gherkin
Given 每日统计违规数据
When 计算违规率
Then 违规率 > 0.1% 触发告警
And 自动降级为纯规则模板
And 人工抽检 10%
```

---

## Feature: forbidden-words 与 ack-pool 引用

### Background
```gherkin
Background:
  Given forbidden-words.yaml 和 ack-pool.yaml 已定义
```

### Scenario: forbidden-words.yaml 覆盖 6 大类（M14-FR-01）
```gherkin
Given forbidden-words.yaml 定义
When 词库加载
Then 覆盖：医疗词 / 医美词 / 效果承诺 / 颜值打分 / 容貌比较 / 危机词
And 总词数 ≥ 50
And 6 大类齐全
```

### Scenario: ack-pool.yaml 30 条合规（M14-FR-02）
```gherkin
Given ack-pool.yaml 定义
When 模板加载
Then 30 条模板全部不含 forbidden_tokens
And CI 扫描 _check_ack_safe 全通过
And 每条 ≤ 30 字
```

### Scenario: 禁止在 SPEC 内嵌 ACK 文本（M14-FR-02）
```gherkin
Given SPEC 文档
When 检查内容
Then 不内嵌 ACK 文本
And 引用 ack-pool.yaml 作为唯一真源
```

---

## Feature: 每日巡检

### Background
```gherkin
Background:
  Given 每日定时执行巡检任务
```

### Scenario: 社区内容每日巡检（M14-FR-04）
```gherkin
Given 每日定时任务执行
When 扫描社区所有已发布内容
Then 检测颜值打分 / 医疗引导 / 容貌比较
And 违规自动告警
And 进入人工复核
```

### Scenario: 每日合规率报告（M14-FR-07）
```gherkin
Given 每日合规统计
When 报告生成
Then 包含：拦截次数 / 违规率 / 危机升级次数
And 发送给运营团队
```

### Scenario: 合规红线变更需评审（M14-FR-05）
```gherkin
Given 合规红线需要变更
When 运营提交变更
Then 需经过合规评审
And 评审通过后版本号更新
And 新版本生效
```
