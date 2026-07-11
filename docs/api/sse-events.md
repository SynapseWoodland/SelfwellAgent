# SSE 事件契约（Server-Sent Events）

> **来源**：PRD §5.1（AI 诊断流程有 8-15 秒等待）  
> **端点**：`GET /api/v1/diagnosis/{id}/stream`  
> **Content-Type**：`text/event-stream`  
> **鉴权**：Bearer JWT（同 `openapi.yaml`）  
> **心跳**：每 15 秒发送注释行 `: heartbeat`

---

## 1. 概述

诊断流程为**异步处理**，客户端发起诊断后需订阅 SSE 流获取实时进度。SSE 流包含从握手到最终结果的完整生命周期事件。

### 1.1 完整事件流

```
[客户端]
    │
    │  POST /api/v1/diagnosis        （获取 diagnosis_id）
    │
    │  GET /api/v1/diagnosis/{id}/stream
    ▼
┌─────────────────────────────────────────────────────────┐
│  [服务器端] SSE 流事件顺序                              │
│                                                         │
│  1. connected        ← 握手确认                         │
│  2. processing       ← 开始处理                         │
│  3. image_validated  ← 图像预处理完成                   │
│  4. llm_calling      ← LLM 调用中                       │
│  5. compliance_check ← 合规审查中                       │
│  6. progress (×N)    ← 进度更新（多次）                 │
│  7. result           ← 最终结果（成功）                  │
│     ── 或 ──                                       │
│  7. fallback         ← 降级结果（LLM 不可用）           │
│     ── 或 ──                                       │
│  7. error            ← 处理失败                        │
│  8. done             ← 流结束                           │
│                                                         │
│  [15s]  : heartbeat （心跳注释行，贯穿全程）            │
└─────────────────────────────────────────────────────────┘
```

### 1.2 诊断阶段耗时预算（PRD §7.2）

| 阶段 | 预计耗时 | 累计上限 |
|------|----------|----------|
| 图像预处理 | ≤ 2s | 2s |
| LLM 调用 | ≤ 15s | 17s |
| 合规审查 | ≤ 3s | 20s |
| **P95 总耗时** | — | **≤ 20s** |

---

## 2. 事件类型详解

### 2.1 `connected` — 握手确认

**说明**：SSE 连接建立成功，表示流已开启。

**触发时机**：服务器收到 GET 请求并验证 JWT 通过后。

**event 字段**：`connected`

**data 格式**：

```json
{
  "sid": "abc123xyz",
  "diagnosis_id": "rpt_001",
  "timestamp": "2026-07-05T12:00:00.000Z",
  "expires_at": "2026-07-05T12:00:30.000Z"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `sid` | string | SSE 会话 ID |
| `diagnosis_id` | string | 诊断 ID |
| `timestamp` | ISO8601 | 服务器当前时间 |
| `expires_at` | ISO8601 | 预计流结束时间（P95 ≤ 20s + 10s buffer） |

**前端处理建议**：

```javascript
// 微信小程序
const eventSource = wx.connectSocket({
  url: 'wss://api.selfwell.app/api/v1/diagnosis/rpt_001/stream',
  header: { Authorization: `Bearer ${token}` }
});

eventSource.onMessage(({ data }) => {
  const event = data.match(/^event: (\w+)/)?.[1];
  const payload = JSON.parse(data.match(/^data: (.+)/)?.[1] || '{}');

  if (event === 'connected') {
    console.log('SSE 连接成功，诊断 ID:', payload.diagnosis_id);
  }
});
```

---

### 2.2 `processing` — 开始处理

**说明**：服务器开始处理诊断请求。

**触发时机**：图像上传完成，开始预处理。

**event 字段**：`processing`

**data 格式**：

```json
{
  "stage": "preprocessing",
  "message": "正在处理您上传的照片...",
  "percent": 5,
  "timestamp": "2026-07-05T12:00:01.000Z"
}
```

**前端处理建议**：

- 显示加载动画（如旋转的 "自愈" logo）
- 显示文案："正在分析您的照片..."
- 进度条初始值 5%

---

### 2.3 `image_validated` — 图像预处理完成

**说明**：3 张照片已完成解码、压缩、格式校验。

**触发时机**：图像预处理成功，验证通过。

**event 字段**：`image_validated`

**data 格式**：

```json
{
  "validated": true,
  "photos_count": 3,
  "photo_urls": [
    "https://cdn.selfwell.app/diagnosis/rpt_001/photo_1.jpg",
    "https://cdn.selfwell.app/diagnosis/rpt_001/photo_2.jpg",
    "https://cdn.selfwell.app/diagnosis/rpt_001/photo_3.jpg"
  ],
  "message": "照片验证通过，正在发送给 AI...",
  "percent": 25,
  "timestamp": "2026-07-05T12:00:02.000Z"
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `validated` | boolean | 验证结果 |
| `photos_count` | integer | 有效照片数量（1-3） |
| `photo_urls` | string[] | CDN 回显 URL |

**前端处理建议**：

- 显示预处理后的照片缩略图（让用户确认上传正确）
- 更新文案："照片验证通过，正在分析..."
- 进度条更新至 25%

---

### 2.4 `llm_calling` — LLM 调用中

**说明**：开始调用 AI 诊断模型（Claude Sonnet / GPT-4o）。

**触发时机**：图像数据已发送给 LLM，等待响应。

**event 字段**：`llm_calling`

**data 格式**：

```json
{
  "model": "claude-sonnet-4-20250514",
  "message": "AI 正在分析您的面部、体态和发质状态...",
  "percent": 40,
  "estimated_remaining_seconds": 12,
  "timestamp": "2026-07-05T12:00:03.000Z"
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `model` | string | 本次调用的 LLM 模型名称 |
| `estimated_remaining_seconds` | integer | 预计剩余等待秒数 |

**前端处理建议**：

- 显示文案："AI 正在诊断中..."
- 显示 LLM 模型名称（透明化，建立信任）
- 进度条更新至 40%
- 显示预计剩余时间

---

### 2.5 `compliance_check` — 合规审查中

**说明**：AI 诊断完成后，进入合规审查（敏感词 + 医疗词汇 + 功效承诺过滤）。

**触发时机**：LLM 返回诊断结果，开始合规校验。

**event 字段**：`compliance_check`

**data 格式**：

```json
{
  "stage": "compliance_review",
  "message": "正在进行内容安全审查...",
  "percent": 80,
  "timestamp": "2026-07-05T12:00:15.000Z"
}
```

**前端处理建议**：

- 更新文案："内容安全审查中..."
- 进度条更新至 80%

---

### 2.6 `progress` — 进度更新

**说明**：通用进度更新事件，在任意阶段可多次触发。

**触发时机**：处理过程中随时可推送。

**event 字段**：`progress`

**data 格式**：

```json
{
  "percent": 60,
  "message": "AI 正在分析面部状态...",
  "stage": "llm_analysis",
  "timestamp": "2026-07-05T12:00:08.000Z"
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `percent` | integer | 当前进度百分比（0-100） |
| `message` | string | 进度描述文案 |
| `stage` | string | 当前阶段标识 |

**前端处理建议**：

- 根据 `percent` 更新进度条
- 根据 `message` 更新文案
- 阶段指示器高亮对应步骤

---

### 2.7 `result` — 最终结果（成功）

**说明**：诊断成功完成，返回完整诊断报告。

**触发时机**：LLM 返回 + 合规审查通过。

**event 字段**：`result`

**data 格式**：

```json
{
  "id": "rpt_001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "photos": [
    "https://cdn.selfwell.app/diagnosis/rpt_001/photo_1.jpg",
    "https://cdn.selfwell.app/diagnosis/rpt_001/photo_2.jpg",
    "https://cdn.selfwell.app/diagnosis/rpt_001/photo_3.jpg"
  ],
  "directions": [
    "肩颈放松：每日 10 分钟针对性拉伸",
    "晨间消肿：早起面部淋巴按摩 3 分钟",
    "体态矫正：圆肩改善每日跟练"
  ],
  "tags": [
    "圆肩", "晨起浮肿", "肩颈僵硬", "轻度头前伸",
    "眼周疲劳", "面部血液循环不畅", "气色偏暗"
  ],
  "recommended_video_ids": ["v001", "v003", "v007"],
  "llm_cost": 0.12,
  "llm_model": "claude-sonnet-4-20250514",
  "created_at": "2026-07-05T12:00:18.000Z",
  "cached_until": "2026-07-12T12:00:00.000Z"
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `directions` | string[] | 3-5 条改善方向（facts-anchor §4） |
| `tags` | string[] | 7-14 个诊断标签（facts-anchor §4） |
| `recommended_video_ids` | string[] | 推荐视频 ID 列表 |
| `llm_cost` | decimal | LLM 调用成本（元） |
| `cached_until` | ISO8601 | 报告缓存截止时间（7 天后） |

**前端处理建议**：

- 停止进度动画
- 展示诊断报告页面：
  - 显示 3-5 条改善方向
  - 显示诊断标签
  - 显示推荐视频卡片
- 弹出"诊断完成"提示
- 自动进入方案生成引导

---

### 2.8 `fallback` — 降级结果

**说明**：LLM 服务不可用，降级到规则引擎，返回标准方案。

**触发时机**：LLM API 限流/超时/不可用时，规则引擎兜底。

**event 字段**：`fallback`

**data 格式**：

```json
{
  "id": "rpt_fallback_001",
  "fallback": true,
  "fallback_reason": "llm_timeout",
  "directions": [
    "肩颈放松",
    "面部舒缓",
    "体态矫正"
  ],
  "tags": ["久坐人群", "肩颈不适"],
  "recommended_video_ids": ["v001", "v002"],
  "message": "AI 服务繁忙，已为您匹配标准养护方案",
  "llm_cost": 0.0,
  "created_at": "2026-07-05T12:00:18.000Z"
}
```

**降级话术库**：30 条轮换（facts-anchor §9）

**前端处理建议**：

- 显示诊断结果（同 `result`）
- 底部显示提示文案（来自 `message` 字段）
- 可选：提示用户稍后可重新诊断获取个性化方案

---

### 2.9 `error` — 处理失败

**说明**：诊断处理过程中发生错误。

**触发时机**：图像预处理失败 / LLM 调用失败 / 合规审查失败等。

**event 字段**：`error`

**data 格式**：

```json
{
  "error_code": "E_DIAGNOSIS_IMAGE_PROCESSING_FAILED",
  "message_zh": "图片预处理失败，请换张照片重试",
  "message_en": "Image preprocessing failed, please try another photo",
  "retryable": true,
  "timestamp": "2026-07-05T12:00:10.000Z"
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `error_code` | string | 错误码（引用 `error-codes.md`） |
| `message_zh` | string | 中文错误信息 |
| `retryable` | boolean | 是否可重试（true=引导重试，false=需用户操作） |

**前端处理建议**：

- 停止进度动画
- 显示错误提示弹窗
- 根据 `retryable` 决定下一步：
  - `true`：显示"重试"按钮
  - `false`：显示"联系客服"或具体操作指引
- 错误码记录日志用于排查

---

### 2.10 `done` — 流结束

**说明**：SSE 流正常结束（所有事件发送完毕后）。

**触发时机**：最终事件（`result`/`fallback`/`error`）发送后。

**event 字段**：`done`

**data 格式**：

```json
{
  "total_duration_ms": 18230,
  "final_percent": 100,
  "event_count": 8,
  "timestamp": "2026-07-05T12:00:18.500Z"
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_duration_ms` | integer | 总耗时（毫秒） |
| `event_count` | integer | 本次流发送的事件总数 |

**前端处理建议**：

- 关闭 SSE 连接
- 记录诊断耗时用于性能监控
- 诊断完成，进入方案生成引导流程

---

## 3. 心跳机制

### 3.1 心跳规则

- **间隔**：每 15 秒发送一次
- **格式**：注释行（不触发 `onMessage`）

```
: heartbeat
```

### 3.2 前端心跳处理

```javascript
// 心跳计数器：如果 15s 内未收到任何事件，断开连接重试
let lastEventTime = Date.now();

eventSource.onMessage(({ data }) => {
  if (data.startsWith(':')) return; // 忽略心跳注释行

  lastEventTime = Date.now();
  handleEvent(data);
});

// 心跳检测
setInterval(() => {
  if (Date.now() - lastEventTime > 30000) {
    console.warn('SSE 心跳超时，断开连接');
    eventSource.close();
    // 重试逻辑
  }
}, 10000);
```

---

## 4. 连接管理与重试

### 4.1 重试策略

| 场景 | 策略 |
|------|------|
| 连接断开（未收到 `done`） | 指数退避重试（1s → 2s → 4s → 8s → 16s），最多 3 次 |
| 诊断已完成（收到 `done`） | 不重试，连接正常关闭 |
| 收到 `error` 且 `retryable=true` | 提示用户点击重试，不自动重试 |
| 收到 `error` 且 `retryable=false` | 提示具体操作，不重试 |

### 4.2 前端 SSE 管理示例

```javascript
class DiagnosisStream {
  constructor(token) {
    this.token = token;
    this.retryCount = 0;
    this.maxRetries = 3;
  }

  connect(diagnosisId) {
    const url = `wss://api.selfwell.app/api/v1/diagnosis/${diagnosisId}/stream`;

    this.source = wx.connectSocket({ url, header: {
      Authorization: `Bearer ${this.token}`
    }});

    this.source.onOpen(() => console.log('SSE 连接已建立'));
    this.source.onMessage(this.handleMessage.bind(this));
    this.source.onClose(this.handleClose.bind(this));
    this.source.onError(this.handleError.bind(this));
  }

  handleMessage({ data }) {
    if (data.startsWith(':')) return; // 心跳

    const event = data.match(/^event: (\w+)/)?.[1];
    const payload = JSON.parse(data.match(/^data: (.+)/)?.[1] || '{}');

    switch (event) {
      case 'connected': this.onConnected(payload); break;
      case 'processing': this.onProcessing(payload); break;
      case 'result': this.onResult(payload); break;
      case 'fallback': this.onFallback(payload); break;
      case 'error': this.onError(payload); break;
      case 'done': this.onDone(payload); break;
    }
  }

  close() {
    this.source?.close();
  }
}
```

---

## 5. 鉴权与安全

### 5.1 JWT 鉴权

SSE 连接使用与 REST API 相同的 Bearer JWT Token：

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 5.2 Token 过期处理

- 连接建立时验证 Token
- Token 过期后连接自动断开
- 前端收到 `401` 后跳转登录页

---

## 6. 响应头规范

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
Transfer-Encoding: chunked
```

| 响应头 | 说明 |
|--------|------|
| `Content-Type: text/event-stream` | SSE 必须 |
| `Cache-Control: no-cache` | 禁用缓存 |
| `Connection: keep-alive` | 保持连接 |
| `X-Accel-Buffering: no` | 关闭 Nginx 缓冲（确保实时） |

---

## 7. 完整事件序列示例

```
event: connected
data: {"sid":"abc123","diagnosis_id":"rpt_001","timestamp":"2026-07-05T12:00:00.000Z","expires_at":"2026-07-05T12:00:30.000Z"}

: heartbeat

event: processing
data: {"stage":"preprocessing","message":"正在处理您上传的照片...","percent":5,"timestamp":"2026-07-05T12:00:00.500Z"}

event: progress
data: {"percent":15,"message":"正在验证图片格式...","stage":"image_validation"}

event: image_validated
data: {"validated":true,"photos_count":3,"message":"照片验证通过，正在发送给 AI...","percent":25,"timestamp":"2026-07-05T12:00:02.000Z"}

event: progress
data: {"percent":35,"message":"正在连接 AI 服务...","stage":"llm_connecting"}

event: llm_calling
data: {"model":"claude-sonnet-4-20250514","message":"AI 正在分析您的面部、体态和发质状态...","percent":40,"estimated_remaining_seconds":12}

: heartbeat

event: progress
data: {"percent":55,"message":"AI 正在分析面部状态...","stage":"llm_analysis_face"}

event: progress
data: {"percent":65,"message":"AI 正在分析体态...","stage":"llm_analysis_posture"}

event: progress
data: {"percent":75,"message":"AI 正在生成改善方案...","stage":"llm_generating"}

event: compliance_check
data: {"stage":"compliance_review","message":"正在进行内容安全审查...","percent":80}

event: result
data: {"id":"rpt_001","directions":["肩颈放松","晨间消肿"],"tags":["圆肩","浮肿","肩颈僵硬"],"llm_cost":0.12,"created_at":"2026-07-05T12:00:18.000Z"}

event: done
data: {"total_duration_ms":18230,"final_percent":100,"event_count":8,"timestamp":"2026-07-05T12:00:18.500Z"}
```

---

> **§5 ~ §6 段为 V5.2.1-PR3 追加**（assistant 域 SSE 契约），与 §1 ~ §4 diagnosis 域并列。
> 端点不同、schema 独立，不覆盖既有 diagnosis 域契约。
> 代码真源：`backend/app/api/routers/assistant_v1.py:113-117` SSE schema docstring。

---

## §5 · assistant 域 SSE 契约（V5.2.1-PR3 追加）

**端点**：`POST /api/v1/assistant/sessions/{session_id}/messages`（SSE StreamingResponse）

**模式路由**：
- `image_keys` 非空 → smart_analyze 模式
- `image_keys` 为空 → chat 模式（token_delta 流）

### §5.1 chat 模式（V5.2.1 §3.7）

```
event: start
data: {"step": 0}

event: token_delta
data: {"token": "你"}

event: token_delta
data: {"token": "好"}

event: end
data: {"ok": true,
       "reply": "你好，今天感觉怎么样？",
       "persona_state": "warm",
       "is_quick_reply": false,
       "level": null,
       "medical_guarded": false,
       "is_mock": false}
```

### §5.2 smart_analyze 模式

```
event: start
data: {"step": 0}

event: progress
data: {"step": 1, "percent": 15, "label": "图片校验中"}

event: progress
data: {"step": 2, "percent": 45, "label": "正在分析体态"}

event: progress
data: {"step": 3, "percent": 75, "label": "生成养护建议"}

event: progress
data: {"step": 4, "percent": 100, "label": "分析完成"}

event: report
data: {"directions": [
         {"title": "肩颈放松",
          "description": "1. ...",
          "video_id": "vid_xxx",
          "level": "中度"}, ...],
       "tags": ["圆肩", "浮肿"],
       "summary": "..."}

event: progress
data: {"step": 5, "percent": 100, "label": "已就绪"}

event: end
data: {"ok": true,
       "reply": "基于你的照片，我为你生成了 N 条养护建议...",
       "persona_state": "warm",
       "is_mock": false,
       "medical_guarded": false,
       "is_quick_reply": false,
       "level": "中度"}

event: error  （可选，异常时下发，不阻塞流）
data: {"code": "E_ASSISTANT_LLM_ERROR",
       "message_zh": "智能分析暂时不可用",
       "message_en": "Smart analyze temporarily unavailable",
       "request_id": "abc123..."}
```

### §5.3 end 事件 7 字段 schema 真源（V5.2.1 §3.6 T19）

| 字段 | 类型 | 说明 |
|------|------|------|
| `ok` | `bool` | 流是否完成（`false` → 异常分支） |
| `reply` | `str` | 智能管家最终回复文本（fallback 模板兜底） |
| `persona_state` | `str` | 切换后的 persona state（from `_next_state`） |
| `is_mock` | `bool` | 是否走 rule-engine fallback（smart_analyze 模式） |
| `medical_guarded` | `bool` | 是否触发 medical_reject 兜底（PR4 才赋真值，前置 `false`） |
| `is_quick_reply` | `bool` | 是否走 ack_pool 兜底（chat 模式） |
| `level` | `str \| null` | 主要方向严重度（"轻度"/"中度"/"重度"），PR2 T13 Pydantic 提供。chat 模式默认 `null` |

### §5.4 progress 事件字段契约（真源 `assistant_v1.py:115`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `step` | `int` | 阶段序号 0..5（start=0，progress=1..5，end 不带 step）|
| `percent` | `int` | 进度百分比 0..100 |
| `label` | `str` | 阶段中文标签（如 "图片校验中"、"分析完成"、"已就绪"）|

### §5.5 错误事件 schema

```
event: error
data: {"code": "E_ASSISTANT_*",
       "message_zh": "...",
       "message_en": "...",
       "request_id": "..."}
```

错误码真源：`backend/app/errors/codes.py`。常用：
- `E_ASSISTANT_LLM_ERROR`（智能分析 LLM 失败）
- `E_ASSISTANT_RATE_LIMIT`（限流，PR-F.2 已上）
- `E_ASSISTANT_SESSION_NOT_FOUND`（404，跳出 SSE 流）
- `E_ASSISTANT_SESSION_CLOSED`（410，跳出 SSE 流）
- `E_ASSISTANT_CONCURRENT_MESSAGE`（并发消息冲突）
- `E_ASSISTANT_MEDICAL_REJECT`（smart_analyze medical_reject 短路，PR4 引入；流停在 error 帧，不发后续 progress/report/end）

### §5.6 fallback 协议（V5.2.1-PR4 F4 追加）

**触发条件**：vision LLM 调用失败或超时（`diagnosis_service._invoke_llm_structured` 走 `_rule_engine_fallback` 降级路径）。

**end event payload 增量字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `is_fallback` | `bool` | `true` = 当前是规则引擎兜底，不是 LLM 真实生成 |
| `fallback_reason` | `str` | 兜底原因（V5.2.1-PR4 固定 `"资料不足"`） |

**示例**：
```
event: end
data: {"ok": true,
       "reply": "基于你的照片，我为你生成了 0 条养护建议，可以看看。",
       "persona_state": "neutral",
       "is_mock": true,
       "medical_guarded": false,
       "is_quick_reply": false,
       "level": "轻度",
       "is_fallback": true,
       "fallback_reason": "资料不足"}
```

**前端处理**：
- `is_fallback=true` 时**不渲染 report card**（directions/tags 为空，渲染会显示空态）
- 引导用户去 `pages/profile/index` 补档案 + 去 `pages/smart-analyze-upload/index` 补图
- 复用 §5.2 的 `summary` 字段（"请先补充档案与图片后再进行智能分析。"）作为 toast 文案

**真源**：
- 后端：`backend/app/services/diagnosis_service.py:_rule_engine_fallback` (return dict) + `backend/app/services/assistant_service.py:_stream_smart_analyze` (end_payload 透传)
- 测试：`backend/tests/unit/services/test_vision_fallback_personalize.py`（5 个契约测试）

## §6 · 与 §1 ~ §4 diagnosis 域契约的关系

- §1 ~ §4：`/api/v1/diagnosis/{id}/stream`（diagnosis 域，前置契约）
- §5：`/api/v1/assistant/sessions/{session_id}/messages`（assistant 域，V5.2.1 追加）

两端 schema **独立**；不互通。
共用 Prometheus 命名空间 `selfwell_*`（如 `selfwell_llm_cost_yuan_total`）。

---

**文档版本**：v1.1 + V5.2.1-PR3 §5  
**基于**：V5.0 §6 + V5.2.1 §3.5/§3.6 + SPEC-V521-PR3-sse-cost-adr.md  
**参考**：`docs/api/openapi.yaml` / `docs/adr/0007-vision-pipeline-split.md` §2.5 / `backend/app/api/routers/assistant_v1.py:113-117`
