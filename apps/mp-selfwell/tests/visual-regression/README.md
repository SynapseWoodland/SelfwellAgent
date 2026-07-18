/**
 * tests/visual-regression/README.md
 * ─────────────────────────────────────────────────────────
 * Layer 2：小程序自身视觉回归
 *
 * 目的：确保每次代码变更后，小程序自身不发生视觉漂移。
 * 方式：微信开发者工具内置截图 + 与上次截图人工对比（maxDiffPixelRatio: 0.01）。
 *
 * 注意：微信小程序无法在纯 CI 环境直接截图，需 reviewer 手动操作。
 * 每次 PR 提交流程：
 *   1. reviewer clone PR branch
 *   2. 微信开发者工具打开项目
 *   3. 逐页面截图（开发者工具 → 截图 → 导出 PNG）
 *   4. 放入 `__snapshots__/` 目录（文件名 = page-name-state.png）
 *   5. 与上一次 commit 的 `__snapshots__/` 做视觉 diff
 *
 * screenshots/ 目录不提交 git，手动存放在 reviewer 本地，
 * 仅在 PR description 引用 diff 结论。
 *
 * PR-V2-A
 */

# Layer 2 · 小程序自身视觉回归

## 工作流程

```
PR 提交流程（Layer 2）：
  1. reviewer checkout PR branch
  2. 微信开发者工具打开 apps/mp-selfwell
  3. 逐页面截图（每个 tab + 每个关键状态）
     - splash / login
     - 今天 Tab（今天无方案 / 今天有方案 / 打卡完成 overlay）
     - 抽屉打开态
     - 广场
     - 我的
     - 诊断上传 / loading / 报告
     - 方案交付
  4. 截图命名规范：
     - {page}-{state}.png
     - 例：home-today-no-plan.png / home-today-with-plan.png / home-drawer-open.png
  5. 与上一次 commit 的截图做人工对比
  6. 结论填入 PR description 结构清单
```

## Layer 2 vs Layer 1 的关系

| 层级 | 对象 | 目的 | 工具 |
|------|------|------|------|
| Layer 1 | HTML 原型 | 验证小程序与设计稿"语义一致" | Playwright（CI 可跑） |
| Layer 2 | 小程序自身 | 防止代码变更引入视觉回归 | 微信开发者工具（手动） |
| Layer 3 | 跨域对照 | 确认小程序渲染接近原型视觉 | 人工（reviewer） |

## 截图清单（每个 PR 必查页面）

| # | 页面 | 截图状态 | 对应原型 |
|---|------|---------|---------|
| 1 | splash | 默认 | 01-splash |
| 2 | login | 默认 | 02-login |
| 3 | 今天 Tab | 今天无方案 | 15b（初始态）|
| 4 | 今天 Tab | 今天有方案 | 15b（有 streak）|
| 5 | 今天 Tab | 打卡完成 overlay | 15b（complete-overlay）|
| 6 | 今天 Tab | 抽屉打开 | 15c |
| 7 | 广场 | 默认 | 09-square |
| 8 | 我的 | 默认 | 11-profile |
| 9 | 诊断上传 | 默认 + 已上传 1 张 | 04-diagnosis-upload |
| 10 | 诊断 loading | 默认 | 05-diagnosis-loading |
| 11 | 诊断报告 | 默认 | 15i |
| 12 | 方案交付 | 默认 | 15h |
