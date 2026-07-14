/**
 * profile-new/index.ts
 * 1:1 复刻修复方案：上绿下白两段式布局
 * - 新增 ageRange/crowd/level（用户标签）
 * - settings 数组每项带 subtitle（副标题）
 */
import { get } from '../../utils/request';
import type { UserMe } from '../../types/api';

interface ProfileNewData {
  nickname: string;
  ageRange: string;
  crowd: string;
  level: string;
  drawerVisible: boolean;
  drawerItems: Array<{
    id: string;
    label: string;
    pagePath: string;
  }>;
  settings: Array<{
    id: string;
    label: string;
    subtitle: string;
    pagePath: string;
  }>;
}

Page<ProfileNewData>({
  data: {
    nickname: '',
    ageRange: '25-30 岁',
    crowd: '久坐人群',
    level: '自律 C',
    drawerVisible: false,
    drawerItems: [
      { id: 'profile', label: '用户档案', pagePath: '/pages/profile-edit/index?mode=read' },
      { id: 'album', label: '我的时光', pagePath: '/pages/album/index' },
      { id: 'notification', label: '通知设置', pagePath: '/pages/notification-settings/index' },
      { id: 'privacy', label: '隐私政策', pagePath: '/pages/privacy-policy/index' },
      { id: 'contact', label: '联系客服', pagePath: '/pages/contact/index' },
      { id: 'about', label: '关于自愈', pagePath: '/pages/about/index' },
    ],
    settings: [
      { id: 'notification', label: '通知设置', subtitle: '打卡提醒 · 抱抱卡发放', pagePath: '/pages/notification-settings/index' },
      { id: 'privacy', label: '隐私政策', subtitle: '数据权限', pagePath: '/pages/privacy-policy/index' },
      { id: 'about', label: '关于自愈', subtitle: '产品介绍', pagePath: '/pages/about/index' },
      { id: 'contact', label: '联系客服', subtitle: '在线反馈', pagePath: '/pages/contact/index' },
    ],
  },

  onLoad() {
    void this.fetchMe();
  },

  async fetchMe() {
    try {
      const me = await get<UserMe>('/users/me');
      if (me) {
        this.setData({
          nickname: me.nickname || '用户',
          ageRange: me.age_range || '25-30 岁',
          crowd: me.crowd || '久坐人群',
          level: me.level || '自律 C',
        });
      }
    } catch {
      /* 兜底默认状态 */
    }
  },

  // ── 抽屉控制 ──
  onOpenDrawer() {
    this.setData({ drawerVisible: true });
  },

  onCloseDrawer() {
    this.setData({ drawerVisible: false });
  },

  onDrawerNav(e: WechatMiniprogram.BaseEvent) {
    const id = (e.currentTarget.dataset as { id?: string }).id;
    const item = this.data.drawerItems.find((s) => s.id === id);
    if (!item) return;
    this.setData({ drawerVisible: false });
    void wx.navigateTo({ url: item.pagePath });
  },

  // ── 设置入口（遍历 settings 数组路由分发）───
  onTapSettings(e: WechatMiniprogram.BaseEvent) {
    const id = (e.currentTarget.dataset as { id?: string }).id;
    const item = this.data.settings.find((s) => s.id === id);
    if (item) {
      void wx.navigateTo({ url: item.pagePath });
    }
  },
});
