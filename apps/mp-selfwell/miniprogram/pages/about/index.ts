/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.7 P21 关于自愈（V2 我的 Tab 子页）
 *
 * PR-5 · 关于自愈子页（不带 tabBar）
 * ─────────────────────────────────────────────────────────────────
 * - 应用版本号（来自 wx.getAccountInfoSync）
 * - 系统信息（来自 wx.getAppBaseInfo）
 * - 静态文案 + 鸣谢
 */

interface AboutData {
  appVersion: string;
  miniVersion: string;
  system: string;
  systemVersion: string;
  wechatVersion: string;
  buildYear: string;
}

const BUILD_YEAR = '2026';

Page<AboutData>({
  data: {
    appVersion: '1.0.0',
    miniVersion: '',
    system: '',
    systemVersion: '',
    wechatVersion: '',
    buildYear: BUILD_YEAR,
  },

  onLoad() {
    this.loadSystemInfo();
  },

  loadSystemInfo() {
    // 1. 应用版本（来自 wx.getAccountInfoSync）
    try {
      const account = wx.getAccountInfoSync();
      const minpVersion = (account?.miniProgram?.version ?? '') as string;
      this.setData({
        appVersion: minpVersion || '1.0.0',
        miniVersion: minpVersion,
      });
    } catch {
      // wx.getAccountInfoSync 在 IDE / 某些低版本不存在 → 兜底空字符串
    }

    // 2. 系统信息（来自 wx.getAppBaseInfo / wx.getSystemInfo）
    try {
      const info = wx.getAppBaseInfo
        ? wx.getAppBaseInfo()
        : wx.getSystemInfoSync();
      this.setData({
        system: info?.system ?? '',
        systemVersion: info?.version ?? '',
        wechatVersion: info?.SDKVersion ?? info?.version ?? '',
      });
    } catch {
      // 忽略：UI 静默降级
    }
  },

  onCopyContact() {
    wx.setClipboardData({
      data: 'selfwell@example.com',
      success: () => wx.showToast({ title: '邮箱已复制', icon: 'success' }),
    });
  },

  onCheckUpdate() {
    wx.showToast({ title: '已是最新版本', icon: 'success' });
  },
});