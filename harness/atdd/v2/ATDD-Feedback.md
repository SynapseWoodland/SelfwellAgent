# ATDD-Feedback: 反馈系统

> **版本**: V1.1
> **状态**: Draft
> **对应模块**: M7 + M7-Album
> **对应 TDS**: `docs/architecture/TDS/TDS-M7-feedback.md` + `docs/architecture/TDS/TDS-M7-time-album.md`
> **对应 SRS**: `docs/requirements/SELFWELL-MVP-SRS.md`
> **对应 PRD**: `docs/PRD/Selfwell-PRD-V1.1.md`

---

## 一、心情日记（M7a）

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

### Scenario: 用户提交图文心情（M7-FR-02）
```gherkin
Given 用户在 P08a 选图 + 选图文心情类型
When 用户点 [保存]
Then 系统写入 feedback（type=mood_photo, photo_url="...", text_content="今天拍了张照片"）
And AI 回复 ≤ 30 字温柔确认
And mood_photo 时 text_content 可选（非必填）
And mood_text 时 photo_url 必为空
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

## 二、多部位反馈（M7b）

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
  And 用户点击 💬 问过去的自己 → soft-tip "补一组" 入口
```

### Scenario: period_photo 两种入口（M7-FR-03）
```gherkin
Given 用户想提交周期对比照片
When 用户通过以下任一入口进入 P08a
| 入口 | 描述 |
|------|------|
| 独立心情日记入口 | 用户直接点心情日记 → 选择"周期对比照"类型 |
| soft-tip 引导 | 用户点 💬 问过去的自己 → soft-tip → [补一组] |
Then 用户在 P08a 选图 + 选部位（face） + 点 [保存]
And 系统写入 feedback（type=period_photo, body_part=face）
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

## 三、完全可选约束

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

## 四、服务层白名单

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
And 返回错误码 E_ASSISTANT_FORBIDDEN_CALLER（403 映射）
And 白名单不包含 3 个组件
```

### Scenario: 白名单内服务方正常读取 feedback（M7-FR-05）
```gherkin
Given P08 心情日记列表页请求 feedback
When caller='mood_diary_list'
Then 返回该用户的全部 feedback
And 仅返回元数据（含 photo_thumbnail_url 缩略图，不含原图 photo_url）
And 原图访问需二次鉴权
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

## 五、时光相册

### Background
```gherkin
Background:
  Given 用户已登录并持有有效 JWT
  And 用户进入时光相册页面
```

### Scenario: 用户上传 1 张照片 ≤ 5 步
```gherkin
Given 用户进入时光相册页
When 用户点击"上传照片"
And 选择照片（≤ 5 步）
Then 照片上传成功
And 返回 photo_id
And POST /album/photos 返回 201
```

### Scenario: 时间轴按上传时间倒序
```gherkin
Given 用户已上传多张照片
When 用户查看时光相册
Then 照片按上传时间倒序排列
And 最新照片在最前面
And GET /album/photos 返回 photos 按 created_at DESC
```

### Scenario: 用户可删除照片
```gherkin
Given 用户查看时光相册
When 用户点击照片的删除按钮
Then 照片被删除
And DELETE /album/photos/{id} 返回 200
And 用户可重新上传
```

### Scenario: 时光相册复用 feedback 表（V1.1 修订）
```gherkin
Given 用户在心情日记提交带照片的 feedback
When 时光相册查询用户照片时间轴
Then 时光相册复用 feedback 表（photo_url IS NOT NULL）
And 按 created_at DESC 排列
And 关联打卡日期 plan_day_id
And 仅用户本人可见
Note: 时光相册不新建 album_photos 表，直接复用 feedback 表
```

### Scenario: day 字段正确关联方案进度
```gherkin
Given 用户已完成 day-N 打卡
When 用户上传时光相册照片
Then photo includes day field indicating plan day
And day is provided by plan service
And day is between 1 and 21
```

### Scenario: 设置照片为私密
```gherkin
Given 用户上传照片
When 用户设置隐私为"私密"
Then 照片仅自己可见
And PUT /album/photos/{id} 更新 privacy='private'
And 照片不出现在成长广场
```

### Scenario: 设置照片为公开
```gherkin
Given 用户上传照片
When 用户设置隐私为"公开"
Then 照片对所有人可见
And PUT /album/photos/{id} 更新 privacy='public'
And 照片可出现在成长广场（用户选择后）
```

---

## 六、合规约束

### Scenario: 不使用 AI 对比
```gherkin
Given 用户查看时光相册
Then 系统不提供任何 AI 对比功能
And 不展示任何雷达图
And 不出现任何照片对比功能
```

### Scenario: 不使用滑动手势
```gherkin
Given 用户查看时光相册
Then 时间轴不使用滑动手势
And 采用点击查看详情模式
And 不使用 swipe / slide / flick 手势
```

### Scenario: 不出现颜值打分
```gherkin
Given 用户查看时光相册
Then 任何界面不出现颜值打分
And 不出现任何评分机制
And 不出现分数/排名/对比数据
```

---

## 七、错误处理

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

## 八、ACK 连续不重复规则

### Scenario: 连续 3 条 feedback 不出现相同 ACK（M7-FR-02）
```gherkin
Given 用户连续提交多条 feedback
When 系统选择 ACK 回复
Then 连续 3 条 feedback 不出现相同 ACK
And 记录历史 ACK 避免近期重复
Example:
  | feedback # | ACK |
  | feedback_1 | "看到了，谢谢分享" |
  | feedback_2 | "你的感受很重要" |
  | feedback_3 | "嗯，我在这里" |
  | feedback_4 | # 不能重复前3条任意一条
```

### Scenario: ACK 生成性能要求（M7-FR-02）
```gherkin
Given 用户提交 feedback
When 系统处理提交
Then ACK 生成（规则匹配）P95 ≤ 500ms
And 含数据库写入总链路 P95 ≤ 3s
And ACK 文本来自 ACK_POOL（非 LLM 生成）
```

---

## 九、ACK 禁用词合规

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

---

## 九、引用说明

### 相关定义
- feedback定义：详见 [ATDD-Shared.md §二](../ATDD-Shared.md#二feedback-定义唯一真源m7m5m8共享)
- ACK禁用词：详见 [ATDD-Shared.md §三.2](../ATDD-Shared.md#三合规红线)
- 白名单定义：详见 [ATDD-Shared.md §十](../ATDD-Shared.md#十feedback-service-caller-白名单)
- 错误码定义：详见 [ATDD-Shared.md §四](../ATDD-Shared.md#四错误码字典)
- 用户旅程：详见 [ATDD-Journey.md §四](../ATDD-Journey.md#四反馈旅程)

---

## 十、修订历史

| 日期 | 版本 | 改动 |
|------|------|------|
| 2026-07-24 | V1.1 | 1. 修订 mood_photo 允许同时提交文字（PRD §1.5 对齐）<br>2. 列表页返回 photo_thumbnail_url（缩略图）<br>3. period_photo 新增独立入口（PRD §1.5 对齐）<br>4. 时光相册改为复用 feedback 表（删除 post 表复用设计）<br>5. 新增 ACK 连续 3 条不重复规则<br>6. ACK 性能量化（生成≤500ms/总链路≤3s） |
| 2026-07-21 | V1.0 | 初次创建，合并M7+M7-Album |
