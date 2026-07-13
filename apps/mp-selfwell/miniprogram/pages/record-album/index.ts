/**
 * PR-A4 清理 · record-album 兜底桩
 * ──────────────────────────────────────────────────────────────
 * H3 record-album 兜底：home/index.ts:266 跳转
 *   wx.navigateTo({ url: '/pages/record-album/index' })
 *
 * PR-5 record-album 落地后由真实实现替换。此 stub：
 *  - 不 404（app.json 未注册，提前垫底）
 *  - 可渲染空白页
 *  - 不依赖任何业务数据
 */
Page({
  data: {},
  onLoad() {},
  onNavBack() {
    wx.navigateBack({ delta: 1 });
  },
});
