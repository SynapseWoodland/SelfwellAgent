/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.6 P11 我的
 * 设计稿: docs/design/figma-pixso-spec/pages/11-profile.html
 * 后端端点:
 *   - openapi.yaml tag=users operationId=getCurrentUser  GET  /users/me
 *   - openapi.yaml tag=users operationId=updatePushToken POST /users/push-token
 *
 * V5.2.1-PR5 FR-2：6 字段档案表单（age_range / sitting_hours / focus_parts /
 *   intensity / preferred_time / skin_type），写 utils/profile-storage.ts storage。
 *
 * 行为（SF4 完工态 + PR5）：
 *  - onLoad 拉 /users/me + 读 storage profile（6 字段）
 *  - "订阅推送"入口 → 调 utils/subscribe.subscribeMessages + 上报 /users/push-token
 *  - 文案禁用：禁止 "你的进度打败了 X% 的用户" 等排名/分数焦虑词
 *  - 6 字段表单填写 → onSubmitProfile → writeUserProfile → showToast
 *  - intensity / skin_type 必填校验
 *  - 顶部 banner 实时显示 "已完善 X/6 项"
 */
import { get, post } from '../../utils/request';
import { subscribeMessages, reportSubscribeResults } from '../../utils/subscribe';
import { STORAGE_KEYS, CLIENT_PLATFORM } from '../../utils/config';
import {
  readUserProfile,
  writeUserProfile,
  countFilledFields,
  type UserProfile6Fields,
} from '../../utils/profile-storage';

interface UserProfile {
  id: string;
  nickname: string;
  avatar?: string;
  status: 'draft' | 'active';
  streak: number;
  currentDay: number;
}

// PR5 FR-2：表单选项常量（与 utils/profile-storage.ts 的 UserProfile6Fields 字段命名对齐）
const AGE_RANGE_OPTIONS = [
  { value: '18-29', label: '18-29' },
  { value: '30-39', label: '30-39' },
  { value: '40-49', label: '40-49' },
  { value: '50+', label: '50+' },
];
const FOCUS_PART_OPTIONS = [
  { value: '面部', label: '面部' },
  { value: '头部', label: '头部' },
  { value: '肩颈', label: '肩颈' },
  { value: '眼周', label: '眼周' },
  { value: '颈部', label: '颈部' },
];
const INTENSITY_OPTIONS = [
  { value: '轻柔', label: '轻柔' },
  { value: '标准', label: '标准' },
  { value: '强效', label: '强效' },
];
const PREFERRED_TIME_OPTIONS = [
  { value: '早上', label: '早上' },
  { value: '中午', label: '中午' },
  { value: '晚上', label: '晚上' },
];
const SKIN_TYPE_OPTIONS = [
  { value: '油性', label: '油性' },
  { value: '干性', label: '干性' },
  { value: '中性', label: '中性' },
  { value: '混合', label: '混合' },
  { value: '敏感', label: '敏感' },
];

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
    // PR5 FR-2：6 字段档案
    ageRangeOptions: AGE_RANGE_OPTIONS,
    focusPartOptions: FOCUS_PART_OPTIONS,
    intensityOptions: INTENSITY_OPTIONS,
    preferredTimeOptions: PREFERRED_TIME_OPTIONS,
    skinTypeOptions: SKIN_TYPE_OPTIONS,
    ageRange: '' as string,
    sittingHours: '' as string, // input number 字符串，避免 input value 0 渲染问题
    focusParts: [] as string[],
    intensity: '' as string,
    preferredTime: '' as string,
    skinType: '' as string,
    profileFilledCount: 0,
  },

  onLoad() {
    this.fetchMe();
    this.loadProfile();
  },

  onShow() {
    this.fetchMe();
    this.loadProfile();
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

  /** PR5 FR-2：读 storage 6 字段填表单 + 计算 filledCount。 */
  loadProfile() {
    const p = readUserProfile();
    this.setData({
      ageRange: p.age_range ?? '',
      sittingHours: p.sitting_hours !== null && p.sitting_hours !== undefined ? String(p.sitting_hours) : '',
      focusParts: Array.isArray(p.focus_parts) ? p.focus_parts : [],
      intensity: p.intensity ?? '',
      preferredTime: p.preferred_time ?? '',
      skinType: p.skin_type ?? '',
      profileFilledCount: countFilledFields(p),
    });
  },

  onSelectAgeRange(e: WechatMiniprogram.BaseEvent) {
    const value = (e.currentTarget.dataset as { value: string }).value;
    this.setData({ ageRange: value });
  },

  onInputSittingHours(e: WechatMiniprogram.Input) {
    this.setData({ sittingHours: e.detail.value });
  },

  onToggleFocusPart(e: WechatMiniprogram.BaseEvent) {
    const value = (e.currentTarget.dataset as { value: string }).value;
    const cur: string[] = this.data.focusParts || [];
    const next = cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value];
    this.setData({ focusParts: next });
  },

  onSelectIntensity(e: WechatMiniprogram.BaseEvent) {
    const value = (e.currentTarget.dataset as { value: string }).value;
    this.setData({ intensity: value });
  },

  onSelectPreferredTime(e: WechatMiniprogram.BaseEvent) {
    const value = (e.currentTarget.dataset as { value: string }).value;
    this.setData({ preferredTime: value });
  },

  onSelectSkinType(e: WechatMiniprogram.BaseEvent) {
    const value = (e.currentTarget.dataset as { value: string }).value;
    this.setData({ skinType: value });
  },

  /** PR5 FR-2：保存 6 字段档案到 storage。必填校验 intensity / skin_type。 */
  onSubmitProfile() {
    if (!this.data.intensity) {
      wx.showToast({ title: '请填写必填项：干预强度', icon: 'none' });
      return;
    }
    if (!this.data.skinType) {
      wx.showToast({ title: '请填写必填项：肤质', icon: 'none' });
      return;
    }
    const profile: UserProfile6Fields = {
      age_range: this.data.ageRange || null,
      sitting_hours: this.data.sittingHours === '' ? null : Number(this.data.sittingHours),
      focus_parts: this.data.focusParts.length > 0 ? this.data.focusParts : null,
      intensity: this.data.intensity || null,
      preferred_time: this.data.preferredTime || null,
      skin_type: this.data.skinType || null,
    };
    writeUserProfile(profile);
    this.setData({ profileFilledCount: countFilledFields(profile) });
    wx.showToast({ title: '档案已保存', icon: 'success' });
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
    if (id === 'notification') {
      void this.onSubscribePush();
    } else if (id === 'profile') {
      // PR5：点 "用户档案" 滚动到档案表单区
      // （未来可跳独立子页；目前 page 内有表单，滚动更轻量）
      wx.showToast({ title: '请向下滚动填写档案', icon: 'none' });
    } else {
      wx.showToast({ title: `${id} 占位`, icon: 'none' });
    }
  },
});
