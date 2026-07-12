/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.6 P11 我的（PR-3 commit-1 redirect stub）
 *
 * PR-3 commit-1 · profile 旧页 → profile-new 主页 跳转 stub
 * ─────────────────────────────────────────────────────────────────
 * - V2 tabBar 第 4 项已切换到 pages/profile-new/index（PR-3 commit-1 §app.json）
 * - 旧 pages/profile/index 在 app.json 中仍保留 pages 注册（向后兼容 deep link / 老用户收藏）
 * - onLoad → wx.reLaunch 跳 /pages/profile-new/index
 * - 防止"跳 profile → 又被切回 profile"死循环：用 reLaunch 而非 navigateTo
 *   reLaunch 会清空页面栈，profile-new 不可能回退到 profile，避免循环
 *
 * 验收：profile redirect 跳 profile-new 不死循环（PR-3 §验收清单）
 */
Page({
  data: {},

  onLoad() {
    // reLaunch 而非 navigateTo：清空页面栈，避免 profile-new → 返回 profile 的回退循环
    wx.reLaunch({ url: '/pages/profile-new/index' });
  },
});