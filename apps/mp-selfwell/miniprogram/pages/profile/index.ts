/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.6 P11 我的
 * 设计稿: docs/design/figma-pixso-spec/pages/11-profile.html
 *
 * V5.2.1-PR5.1 改造：
 * - 移除 PR5 内嵌的 6 字段表单（搬到 pages/profile-edit 子页，对齐设计稿 §4.6）
 * - onTapSetting('profile') 跳子页（之前是弹 toast'请向下滚动'，是绕设计稿的 tmp）
 * - loadProfileMiniSummary 读 storage 计算 filledCount 显示在设置列表「用户档案」右侧
 *
 * 行为（SF4 完工态 + PR5.1）：
 *  - onLoad 拉 /users/me + 读 storage 计算档案完成度
 *  - "订阅推送"入口 → 调 utils/subscribe.subscribeMessages + 上报 /users/push-token
 *  - 「用户档案」→ wx.navigateTo('/pages/profile-edit/index')（不是 switchTab，子页不在 tabBar）
 *  - 文案禁用：禁止 "你的进度打败了 X% 的用户" 等排名/分数焦虑词
 */

import { get, post } from '../../utils/request';
import { subscribeMessages, reportSubscribeResults } from '../../utils/subscribe';
import { STORAGE_KEYS, CLIENT_PLATFORM } from '../../utils/config';
import {
  readUserProfile,
  countFilledFields,
} from '../../utils/profile-storage';
import {
  PICK_PROFILE_TARGET_PATH,
} from '../profile-edit/index.smart-body';

interface UserProfile {
  id: string;
  nickname: string;
  avatar?: string;
  status: 'draft' | 'active';
  streak: number;
  currentDay: number;
}

/**
 * PR5.1 · 读 storage 6 字段并计算档案完成度，只在设置列表「用户档案」右侧展示。
 * 不渲染表单；表单在子页。
 */
function getProfileFilledCount(): number {
  return countFilledFields(readUserProfile());
}

Page({
  data: {
    nickname: '自愈用户',
    avatar: '',
    streak: 7,
    currentDay: 7,
    percent: 33,
    settings: [
      // 「用户档案」右侧显示进度（filled/total）；在 wxml 用 data 属性读
      // 注意：profileFilledLabel 在 onLoad/onShow 时计算并 merge 进 settings[0]
    ],
    /** PR5.1 · 显示在设置列表「用户档案」右侧；子页全文展示 */
    profileSummary: { filledCount: 0, totalCount: 6, label: '0/6' },
  },

  onLoad() {
    this.refreshSettingsWithSummary();
    this.fetchMe();
  },

  onShow() {
    this.refreshSettingsWithSummary();
    this.fetchMe();
  },

  /**
   * PR5.1 · 重算 settings 列表头项「用户档案」右侧 label。
   * 用户从子页回来立刻看到最新完成度。
   */
  refreshSettingsWithSummary() {
    const filled = getProfileFilledCount();
    const label = `${filled}/6`;
    this.setData({
      settings: [
        { id: 'profile', label: '用户档案', filledLabel: label },
        { id: 'notification', label: '通知设置' },
        { id: 'about', label: '关于自愈' },
        { id: 'privacy', label: '隐私政策' },
        { id: 'support', label: '联系客服' },
      ],
      profileSummary: { filledCount: filled, totalCount: 6, label },
    });
  },

  async fetchMe() {
    try {
      const me = await get<UserProfile>('/users/me');
      if (me) {
        this.setData({
          nickname: me.nickname || '自愈用户',
          avatar: me.avatar || '',
          streak: me.streak ?? 0,
          currentDay: me.currentDay ?? 0,
          percent: Math.min(100, Math.round((me.currentDay / 21) * 100)),
        });
      }
    } catch {
      /* mock 兜底 */
    }
  },

  async onSubscribePush() {
    const results = await subscribeMessages(['checkin_remind', 'recall_card']);
    const accepted = results.filter((r) => r.status === 'accept').map((r) => r.templateId);
    await reportSubscribeResults(results);
    if (accepted.length === 0) {
      wx.showToast({ title: '未授权，仍可在 App 内收到提醒', icon: 'none' });
      return;
    }
    // 上报 push token（mock；真实 token 通过 wx.getStorageSync('push_token_wechat_mp') 取）
    const userId = wx.getStorageSync(STORAGE_KEYS.userId) || '';
    const pushToken = wx.getStorageSync(STORAGE_KEYS.pushToken) || 'mock_push_token';
    try {
      await post('/users/push-token', {
        token: pushToken,
        client_platform: CLIENT_PLATFORM,
        user_id_pseudo: userId ? 'pseudo_' + userId.slice(-6) : 'pseudo_anon',
        templates: accepted,
      });
      wx.showToast({ title: '订阅成功', icon: 'success' });
    } catch {
      wx.showToast({ title: '订阅失败，请稍后再试', icon: 'none' });
    }
  },

  onGotoShare() {
    wx.navigateTo({ url: '/pages/share-hug-card/index?day=7' });
  },

  onTapSetting(e: WechatMiniprogram.BaseEvent) {
    const id = (e.currentTarget.dataset as { id: string }).id;
    if (id === 'profile') {
      // PR5.1：跳子页（PR5 这里弹 toast'请向下滚动填写档案'，绕设计稿的临时方案）
      // 子页 profile-edit 不在 tabBar 列表，必须用 wx.navigateTo（switchTab 会 fail silently）
      wx.navigateTo({ url: PICK_PROFILE_TARGET_PATH });
      return;
    }
    if (id === 'notification') {
      void this.onSubscribePush();
      return;
    }
    wx.showToast({ title: `${id} 占位`, icon: 'none' });
  },
});
