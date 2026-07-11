/**
 * profile-edit 子页 · V5.2.1-PR5.1
 *
 * 真源：SPEC-V521-PR5.1-profile-edit-subpage.md §FR-1/§FR-2/§FR-3/§FR-4
 * 依赖：utils/profile-storage.ts（PR5）+ utils/request.ts（post + ApiException）
 *
 * 设计要点：
 * - 6 字段表单从 PR5 pages/profile/index.ts 平移过来（diff 控制在净增 ≤30 行）
 * - onSubmitProfile 调 POST /users/profile 真接后端，submitting 锁 + fail-soft
 * - skin_type 写本地 storage（前端 SSE 入参需要），不上送后端
 * - 所有副作用走 wx.showToast / wx.setStorageSync / post；纯逻辑委托给 index.smart-body.ts
 *
 * IA 引用：docs/design/ia-and-wireframe.md §4.6 P06 子页（用户档案编辑）
 */

import {
  readUserProfile,
  writeUserProfile,
  countFilledFields,
  type UserProfile6Fields,
} from '../../utils/profile-storage';
import { post, ApiException } from '../../utils/request';
import {
  buildProfileBackendPayload,
  validateProfileRequiredFields,
  PICK_PROFILE_TARGET_PATH,
} from './index.smart-body';

// PR5 选项常量（与 pages/profile/index.ts:39-68 完全一致；平移避免变更面）
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

/**
 * WXML 多选 chip 的"是否选中"必须在 JS 端预计算成 map（key→bool），
 * 模板直接读 `map[item.value]`（WXML 不支持 Array.prototype.indexOf）。
 * 与 PR5 pages/profile/index.ts:75-81 同款实现。
 */
function buildFocusPartsSelected(values: string[]): Record<string, boolean> {
  const map: Record<string, boolean> = {};
  for (const opt of FOCUS_PART_OPTIONS) {
    map[opt.value] = values.includes(opt.value);
  }
  return map;
}

/** Toast 文案集中常量（与 SPEC §FR-3 + §FR-4 对齐） */
const TOAST_PROFILE_SAVED_LOCAL_ONLY = '本地已保存';
const TOAST_PROFILE_SYNCED = '档案已同步';
const TOAST_PROFILE_SYNC_FAILED = '同步失败，本地已保存';
const TOAST_REQUIRED_INTENSITY = '请填写必填项：干预强度';
const TOAST_REQUIRED_SKIN_TYPE = '请填写必填项：肤质';

Page({
  data: {
    ageRangeOptions: AGE_RANGE_OPTIONS,
    focusPartOptions: FOCUS_PART_OPTIONS,
    intensityOptions: INTENSITY_OPTIONS,
    preferredTimeOptions: PREFERRED_TIME_OPTIONS,
    skinTypeOptions: SKIN_TYPE_OPTIONS,
    ageRange: '' as string,
    sittingHours: '' as string,
    focusParts: [] as string[],
    focusPartsSelected: buildFocusPartsSelected([]),
    intensity: '' as string,
    preferredTime: '' as string,
    skinType: '' as string,
    profileFilledCount: 0,
    /** FR-4：提交中状态锁（防抖），WXML disabled 绑定此字段 */
    submitting: false as boolean,
  },

  onLoad() {
    this.loadProfile();
  },

  onShow() {
    this.loadProfile();
  },

  /** PR5：读 storage 6 字段回填表单 + 计算 filledCount（顶部 banner）。 */
  loadProfile() {
    const p: UserProfile6Fields = readUserProfile();
    const focusParts = Array.isArray(p.focus_parts) ? p.focus_parts : [];
    this.setData({
      ageRange: p.age_range ?? '',
      sittingHours:
        p.sitting_hours !== null && p.sitting_hours !== undefined
          ? String(p.sitting_hours)
          : '',
      focusParts,
      focusPartsSelected: buildFocusPartsSelected(focusParts),
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
    this.setData({
      focusParts: next,
      focusPartsSelected: buildFocusPartsSelected(next),
    });
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

  /**
   * FR-3 + FR-4：保存 6 字段档案。
   *
   * 流程：
   *   1. 防抖闸门：submitting=true 直接 return
   *   2. 必填校验：intensity + skin_type（validateProfileRequiredFields 纯函数）
   *   3. 校验通过 → 本地 6 字段 writeUserProfile（local-first）
   *   4. 构造 5 字段 payload（buildProfileBackendPayload 纯函数）→ POST /users/profile
   *   5. 成功 → toast '档案已同步'；失败 → toast '同步失败，本地已保存'（fail-soft）
   *   6. finally 释放 submitting 锁
   *
   * 关键约束（SPEC §3.1 / §3.4）：
   * - skin_type 不上送后端（前端 SSE 入参需要，本地保留）
   * - 本地存为先（fail-soft 兜底），用户体感"档案永远不丢"
   * - 失败不阻塞 UI（不弹阻塞式 modal，只 toast）
   */
  async onSubmitProfile() {
    // FR-4 · 防抖闸门
    if (this.data.submitting) return;
    this.setData({ submitting: true });

    try {
      const localState = {
        age_range: this.data.ageRange,
        sitting_hours:
          this.data.sittingHours === '' ? null : Number(this.data.sittingHours),
        focus_parts: this.data.focusParts,
        intensity: this.data.intensity,
        preferred_time: this.data.preferredTime,
        skin_type: this.data.skinType,
      };

      // 必填校验（纯函数）
      const v = validateProfileRequiredFields(localState);
      if (!v.ok) {
        const msg =
          v.reason === 'intensity_missing'
            ? TOAST_REQUIRED_INTENSITY
            : TOAST_REQUIRED_SKIN_TYPE;
        wx.showToast({ title: msg, icon: 'none' });
        return; // 注意：finally 仍会执行，把 submitting 重置回 false
      }

      // local-first：本地 6 字段先写（skin_type 保留给 SSE）
      const localProfile: UserProfile6Fields = {
        age_range: localState.age_range || null,
        sitting_hours: localState.sitting_hours,
        focus_parts: localState.focus_parts.length > 0 ? localState.focus_parts : null,
        intensity: localState.intensity || null,
        preferred_time: localState.preferred_time || null,
        skin_type: localState.skin_type || null,
      };
      writeUserProfile(localProfile);

      // FR-3 · 后端 5 字段 payload（skin_type 不上送）
      const backendPayload = buildProfileBackendPayload({
        ...localState,
        sitting_hours: localState.sitting_hours,
      });

      try {
        await post<unknown>('/users/profile', backendPayload);
        this.setData({ profileFilledCount: countFilledFields(localProfile) });
        wx.showToast({ title: TOAST_PROFILE_SYNCED, icon: 'success' });
      } catch (err) {
        // fail-soft：本地已保存（响应用户"未丢失"的体感）
        const detail =
          err instanceof ApiException ? `(${err.code})` : '';
        console.warn('[profile-edit] 后端同步失败，本地已存', detail);
        wx.showToast({ title: TOAST_PROFILE_SYNC_FAILED, icon: 'none' });
      }
    } finally {
      // FR-4 · 释放锁：无论成功/失败/校验失败都要回到可点击
      this.setData({ submitting: false });
    }
  },
});

/** 目标路径在 pages/profile-edit/index.smart-body.ts（PICK_PROFILE_TARGET_PATH）。
 *  pages/profile/index.ts:onTapSetting 跳子页时直接 import 这个常量。
 *（避免 index.ts 既注册 Page() 又导出常量，导致 ts-jest 误把 Page 注册侧效应当 module 副作用。） */
