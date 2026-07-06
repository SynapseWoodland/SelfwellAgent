/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.6 P11 我的
 * 设计稿: docs/design/figma-pixso-spec/pages/11-profile.html
 * 后端端点:
 *   - openapi.yaml tag=users operationId=getCurrentUser  GET  /users/me
 *   - openapi.yaml tag=users operationId=updatePushToken POST /users/push-token
 *
 * 行为（SF4 完工态）：
 *  - onLoad 拉 /users/me
 *  - "订阅推送"入口 → 调 utils/subscribe.subscribeMessages + 上报 /users/push-token
 *  - 文案禁用：禁止 "你的进度打败了 X% 的用户" 等排名/分数焦虑词
 */
import { get, post } from '../../utils/request';
import { subscribeMessages, reportSubscribeResults } from '../../utils/subscribe';
import { STORAGE_KEYS, CLIENT_PLATFORM } from '../../utils/config';

interface UserProfile {
  id: string;
  nickname: string;
  avatar?: string;
  status: 'draft' | 'active';
  streak: number;
  currentDay: number;
}
Page({
  data: {
    nickname: '自愈用户',
    avatar: '',
    streak: 7,
    currentDay: 7,
    percent: 33,
    settings: [
      { id: 'profile', label: '用户档案' },
      { id: 'notification', label: '通知设置' },
      { id: 'about', label: '关于自愈' },
      { id: 'privacy', label: '隐私政策' },
      { id: 'support', label: '联系客服' },
    ],
  },

  onLoad() {
    this.fetchMe();
  },

  onShow() {
    this.fetchMe();
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
    wx.navigateTo({ url: '/miniprogram/pages/share-hug-card/index?day=7' });
  },

  onTapSetting(e: WechatMiniprogram.CustomEvent<{ id: string }>) {
    const id = e.detail?.id;
    if (id === 'notification') {
      this.onSubscribePush();
    } else if (id === 'profile') {
      wx.showToast({ title: '档案编辑（M1 SF1 接入）', icon: 'none' });
    } else {
      wx.showToast({ title: `${id} 占位`, icon: 'none' });
    }
  },
});