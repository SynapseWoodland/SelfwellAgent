# Selfwell 自愈 · 微信小程序

> **模块**：M1-M11（MVP 全量客户端）
> **后端基线**：[MVP-PRD V1.3](../../docs/PRD/MVP-PRD%20V1.3.md) + [mvp-tech-architecture V1.1.1](../../docs/architecture/mvp-tech-architecture.md)
> **对齐文档**：[mvp-implementation-plan.md §15.3](../../docs/plan/mvp-implementation-plan.md) · §17 前端强约束 8 条
> **路径约定**：`miniprogram/` 是小程序代码根目录

## Sprint 状态（SF0 完成 · 2026-07-06 / SF1 完成 · 2026-07-06）

| 项 | 状态 |
|---|---|
| `project.config.json` + `project.private.config.json` | ✅ SF0 完成；appid 占位 `wx_your_appid`（W0-D1 注册后替换） |
| `miniprogram/app.json` | ✅ 14 pages + tabBar 4 项 + requiredPrivateInfos + permission |
| `miniprogram/app.ts` | ✅ globalData(token/userId/deviceId/clientPlatform) + onLaunch 4 步 |
| `miniprogram/app.wxss` | ✅ 全局 token CSS 变量（与 `figma-pixso-spec/dist/tokens-flat.json` 1:1） |
| `miniprogram/utils/` | ✅ 6 个工具：config / request(.ts + .js 入口) / sse / picker / subscribe / error-code (+ uuid) |
| `miniprogram/components/` | ✅ 7 个自定义组件 |
| `miniprogram/pages/` | ✅ 14 个 page；SF1 在 4 个 page（splash/login/home/checkin）落地 |
| `miniprogram/assets/tabbar/` | ✅ 8 张 tabBar 图标（81×81 PNG） |
| `miniprogram/types/global.d.ts` | ✅ 类型补丁（SocketTask / wx.compressImage） |
| `tests/smoke.test.js` | ✅ 33 项断言全部 PASS（**禁用色 0 命中**） |
| `tests/sf1-pages.test.js` | ✅ **70 项 SF1 强约束断言全部 PASS**（含 IA-REF/FIGMA/API 三件套） |
| `tests/sf1/{splash,login,home,checkin}-screenshot.test.js` | ✅ 4 个 page 静态渲染 stub（miniprogram-automator mock 形态） |
| `tests/check-forbidden-colors.js` | ✅ 0 命中（区分注释 / 文档行的精确扫描） |
| `packages/api-types/{ts,dart}/` | ⏳ 占位 README；SF2 接入生成（不在 SF1 scope） |

## 14 个页面（与 Pixso 高保真一一对齐）

| # | 页面 | 设计稿 | IA-REF | 后端 operationId |
|---|---|---|---|---|
| 01 | splash | 01-splash.html | §1 启动流程 / §4.1 P01 | tag=users `getCurrentUser`（可选） |
| 02 | login | 02-login.html | §4.1 P01 | tag=auth `wxMpLogin` |
| 03 | home | 03-home.html | §4.2 P02 P05 | tag=users `getCurrentUser` / tag=checkins `getCheckinCalendar` / tag=plans `getTodayPlan` |
| 04 | diagnosis-upload | 04-butler-analyze-upload.html | §5 P03 上传 | tag=uploads `presignUpload` / tag=diagnosis `createDiagnosis` |
| 05 | diagnosis-loading | 05-butler-analyze-loading.html | §5 P03 分析中 | tag=diagnosis `streamDiagnosis`（SSE） |
| 06 | diagnosis-report | 06-butler-analyze-report.html | §5 P03 报告 | tag=diagnosis `getDiagnosis` |
| 07 | assistant-home | 07-butler-home.html | §6 P03a | tag=assistant `assistantChat` / tag=butler `triggerRecall` |
| 08 | plan | 07-plan.html | §7 P04 | tag=plans `generatePlan` / tag=videos `getRecommendedVideos` |
| 09 | feedback-diary | 08-butler-diary.html | §8 P08 | tag=feedback `createFeedback` |
| 10 | checkin | 08-checkin.html | §9 P05 | tag=checkins `createCheckin` / tag=feedback `createFeedback` |
| 11 | recall-compare | 09-butler-compare.html | §10 P09 | tag=butler `getRecallMessages` / `listRecallHistory` |
| 12 | community | 09-plaza.html | §11 P10 | tag=community `getCommunityPosts` / `createPost` |
| 13 | profile | 11-profile.html | §12 P11 | tag=users `getCurrentUser` / `updatePushToken` |
| 14 | share-hug-card | 12/13/14-hug-card-day*.html | §13 M10 | tag=share `generateSharePoster` |

## 开发顺序（与 §1.2 Sprint 路线图对齐）

1. **SF0** ✅ 本 Sprint：骨架 + 14 page 占位 + 7 组件 + 4 工具
2. **SF1**：P00 启动 + P01 微信登录 + P02 首页 + P05 打卡完成（login / home / checkin 联调）
3. **SF2**：P03a/b/c 智能分析三段 + SSE + image-uploader
4. **SF3**：P03a 智能管家（persona_state FSM）+ P08 心情日记（ack-bubble 30 字）
5. **SF4**：P06 方案 / P09 对比回顾 / P10 广场 / P11 我的 + 3 张抱抱卡
6. **SF5**：推送 4 端 SDK（FCM/APNs/HMS/email）+ wx.requestSubscribeMessage

## 必跑命令（commit 前）

```bash
cd apps/mp-selfwell

# 1) SF0 烟雾测试（33 项断言）
cd tests && npm install && npm test && cd ..

# 2) SF1 强约束测试（70 项断言：IA-REF/FIGMA/API + 4 page 行为）
node tests/sf1-pages.test.js

# 3) SF1 4 page 静态渲染 stub
node tests/sf1/splash-screenshot.test.js
node tests/sf1/login-screenshot.test.js
node tests/sf1/home-screenshot.test.js
node tests/sf1/checkin-screenshot.test.js

# 4) 像素禁用色校验（§17.11 · 排除注释/文档）
node tests/check-forbidden-colors.js

# 5) 微信开发者工具 CLI（CI 镜像内置 cli.bat；本地开发手跑 IDE 即可）
cli.bat project preview
```

## 注意事项

- 类目选择：**MVP 阶段选"工具-效率"**（W6 升级公司主体后切"工具-健康"）
- 简介避免"医疗/医美/治疗"字眼，写成"AI 智能习惯陪伴 / 21 天轻自律"
- 详见 [ADR-0005 微信小程序类目](../../docs/architecture/adr/0005-wechat-mp-category.md)
- **像素禁用色栅栏**详见 `miniprogram/app.wxss` 顶部注释，CI grep 卡死
- **ack-bubble ≤ 30 字**由 `utils/config.ts` 中 `ACK_MAX_CHARS` 统一约束