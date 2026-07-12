/**
 * V5.2.1-PR5 · assistant-home 上传卡的纯函数模块（缺料校验 + body 构造）。
 *
 * 真源：SPEC-V521-PR5-frontend-contract.md §FR-6 + §FR-7。
 *
 * 为什么独立文件：
 * 1. assistant-home/index.ts 是 Page() 形式（1500+ 行），jest 测试 Page 需要 mock
 *    完整生命周期（onLoad / onShow / setData / ...），实现复杂度高；
 * 2. 把缺料校验 + body 构造抽成纯函数后，jest 只测这两个函数，Page() 内部
 *    `onSubmitUpload` / `runSmartAnalyze` 直接调用它们，逻辑唯一源；
 * 3. 与 SPEC §6 PR5/PR6 边界对齐：PR6 只动 onTapHistory（:1034），不碰这两个函数。
 *
 * 设计要点：
 * - checkSmartAnalyzePrerequisites 是**无副作用**函数（不调 wx.showToast / showModal）
 *   由 onSubmitUpload 拿到返回值后自己触发 UI 副作用；
 * - 这样 jest 测试不依赖全局 wx mock 的副作用顺序，可单独断言 reason 字段。
 */

import {
  readUserProfile,
  countFilledFields,
  type UserProfile6Fields,
} from '../../utils/profile-storage';

// 微信小程序全局 wx 类型补丁（与 utils/profile-storage.ts 一致，jest 环境由 setup.ts 注入 mock）。
declare const wx: {
  getStorageSync(key: string): string;
  setStorageSync(key: string, value: string | number | boolean | object): void;
};

/** assistant-home 上传卡槽位状态（与 upload-card 组件 wxml 字段对齐）。 */
export interface SmartAnalyzeSlotState {
  index: number;
  /** 显示名（"面部"/"头部"/"肩颈"/"眼周" 等，与后端 body_part 略有区别） */
  label: string;
  /** 后端 body_part 枚举值（face / head / shoulder_neck / ...） */
  bodyPart: 'face' | 'head' | 'shoulder_neck' | string;
  filled: boolean;
  filledUrl?: string;
}

/** 校验失败原因枚举（前端 UX 文案映射）。 */
export type PrerequisiteFailReason =
  | 'no_photo'
  | 'no_face'
  | 'profile_insufficient';

/** 校验结果：成功 / 失败 + reason。 */
export type PrerequisiteResult =
  | { ok: true }
  | { ok: false; reason: PrerequisiteFailReason; filledCount?: number; missing?: number };

export interface PrerequisiteInput {
  slots: SmartAnalyzeSlotState[];
  profile: UserProfile6Fields;
}

/**
 * 校验上传卡 "开始分析" 按钮的前置条件（SPEC FR-7 §5.2.1-3 微调 2）。
 *
 * 校验顺序：
 *   1) ≥1 张图（slots.filter(s => s.filled).length >= 1）
 *   2) face 必含（slots.some(s => s.filled && s.bodyPart === 'face')）
 *   3) ≥3 项档案已填（countFilledFields(profile) >= 3）
 *
 * 全部通过 → ok=true；
 * 任一失败 → ok=false + reason（用于 onSubmitUpload 决定 wx.showToast 还是 showModal）。
 */
export function checkSmartAnalyzePrerequisites(input: PrerequisiteInput): PrerequisiteResult {
  const { slots, profile } = input;

  // 校验 1：≥1 张图
  const filledCount = slots.filter((s) => s.filled).length;
  if (filledCount < 1) {
    return { ok: false, reason: 'no_photo' };
  }

  // 校验 2：face 必含
  const hasFace = slots.some((s) => s.filled && s.bodyPart === 'face');
  if (!hasFace) {
    return { ok: false, reason: 'no_face' };
  }

  // 校验 3：≥3 项档案
  const pFilled = countFilledFields(profile);
  if (pFilled < 3) {
    return {
      ok: false,
      reason: 'profile_insufficient',
      filledCount: pFilled,
      missing: 3 - pFilled,
    };
  }

  return { ok: true };
}

/** SSE body 构造输入。 */
export interface BuildBodyInput {
  text: string;
  imageKeys: string[];
  bodyParts: string[];
}

/** SSE body 构造输出（与后端 SendMessageBody schema 对齐）。 */
export interface BuildBodyOutput {
  text: string;
  image_keys: string[];
  body_parts: string[];
  profile?: UserProfile6Fields;
}

/**
 * V5.2.1-PR5 §修正（post-merge bugfix）· ActionSheet 3 选项决策。
 *
 * 背景：原实现用 wx.showModal（2 button），用户反馈：
 *   1) 没有"取消"选项（继续分析会被强制 = 降质量分析）
 *   2) iOS 点遮罩关不掉 modal（官方明示 wx.showModal 不支持）
 * 业界做法（小红书/抖音/企业微信）= 底部 ActionSheet，支持点遮罩关闭。
 *
 * 本函数把 tapIndex → 用户意图 抽成纯函数，便于 jest 测试与回滚。
 *
 * 注意：itemList 文案与顺序必须与 assistant-home/index.ts:onSubmitUpload 完全一致。
 */
export type ProfileInsufficientAction =
  | { kind: 'goto_profile' }
  | { kind: 'continue_fallback' }
  | { kind: 'cancel' };

export const PROFILE_INSUFFICIENT_ITEM_LIST = [
  '去完善档案',
  '继续分析（资料不足会降质量）',
  '稍后再分析',
] as const;

export function pickProfileInsufficientAction(tapIndex: number | undefined): ProfileInsufficientAction {
  if (tapIndex === 0) return { kind: 'goto_profile' };
  if (tapIndex === 1) return { kind: 'continue_fallback' };
  return { kind: 'cancel' }; // tapIndex === 2 / undefined / 越界
}

/**
 * 构造 smart_analyze SSE 调用的 body（SPEC FR-6）。
 *
 * profile 字段处理：
 *   - storage 有数据时（任一字段非 null）→ 包含 profile 字段
 *   - storage 全 null → 省略 profile 字段（后端 Pydantic Optional 兜底 None）
 *
 * 由 onSubmitUpload 在校验通过后调用，或 modal "继续分析" 分支调用。
 */
export function buildSmartAnalyzeBody(input: BuildBodyInput): BuildBodyOutput {
  const profile = readUserProfile();
  const pFilled = countFilledFields(profile);
  const body: BuildBodyOutput = {
    text: input.text,
    image_keys: input.imageKeys,
    body_parts: input.bodyParts,
  };
  if (pFilled > 0) {
    body.profile = profile;
  }
  return body;
}
