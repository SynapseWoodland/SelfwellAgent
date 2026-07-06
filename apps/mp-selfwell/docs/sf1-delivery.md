# SF1 完工报告（2026-07-06）

> 范围：**P00 启动 + P01 微信登录 + P02 首页（打卡）+ P05 打卡完成**
> 不在 scope：SF2~SF5（智能分析 / 智能管家 / 21 天方案 / 蜕变广场 / 推送 4 端 SDK）

## 1. 交付物

| 路径 | 状态 | 强约束满足 |
|------|------|----------|
| `miniprogram/utils/request.ts` | ✅ 已有（SF0 增量未改） | §17.7 Traceparent + JWT 拦截器，ApiException 类 |
| `miniprogram/utils/request.js` | ✅ 新增（plan §15.3 文档口径入口别名） | 同上 |
| `miniprogram/utils/sse.ts` | ✅ 已有 | §17.6 1s→2s→4s→8s→16s→30s 退避 |
| `miniprogram/utils/error-code.ts` | ✅ 新增 | 错误码 → 中文 toast 映射 |
| `miniprogram/utils/config.ts` | ✅ SF1 增量 | STORAGE_KEYS 扩 4 项 |
| `miniprogram/pages/splash/index.ts` | ✅ SF1 强化 | routed 锁 + jwt 长度/格式最小校验 |
| `miniprogram/pages/login/index.ts` | ✅ SF1 强化 | 错误码 → ERR_LABEL → toast |
| `miniprogram/pages/home/index.ts` | ✅ SF1 强化 | _inFlight 锁 + Promise.allSettled 单点容错 + streak clamp |
| `miniprogram/pages/checkin/index.ts` | ✅ SF1 强化 | packAck 页级 30 字截断 + onAckLongPress 长按 tooltip |
| `miniprogram/components/ack-bubble/index.ts` | ✅ 已有 | observers 二次截断 + onLongPress tooltip |
| `miniprogram/app.wxss` | ✅ 已有 | --mint/--cream/--ink-* 全局 CSS var + rpx 体系 |
| `tests/sf1-pages.test.js` | ✅ 新增 | 70 项强约束断言 |
| `tests/sf1/{splash,login,home,checkin}-screenshot.test.js` | ✅ 新增 | 4 个 page 静态渲染 stub（miniprogram-automator mock 形态） |
| `tests/check-forbidden-colors.js` | ✅ 新增 | 精确扫描（区分注释/文档） |

## 2. 强约束自检（§17 8 条）

| # | 强约束 | 状态 | 验证手段 |
|---|--------|------|---------|
| 1 | Pixel 禁用色 `#FF4D4F/#D32F2F/#007BFF` | ✅ 0 命中 | `tests/check-forbidden-colors.js` |
| 2 | 页面 IA 锚点 1:1（IA-REF + FIGMA + API 三件套） | ✅ 4/4 page | `tests/sf1-pages.test.js` |
| 3 | 双端类型共享（`packages/api-types/ts/`） | ⏳ 占位 README 已存在；SF2 接入生成 | — |
| 4 | 设计稿与开发契约（顶部 FIGMA 引用） | ✅ 4/4 page | `tests/sf1-pages.test.js` |
| 5 | 30 字 ACK 渲染 + 超长截断 tooltip | ✅ checkin 页级 packAck + ack-bubble observers + onAckLongPress | `tests/sf1/checkin-screenshot.test.js` |
| 6 | SSE 客户端 1s→2s→4s→8s→16s→30s 上限 | ✅ `utils/sse.ts` + `utils/config.ts` SSE_BACKOFF_STEPS_MS | `tests/sf1-pages.test.js` |
| 7 | 推送 4 端 SDK 一致 | ⏳ 不在 SF1 scope；SF5 实施 | — |
| 8 | 设计稿双端像素对齐 | ⏳ 不在 SF1 scope；miniprogram-automator 真截图 W5 起 CI 跑 | — |

## 3. 测试结果

```
[PASS] tests/smoke.test.js          33/33  (SF0 baseline)
[PASS] tests/sf1-pages.test.js      70/70  (SF1 强约束)
[PASS] tests/sf1/splash-…test.js    14/14
[PASS] tests/sf1/login-…test.js     13/13
[PASS] tests/sf1/home-…test.js      22/22
[PASS] tests/sf1/checkin-…test.js   30/30  (含 §17.15 30 字截断静态模拟)
[PASS] tests/check-forbidden-colors 0 hits
```

## 4. 留给后续轮次（SF2~SF5）

- SF2：P03a/b/c 智能分析三段 + SSE 8 阶段 + image-uploader
- SF3：P03a 智能管家（persona_state FSM 4 态映射）+ P08 心情日记（ack-bubble 30 字）
- SF4：P06 21 天方案 / P09 对比回顾 / P10 蜕变广场 / P11 我的 + 3 张抱抱卡
- SF5：推送 4 端 SDK（FCM/APNs/HMS/email）+ wx.requestSubscribeMessage + 像素 diff CI 跑通

## 5. 与 §17 强约束 8 条的接口状态

| 接口 | SF1 状态 |
|------|---------|
| `POST /auth/wx-login` | ✅ login page 接入 |
| `GET /users/me` | ✅ home page 接入 |
| `GET /checkins/today` | ✅ home / checkin 接入 |
| `GET /plans/today` | ✅ home / checkin 接入 |
| `POST /checkins` | ✅ checkin 接入 |
| `POST /feedback` | ✅ checkin mood-only 路径接入 |
| `WS /diagnosis/{id}/stream` | ⏳ SF2 |
| `wx.connectSocket` | ⏳ SF2 |
