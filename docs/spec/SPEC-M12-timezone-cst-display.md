# SPEC-M12: 全链路时区统一（UTC 存储 · Asia/Shanghai 显示）

> **版本**: V1.0（draft）
> **日期**: 2026-07-14
> **依赖文档**: `facts-anchor.md` (§6 §17.10)、`docs/data/data-dictionary.md` (§1.10 ai_sessions, §1.11 ai_messages)、`docs/api/openapi.yaml` V1.1.0
> **模块编号**: M12（横切能力 · 全链路时区基线）
> **状态**: Draft → 待 Backend / Frontend 双 Agent 评审
> **已对齐**: facts-anchor.md V2.0 + openapi.yaml V1.1.0

---

> **IA-REF**: 本 SPEC 是横切基线，不绑定单一 IA 页面；覆盖 `assistant-home`、`home (today tab)`、`feedback-diary`、`recall-flow`、`album`、`checkin` 等所有时间显示点位。

---

## 0. 术语对齐

| 术语 | 定义 | 备注 |
|------|------|------|
| UTC | 数据库与服务端唯一权威时区 | TIMESTAMPTZ 内部存储 |
| Asia/Shanghai (CST, UTC+8) | 前端**显示**唯一权威时区 | 与事实基线 §6 "北京时间" 一致 |
| Client TZ | 客户端设备时区（任意） | 仅用于 `Intl.DateTimeFormat` 内置转换，**不再作为显示锚点** |
| Display TZ | 前端格式化时显式指定的时区 | 全链路固定 `Asia/Shanghai` |

---

## 1. 模块概述

| 维度 | 内容 |
|------|------|
| **一句话定义** | 把"DB / API / 前端"三层时区锚点统一为 **"DB 存 UTC、API 透传 UTC ISO、前端恒显 Asia/Shanghai"**，并在 `assistant-home` 聊天气泡新增 **消息时间戳** |
| **上线顺序** | 横切（无独立 W）—— 建议 W3 与 PR-V2-D 同步合入 |
| **前置依赖** | M5（persona-chat · assistant-home 聊天框） |
| **关联模块** | M4（checkin）、M7（feedback-diary）、M8（recall-flow）、M10（share-card · 海报时间） |

---

## 2. 现状摸底（事实层 · 已 100% 核对）

### 2.1 DB 层（✅ 已合规）

| 维度 | 现状 | 评估 |
|------|------|------|
| 数据库 | PostgreSQL（端口 5432，`postgresql+asyncpg`） | ✅ |
| 时间列类型 | 全部 `TIMESTAMP(timezone=True)`（= `TIMESTAMPTZ`） | ✅ |
| 内部存储 | UTC（TIMESTAMPTZ 原生行为） | ✅ |
| Python 生成 | 全部 `datetime.now(UTC)`，零次 `datetime.utcnow()`、零次 `datetime.now()` 无参 | ✅ |
| 唯一例外 | `plans.started_at` / `plans.completed_at` 用 `DATE` 类型（仅日期，无时区） | ✅ 无需处理 |
| server_default | 仅 `0007_add_v2_ia_tables.py` 部分字段带 `server_default=sa.text("NOW()")` | ✅ UTC |

### 2.2 API 层（✅ 已合规）

| 维度 | 现状 | 评估 |
|------|------|------|
| 序列化 | 全部手动 `.isoformat()` → ISO 8601 字符串 | ✅ |
| 格式示例 | `"2026-07-14T08:30:00+00:00"`（带 `+00:00` UTC 标识） | ✅ |
| Pydantic schema | 时间字段类型为 `str`，未走 `datetime` 自动序列化（避免丢失 tz） | ✅ |
| 自定义 encoder | 无 | ✅ 不需要 |

### 2.3 前端层（❌ 不合规 · 根因所在）

| 维度 | 现状 | 评估 |
|------|------|------|
| 时间解析 | `new Date(isoString)` 依赖浏览器/小程序内置解析 → 转设备本地时区 | ⚠️ |
| 时间格式化 | `getHours()` / `getMonth()` / `getDate()` 等本地方法 | ❌ 跨时区失真 |
| `toISOString().slice(0,10)` | 取 UTC 日期（`home/index.ts:434`、`checkin/index.ts:117`） | ❌ 跨时区可能"日期错位" |
| `formatDate()` | `recall-flow/index.ts:86-97` 用本地 `getFullYear()` 等 | ⚠️ |
| 智能管家聊天框 | **`ChatTurn` 只有 `state + text`，不显示时间戳** | ❌ 缺失 |
| 统一时间工具 | **无 `utils/time.ts`** | ❌ 缺失 |

### 2.4 根因定位

> **结论：DB 与 API 均已合规，"不是北京时间"的根因在**前端显示层**——前端用设备本地时区格式化，且聊天框没有时间戳。**

跨时区典型 case：

```
设备时区: Asia/Tokyo (UTC+9)
后端返回: "2026-07-14T08:30:00+00:00"  (UTC)
前端 new Date() 后: 2026-07-14 17:30 JST
前端 getHours(): 17
→ 期望 16:30（北京时间），实际 17:30，差 1 小时
```

---

## 3. 设计目标（验收口径）

| # | 目标 | 验收 |
|---|------|------|
| G1 | DB 存储语义不变：保持 UTC | alembic head + 表结构复核 `TIMESTAMPTZ` |
| G2 | API 契约不变：仍返回 ISO 8601 字符串 + `+00:00` | OpenAPI schema diff = 0 |
| G3 | 前端**所有时间格式化**统一走 `Asia/Shanghai` | 设备切 Tokyo / LA 时显示不变 |
| G4 | `assistant-home` 聊天气泡显示消息时间戳（HH:mm / 跨日 MM-DD HH:mm） | 视觉基线截图 |
| G5 | 任何前端代码**禁止**调用 `new Date().toISOString().slice(0,10)` 取业务日期 | grep 规则 |
| G6 | 任何后端代码**禁止**调用 `datetime.now()`（无参）/ `datetime.utcnow()` | ruff 自定义规则 / grep CI |

---

## 4. 方案设计（三层时区锚点 + 1 个新增 UI）

### 4.1 三层时区锚点

```
┌──────────────────────────────────────────────────────────────────┐
│ Layer 1 · DB（不变）                                              │
│   • TIMESTAMPTZ 内部存 UTC                                        │
│   • 任何 server_default = NOW() 也是 UTC                          │
├──────────────────────────────────────────────────────────────────┤
│ Layer 2 · API（不变）                                             │
│   • .isoformat() 返回 ISO 8601 + "Z" 标识（强制 UTC）             │
│   • 不引入二次转换、不暴露 tz_offset 给前端                       │
├──────────────────────────────────────────────────────────────────┤
│ Layer 3 · Frontend（新增强制统一）                                │
│   • 唯一时区锚点: Asia/Shanghai（UTC+8）                          │
│   • 唯一入口: utils/time.ts（mp-selfwell + flutter_app）           │
│   • 格式化函数全部基于"先把 ISO 转 UTC Date 对象，再 .toLocaleString(               │
│     { timeZone: 'Asia/Shanghai', ... })"                          │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 后端零改动（验收口径：API 契约冻结）

- ❌ 不引入二次 `.astimezone()` 转换（避免双重时区偏移 bug）
- ❌ 不改 `assistant_service.py:1476` 的 `.isoformat()`（已正确）
- ❌ 不引入 `app/core/timezone.py`（已统一 `datetime.now(UTC)`，无需抽工具）
- ✅ **可选增强**：为防御性，新增 `backend/app/core/timezone.py`（详见 §5.1），仅作为 `_utcnow()` 单一来源替换，不改变语义

### 4.3 前端统一时间工具（核心新增）

#### 4.3.1 新建 `apps/mp-selfwell/miniprogram/utils/time.ts`

```ts
// 单文件、纯函数、零依赖、强类型
export const DISPLAY_TZ = 'Asia/Shanghai';

/** ISO 字符串 → UTC Date 对象（兼容 "Z" / "+00:00" / "+08:00"） */
export function parseUtc(iso: string): Date {
  // ISO 8601: 微信小程序/JS 均原生支持 Date 解析
  // 关键：Date 内部统一存 UTC，format 阶段再切换到 Asia/Shanghai
  return new Date(iso);
}

/** Date → "HH:mm"（Asia/Shanghai） */
export function formatHM(d: Date | string): string {
  const date = typeof d === 'string' ? parseUtc(d) : d;
  return date.toLocaleString('en-GB', {
    timeZone: DISPLAY_TZ, hour: '2-digit', minute: '2-digit', hour12: false,
  });
}

/** Date → "YYYY-MM-DD HH:mm"（Asia/Shanghai） */
export function formatDateTime(d: Date | string): string {
  const date = typeof d === 'string' ? parseUtc(d) : d;
  const pad = (n: number) => String(n).padStart(2, '0');
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: DISPLAY_TZ,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  });
  // en-CA 默认格式 YYYY-MM-DD, HH:MM
  return fmt.format(date).replace(',', '');
}

/** Date → "MM月DD日"（Asia/Shanghai） */
export function formatMd(d: Date | string): string {
  const date = typeof d === 'string' ? parseUtc(d) : d;
  const fmt = new Intl.DateTimeFormat('zh-CN', {
    timeZone: DISPLAY_TZ, month: 'long', day: 'numeric',
  });
  return fmt.format(date);
}

/** "今天 / 昨天 / MM-DD HH:mm / YYYY-MM-DD HH:mm"（Asia/Shanghai） */
export function formatChatTime(d: Date | string): string {
  const date = typeof d === 'string' ? parseUtc(d) : d;
  const now = new Date();
  // 拿到北京时间下的 yyyy/mm/dd 字符串
  const dayKey = (dt: Date) =>
    new Intl.DateTimeFormat('en-CA', {
      timeZone: DISPLAY_TZ, year: 'numeric', month: '2-digit', day: '2-digit',
    }).format(dt);
  const todayKey = dayKey(now);
  const msgKey = dayKey(date);
  if (msgKey === todayKey) return formatHM(date);              // 今天：HH:mm
  // 昨天判定
  const yesterday = new Date(now.getTime() - 24 * 3600 * 1000);
  if (msgKey === dayKey(yesterday)) return `昨天 ${formatHM(date)}`;
  // 跨年判定
  const yyyy = new Intl.DateTimeFormat('en-CA', {
    timeZone: DISPLAY_TZ, year: 'numeric',
  }).format(date);
  const thisYear = new Intl.DateTimeFormat('en-CA', {
    timeZone: DISPLAY_TZ, year: 'numeric',
  }).format(now);
  if (yyyy !== thisYear) return formatDateTime(date);
  return `${msgKey} ${formatHM(date)}`;
}

/** "今天"在 Asia/Shanghai 下的 YYYY-MM-DD（用于业务日期参数） */
export function todayInCST(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: DISPLAY_TZ, year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date());
}
```

#### 4.3.2 Flutter 端镜像实现

新建 `apps/flutter_app/lib/core/time/time_x.dart`，提供同 API 集（`formatHM` / `formatDateTime` / `formatMd` / `formatChatTime` / `todayInCST`），实现用 `intl` 包的 `DateFormat.yMd('zh_CN').add_jm()` + `DateTime.now().toUtc().add(Duration(hours: 8))` 双轨方案，**避免依赖系统时区**。

### 4.4 智能管家聊天框时间戳（新增 UI）

#### 4.4.1 数据契约扩展

后端 `assistant_service.py:1476` 当前返回 `created_at`（ISO 8601 UTC）。前端 `ChatTurn` 增加字段：

```ts
// apps/mp-selfwell/miniprogram/pages/assistant-home/index.ts
interface ChatTurn {
  id: string;
  state: PersonaState;
  text: string;
  title?: string;
  /** v2.1 · 后端 ISO 8601 UTC 时间戳；前端统一按 Asia/Shanghai 显示 */
  createdAt?: string;
}
```

#### 4.4.2 写入时机

- **用户消息**（`onSend`）：本地 `new Date().toISOString()` 写入 `createdAt`
- **后端消息**（`runChatStream` 接收 `start` 事件时）：从 SSE `data.created_at` 字段读
- **兜底**：历史 sessions 通过 `/assistant/sessions/{id}/messages` 拉取列表时回填（详见 §5.4）

#### 4.4.3 UI 渲染

```xml
<!-- assistant-home/index.wxml -->
<view class="assistant-turn" wx:for="{{turns}}" wx:key="id" id="{{item.id}}">
  <persona-bubble
    state="{{item.state}}"
    text="{{item.text || ''}}"
    title="{{item.title || ''}}"
  />
  <!-- v2.1 新增：消息时间戳（Asia/Shanghai） -->
  <view class="assistant-turn-time" wx:if="{{item.createdAt}}">
    {{item.timeLabel}}
  </view>
</view>
```

`timeLabel` 由 `onSend` / SSE `applyAssistantEvent` 写入时同步计算（`formatChatTime(item.createdAt)`），避免每帧重算。

#### 4.4.4 视觉规格

| 元素 | 样式 | Token |
|------|------|-------|
| 时间戳位置 | 气泡下方居中（或左对齐） | 由 `persona-bubble` 组件决定 |
| 字号 | 11px | v2-token `--font-caption` |
| 颜色 | `#999` | v2-token `--color-text-tertiary` |
| 跨日提示 | "昨天 HH:mm" 加粗 | 视觉与 `feedback-diary` 现有日期标签一致 |

---

## 5. 实施步骤（PR 拆分建议）

### 5.1 PR-1 · Backend Hardening（防御性，可选）

| 文件 | 改动 | 原因 |
|------|------|------|
| `backend/app/core/timezone.py` | **新建**：`utcnow() -> datetime` 单一函数 | 防御未来误用 `datetime.now()` |
| `backend/app/services/assistant_service.py` 等 18 处 | `datetime.now(UTC)` → `utcnow()` | 统一入口 |
| `backend/tests/test_timezone.py` | **新建**：单元测试 + `ruff` 自定义规则 | L0 门禁 |

> **说明**：此 PR 不改任何接口语义，是防御性硬化。

### 5.2 PR-2 · Frontend Time Util（核心基建）

| 文件 | 改动 |
|------|------|
| `apps/mp-selfwell/miniprogram/utils/time.ts` | **新建**（§4.3.1 全量代码） |
| `apps/mp-selfwell/miniprogram/utils/time.spec.ts` | **新建**：vitest 单元测试（todayInCST 跨时区 case） |
| `apps/mp-selfwell/miniprogram/types/api.ts` | `ISODateTime` 加 JSDoc：`// 始终 UTC；前端用 utils/time.ts 格式化到 Asia/Shanghai` |
| `apps/mp-selfwell/miniprogram/pages/home/index.ts` | `new Date().getHours()` / `.toISOString().slice(0,10)` → `todayInCST()` |
| `apps/mp-selfwell/miniprogram/pages/checkin/index.ts` | 同上 |
| `apps/mp-selfwell/miniprogram/pages/feedback-diary/index.ts` | `_formatDate()` → `formatMd()` |
| `apps/mp-selfwell/miniprogram/pages/recall-flow/index.ts` | `formatDate()` → `todayInCST()` + `Intl.DateTimeFormat` |
| `apps/mp-selfwell/miniprogram/pages/album/index.ts` | 周历计算统一走 Asia/Shanghai |

### 5.3 PR-3 · Chat Bubble Timestamp（功能新增）

| 文件 | 改动 |
|------|------|
| `apps/mp-selfwell/miniprogram/components/persona-bubble/index.ts` | 增加 `timeText` prop |
| `apps/mp-selfwell/miniprogram/components/persona-bubble/index.wxml` | 渲染 `<view class="bubble-time">{{timeText}}</view>` |
| `apps/mp-selfwell/miniprogram/components/persona-bubble/index.wxss` | 新增 `.bubble-time` 样式（11px / #999 / 居中） |
| `apps/mp-selfwell/miniprogram/pages/assistant-home/index.ts` | `ChatTurn.createdAt` + `timeLabel`；`onSend` / `runChatStream` 写入 |
| `apps/mp-selfwell/miniprogram/pages/assistant-home/index.wxml` | 渲染 `{{item.timeLabel}}` |

### 5.4 PR-4 · 历史 Session 回填 + SSE 契约扩展

| 文件 | 改动 |
|------|------|
| `backend/app/services/assistant_service.py` | 消息列表返回结构已含 `created_at`（ISO），**无需改后端** |
| `backend/app/services/assistant_service.py` `_stream_chat` | `start` 事件 payload 增加 `created_at: datetime.now(UTC).isoformat()` |
| `apps/mp-selfwell/miniprogram/pages/assistant-home/index.ts` | SSE `start` 事件回调写入 `createdAt` + `timeLabel` |
| `apps/mp-selfwell/miniprogram/utils/sse-http.ts` | SseEvent 类型扩展（向后兼容） |

### 5.5 PR-5 · Flutter 镜像（可选延后）

| 文件 | 改动 |
|------|------|
| `apps/flutter_app/lib/core/time/time_x.dart` | **新建**（§4.3.2 镜像） |
| `apps/flutter_app/lib/pages/feedback/feedback_diary_page.dart` | 替换 `DateTime.now()` 时间格式化 |
| `apps/flutter_app/lib/pages/home/home_page.dart` | 替换时间显示 |
| `apps/flutter_app/lib/pages/diagnosis/report/diagnosis_report_page.dart` | 报告时间戳 |

### 5.6 PR-6 · 视觉基线 & 守护

| 文件 | 改动 |
|------|------|
| `apps/mp-selfwell/tests/visual-baseline/visual-baseline.spec.ts` | 新增 case `15j-assistant-home-chat-timestamp-chromium-win32.png` |
| `apps/mp-selfwell/tests/visual-baseline/__snapshots__/` | 新增基线截图 |
| `apps/mp-selfwell/scripts/visual-baseline-setup.js` | 设备切 Tokyo / LA 跑两遍，截图对比 |

---

## 6. 风险评估 & 兜底

| 风险 | 概率 | 影响 | 兜底 |
|------|------|------|------|
| `Intl.DateTimeFormat` 在低端微信基础库不可用 | 低 | 高 | 运行时探测 + 兜底 `formatChatTime` 用 `getUTC*` + 手工 +8 偏移 |
| `toLocaleString` 在 iOS WebView 表现差异 | 中 | 中 | 固定 `'en-CA'` / `'zh-CN'` locale，行为可预测 |
| 后端历史数据 `created_at` 缺失 | 极低 | 低 | 前端 `timeLabel` 兜底为空（`wx:if` 不渲染） |
| Flutter `intl` 包未引入 | 中 | 中 | PR-5 引入依赖（已声明于 `pubspec.yaml`） |
| 跨日边界（23:59:59 → 00:00:00 CST） | 低 | 低 | `formatChatTime` 用 `dayKey` 字符串比较而非 `Date.getDate()`，天然正确 |

---

## 7. 测试矩阵（PR-Gate）

| 测试类型 | 用例 | 期望 |
|---------|------|------|
| 单元 | `formatHM('2026-07-14T08:30:00+00:00')` | `'16:30'` |
| 单元 | `formatChatTime` 跨日（昨天） | `'昨天 23:30'` |
| 单元 | `formatChatTime` 跨年（去年 12-31） | `'2025-12-31 23:30'` |
| 单元 | `todayInCST()` 设备时区=Tokyo | 返回 Beijing 当天日期 |
| 集成 | 设备切 Tokyo，调 `GET /assistant/sessions/{id}/messages` | `created_at` 不变，显示层按 Beijing |
| 视觉 | `15j-assistant-home-chat-timestamp` | 气泡下方 HH:mm 居中 |
| E2E | Playwright `tests/video-url.test.ts` 时间字段断言 | ISO 字符串以 `+00:00` 结尾 |

---

## 8. 评审清单（PR-Gate 必勾）

- [ ] Backend Agent 评审 §4.2（确认后端零改动）
- [ ] Frontend Agent 评审 §4.3 / §4.4（API 兼容性）
- [ ] Security Agent 检查 `utils/time.ts` 无 `eval` / 无外链
- [ ] QA Agent 评审 §7 测试矩阵 + §5 PR 拆分
- [ ] DevOps Agent 评审 CI：lint 增加 `no-direct-date-format` 自定义规则
- [ ] 文案合规：`昨天` / `今天` / `HH:mm` 不触及 `forbidden-words.md`

---

## 9. 变更影响摘要

| 文件数 | 新增 | 修改 | 删除 |
|--------|------|------|------|
| Backend | 1（`core/timezone.py`）+ 1（test） | ~6（防御性替换） | 0 |
| Frontend (mp-selfwell) | 2（`utils/time.ts` + spec） + 1（visual baseline） | ~8（页面 + 组件） | 0 |
| Frontend (flutter_app) | 1（`core/time/time_x.dart`） | ~3 | 0 |
| **API 契约** | **0** | **0** | **0** |

**关键不变项**：OpenAPI V1.1.0 不动、DB schema 不动、所有现有测试基线不动。

---

## 10. 个人中心与数据合规

> **承接来源**：PRD V1.1 §1.9 用户账户 + 合规；S12 §3.2~§3.5

### 10.1 模块概述

| 维度 | 内容 |
|------|------|
| 一句话定义 | 用户在个人中心管理账户、查看数据、导出个人数据、申请注销 |
| 上线顺序 | W4 横切能力 |
| 前置依赖 | M1（极简登录） |
| 关联模块 | M14（合规） |

### 10.2 功能清单

#### 10.2.1 推送偏好管理
- 用户可设置 4 类推送开关（方案提醒 / 主动回忆 / 社区互动 / 活动推送）
- 微信服务通知需用户授权订阅（首次进入引导）

#### 10.2.2 数据导出
- 用户发起 → 后端异步打包（7 天内可下载）
- 导出格式：ZIP 包（含 JSON 数据 + 用户上传照片）
- TTL：7 天，过期失效

#### 10.2.3 账户注销
- 用户发起注销 → 15 天冷静期
- 冷静期内所有数据冻结，不可登录
- 用户可点击"恢复账户"撤销
- 冷静期结束：数据永久删除（用户数据 / Qdrant 向量 / MinIO 对象文件）

### 10.3 数据契约（TODO：字段待补充）

> **来源**：PRD V1.1 §1.9.3 / §1.9.4
> **TODO**：以下字段定义待从 PRD §4.1 T-P*-* 迁移

### 10.4 API 契约（TODO：端点待补充）

> **来源**：S12 §3.2 API 端点
> **TODO**：以下端点定义待从 S12 §3.2 迁移

| 端点 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `/api/v1/export` | POST | 发起数据导出 | TODO |
| `/api/v1/export/{job_id}` | GET | 查询导出状态 | TODO |
| `/api/v1/account/delete` | POST | 发起注销 | TODO |

### 10.5 合规要点（TODO：待填充）

> **来源**：PRD V1.1 §3 合规与隐私
> **TODO**：
> - 数据导出 ZIP 包的 GDPR 合规说明
> - 注销后数据永久删除的执行流程
> - safety_audit_logs 记录规范（危机事件不存对话内容、保留 90 天）

### 10.6 验收标准（TODO）

> **来源**：S12 §6 场景用例
> **TODO**：以下 AC 待从 S12 §6 迁移
