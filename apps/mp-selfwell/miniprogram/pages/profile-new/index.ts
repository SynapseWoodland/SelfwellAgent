/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.6 P11 我的（V2 tabBar 主页 · PR-3 commit-1）
 * FIGMA  : docs/design/figma-pixso-spec/pages/11-profile.html
 *
 * PR-3 commit-1 · profile-new 主页（V2 11-profile.html）
 * ─────────────────────────────────────────────────────────────────
 * - 头像渐变（mint → sky）+ 昵称 + streak
 * - 6 列表项：用户档案 / 我的时光 / 通知设置 / 隐私政策 / 联系客服 / 关于自愈
 * - 头像渐变走 PR-6 app.wxss 既有 token，不在 wxss 内硬编码 hex（与 PR-6 锁值契约一致）
 *
 * PR-5 扩展 · 5 跳转入口
 * ─────────────────────────────────────────────────────────────────
 * - 用户档案：?mode=read（默认 read，只读视图；走 pages/profile-edit）
 * - 我的时光：/pages/album/index（PR-5 新建；接管 PR-3 旧的 record-album）
 * - 通知设置：/pages/notification-settings/index（PR-5 新建）
 * - 隐私政策：/pages/privacy-policy/index（PR-5 新建）
 * - 联系客服：/pages/contact/index（PR-5 新建）
 * - 关于自愈：/pages/about/index（PR-5 新建）
 *
 * 数据来源：
 * - /users/me → nickname / current_streak_days（PR-2 已扩 streak_days）
 * - profile 6 字段完成度 → 本地 profile-storage 读（PR5 沿用）
 *
 * 子页跳转全部用 wx.navigateTo（profile-new 是 tabBar 页，navigateTo 不能跳 tabBar；
 * 反之 navigateTo 可从 tabBar 跳到非 tabBar 子页）。
 */
import { get } from '../../utils/request';
import { readUserProfile, countFilledFields } from '../../utils/profile-storage';
import type { UserMe } from '../../types/api';

interface ProfileNewData {
  nickname: string;
  streak: number;
  currentDay: number;
  percent: number;
  profileFilledLabel: string;
  settings: Array<{
    id: string;
    label: string;
    rightLabel?: string;
    pagePath: string;
  }>;
}

Page<ProfileNewData>({
  data: {
    nickname: '自愈用户',
    streak: 0,
    currentDay: 0,
    percent: 0,
    profileFilledLabel: '0/6',
    settings: [],
  },

  onLoad() {
    this.refreshSettings();
    void this.fetchMe();
  },

  onShow() {
    // 从子页回来时刷新档案完成度
    this.refreshSettings();
  },

  refreshSettings() {
    const filled = countFilledFields(readUserProfile());
    const label = `${filled}/6`;
    this.setData({
      profileFilledLabel: label,
      settings: [
        { id: 'profile', label: '用户档案', rightLabel: `档案 ${label}`, pagePath: '/pages/profile-edit/index?mode=read' },
        { id: 'time', label: '我的时光', pagePath: '/pages/album/index' },
        { id: 'notification', label: '通知设置', pagePath: '/pages/notification-settings/index' },
        { id: 'privacy', label: '隐私政策', pagePath: '/pages/privacy-policy/index' },
        { id: 'support', label: '联系客服', pagePath: '/pages/contact/index' },
        { id: 'about', label: '关于自愈', pagePath: '/pages/about/index' },
      ],
    });
  },

  async fetchMe() {
    try {
      const me = await get<UserMe>('/users/me');
      if (me) {
        this.setData({
          nickname: me.nickname || '自愈用户',
          streak: me.current_streak_days ?? 0,
          currentDay: me.current_streak_days ?? 0,
          percent: Math.min(100, Math.round(((me.current_streak_days ?? 0) / 21) * 100)),
        });
      }
    } catch {
      /* 兜底 */
    }
  },

  onTapSetting(e: WechatMiniprogram.BaseEvent) {
    const id = (e.currentTarget.dataset as { id?: string }).id;
    const item = this.data.settings.find((s) => s.id === id);
    if (!item) return;
    // profile-new 是 tabBar 页；子页不在 tabBar 内 → navigateTo（switchTab 会失败）
    wx.navigateTo({ url: item.pagePath });
  },

  // ── PR-5 · 5 个具名跳转入口（与 data-id 一一对应；保留向后兼容） ──
  onTapProfileEdit() {
    wx.navigateTo({ url: '/pages/profile-edit/index?mode=read' });
  },

  onTapArchiveAlbum() {
    wx.navigateTo({ url: '/pages/album/index' });
  },

  onTapNotifications() {
    wx.navigateTo({ url: '/pages/notification-settings/index' });
  },

  onTapPrivacy() {
    wx.navigateTo({ url: '/pages/privacy-policy/index' });
  },

  onTapContact() {
    wx.navigateTo({ url: '/pages/contact/index' });
  },

  onTapAbout() {
    wx.navigateTo({ url: '/pages/about/index' });
  },

  onGotoShare() {
    wx.navigateTo({ url: '/pages/share-hug-card/index' });
  },
});