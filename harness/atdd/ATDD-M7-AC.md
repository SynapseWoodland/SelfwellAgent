# TDS-M7: 反馈系统 - 验收标准

> **版本**: V1.0
> **状态**: Draft
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`

---

## Feature: 心情日记（M7a）

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
  And 用户点击 📖 心情日记入口卡
```

### Scenario: 用户进入 P08 心情日记列表页 < 1 秒（M7-FR-01）
```gherkin
Given 用户点 📖 心情日记入口卡
When 页面加载
Then 系统在 1 秒内展示 P08 时间轴列表
And 按 created_at DESC 排列，最新在最上
And 显示 feedback 类型标签
```

### Scenario: 用户提交纯文字反馈（M7-FR-02）
```gherkin
Given 用户在 P08a 输入 "今天感觉不错"
When 用户点 [保存]
Then 系统写入 feedback（type=mood_text, text_content="今天感觉不错"）
And AI 回复 ≤ 30 字温柔确认（来自 ACK_POOL）
And feedback.ai_ack_id 关联 ai_messages.id
And 返回 feedback.id
```

### Scenario: 用户提交带照片反馈（M7-FR-02）
```gherkin
Given 用户在 P08a 选图 + 不填文字
When 用户点 [保存]
Then 系统写入 feedback（type=mood_photo, photo_url="..."）
And AI 回复 ≤ 30 字温柔确认
And mood_photo 时 text_content 必为空
```

### Scenario: 提交反馈 → AI 回应 ≤ 3 秒（M7-FR-02）
```gherkin
Given 用户点 [保存] 提交 feedback
When 系统处理提交
Then AI ACK 回复 P95 ≤ 3 秒
And ACK 文本来自 ACK_POOL（非 LLM 生成）
And feedback.ai_ack_id 写入
```

### Scenario: 30 条 ACK 模板全部通过禁用词扫描（M7-FR-02）
```gherkin
Given 运营新增 1 条 ACK 模板
When CI 跑 _check_ack_safe 测试
Then 命中任意 ACK_FORBIDDEN_TOKENS 的模板被拒绝
And 合规模板才可入库
And 禁用词包括：坚持/打卡/好棒/进步/改善/变好/效果/变美/变白/变瘦/分数/排名/治疗/医美/瘦/减/白/好看/颜值/打败/超过/满分/100分/坚持X天
```

---

## Feature: 多部位反馈（M7b）

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
  And 用户点击 💬 问过去的自己 → soft-tip "补一组" 入口
```

### Scenario: 用户通过 soft-tip "补一组"入口提交（M7-FR-03）
```gherkin
Given 用户点 💬 问过去的自己 → soft-tip → [补一组]
When 用户在 P08a 选图 + 选部位（face） + 点 [保存]
Then 系统写入 feedback（type=period_photo, body_part=face）
And AI 回复 ≤ 30 字
```

### Scenario: body_part 枚举与 focus_parts 对齐（M7-FR-03）
```gherkin
Given 用户在 P08a 选部位
When 系统渲染部位选择器
Then body_part 可选项：face / head / shoulder_neck / waist / leg / overall_look
And 与 users.focus_parts 枚举完全一致
```

### Scenario: plan_compare_photo 必须传 body_part（M7-FR-03）
```gherkin
Given 用户提交 type=plan_compare_photo
When body_part 为空
Then 返回错误码 E_FEEDBACK_BODY_PART_REQUIRED
And 不写入数据库
```

### Scenario: period_photo 照片来源为补拍（M7-FR-03）
```gherkin
Given 用户通过 [补一组] 入口提交
When feedback 创建
Then feedback.type='period_photo'
And photo_url 必填
And body_part 必填
```

---

## Feature: 完全可选约束

### Background
```gherkin
Background:
  Given 用户持有有效 JWT
```

### Scenario: 21 天方案不强制要求 feedback 存在（M7-FR-04）
```gherkin
Given 用户未提交任何 feedback
When 用户完成 21 天方案
Then 用户仍可正常结束方案
And 不出现 "请先填写反馈" 等强制提示
```

### Scenario: 启动 21 天方案不检查 feedback（M7-FR-04）
```gherkin
Given 用户未提交任何 feedback
When 用户点 [开始 21 天]
Then 系统直接跳转方案页
And 不触发任何 feedback 校验
```

### Scenario: 打卡不检查 feedback（M7-FR-04）
```gherkin
Given 用户未提交任何 feedback
When 用户完成打卡
Then 打卡成功
And 不出现任何 feedback 相关提示
```

---

## Feature: 服务层白名单

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
```

### Scenario: M5 输入框无法读取 photo_url（M7-FR-05）
```gherkin
Given 用户在 P03a 输入框问 "看看我之前的照片"
When SmartRouter / PersonaEngine / ModuleDispatcher 调用 feedback_service.list
Then 触发 PermissionError
And 返回错误码 E_ASSISTANT_MESSAGE_INVALID（403 映射）
And 白名单不包含 3 个组件
```

### Scenario: 白名单内服务方正常读取 feedback（M7-FR-05）
```gherkin
Given P08 心情日记列表页请求 feedback
When caller='mood_diary_list'
Then 返回该用户的全部 feedback
And 仅返回元数据（不含 photo_url）
```

### Scenario: 白名单外服务方无法读取 feedback（M7-FR-05）
```gherkin
Given 某未知模块尝试调用 feedback_service.list
When caller 不在 ALLOWED_CALLERS 列表
Then 触发 PermissionError
And 返回 403 错误
```

### Scenario: 白名单内允许的服务方（M7-FR-05）
```gherkin
Given 以下服务方调用 feedback_service
When caller 属于白名单
Then 以下服务方允许通过：mood_diary_list / recall_retrieve / time_album_list / feedback_create_own
And 其他服务方拒绝
```

---

## Feature: 错误处理

### Scenario: feedback_type 不在 4 种枚举内（M7-FR-02）
```gherkin
Given 用户提交 feedback_type='invalid_type'
When 系统校验
Then 返回错误码 E_FEEDBACK_INVALID_TYPE
And 不写入数据库
```

### Scenario: text_content 超过 500 字被拦截（M7-FR-02）
```gherkin
Given 用户输入 text_content 超过 500 字
When 用户点 [保存]
Then 返回错误码 E_FEEDBACK_TEXT_TOO_LONG
And 提示字数超限
```

### Scenario: feedback_type 与 payload 字段不一致（M7-FR-02）
```gherkin
Given 用户提交 type=mood_text
When payload 中包含 photo_url（非空）
Then 返回错误码 E_FEEDBACK_PAYLOAD_MISMATCH
And 不写入数据库
```

### Scenario: 1 分钟内重复提交被防抖（M7-FR-02）
```gherkin
Given 用户在 1 分钟内重复提交相同 feedback
When 用户再次点 [保存]
Then 防抖拦截
And 返回已有记录
And 不重复写入
```

---

## Feature: ACK 禁用词合规

### Scenario: ACK 文本不含禁用词（M7-FR-02）
```gherkin
Given ACK_POOL 30 条模板
When 任意一条模板
Then 不含：坚持/打卡/好棒/进步/改善/变好/分数/颜值/好看/治疗/医美/瘦/减/白/打败/超过/满分/100分
And _check_ack_safe 扫描返回 true
```

### Scenario: 运营新增 ACK 模板合规检查（M7-FR-02）
```gherkin
Given 运营在 ack-pool.yaml 新增 1 条模板
When CI 跑 _check_ack_safe 全量测试
Then 任意一条模板命中 forbidden_tokens 即拒绝
And CI 失败，阻止合入
And 上线前人工逐条核对 valid=true
```
