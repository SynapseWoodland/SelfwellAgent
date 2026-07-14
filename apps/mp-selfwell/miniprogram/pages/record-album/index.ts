/**
 * FE-FIX-02 · record-album → album 重定向桩
 * ──────────────────────────────────────────────────────────────
 * 真源：docs/plan/frontend-fix-plan.md §FE-FIX-02。
 *
 * 临时兜底：用户从「home 抽屉 我的时光」进入 record-album 时，
 * 自动 redirect 到已实现的 album 页（避免用户看到空白页）。
 *
 * PR-5 决策后保留 `record-album`（命名更清晰），将 `album` 逻辑迁回
 * 到 `record-album`，删除 `album`。本 redirect 桩届时可删除。
 */
Page({
  data: {},
  onLoad() {
    wx.redirectTo({ url: '/pages/album/index' });
  },
  onNavBack() {
    // 重定向后原页面已销毁，无法 navigateBack；统一走 reLaunch 兜底。
    wx.reLaunch({ url: '/pages/home/index' });
  },
});
