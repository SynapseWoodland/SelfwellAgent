/**
 * profile-edit/index.smart-body.ts
 *
 * V5.2.1-PR5.1 抽出的纯函数库（与 pages/profile-edit/index.ts 一一对应）。
 * 与 assistant-home/index.smart-body.ts 的设计思路一致：
 * - 不调 wx.showToast / wx.request / wx.showModal（无副作用）
 * - jest 直接 import 测试，避免 mock Page() 生命周期
 *
 * 真源：SPEC-V521-PR5.1-profile-edit-subpage.md §FR-2 / §FR-3 / §FR-4。
 *
 * 三类导出：
 * 1. `buildProfileBackendPayload(localProfile)` —— 6 字段 → 5 字段后端 schema 映射
 *    （skin_type 不上送；sitting_hours number → string）
 * 2. `validateProfileRequiredFields(localProfile)` —— intensity + skin_type 必填校验
 * 3. `PICK_PROFILE_TARGET_PATH` —— 「用户档案」按钮跳转常量子页路径
 */

import type { UserProfile6Fields } from '../../utils/profile-storage';

/**
 * 本地 6 字段表单 state（与 pages/profile-edit/index.ts data 同 shape）。
 * 字段允许 null（前端未填）；运行时校验（onSubmitProfile 会把 '' 转 null）。
 * 注意：sitting_hours 是 number | null（WXML input 是 string，但 handler 内部 Number()），
 * focus_parts 是 string[] | null（前端 array；空数组或 null 都视为"未填"）。
 */
export type LocalProfileState = {
  age_range: string | null;
  sitting_hours: number | null;
  focus_parts: string[] | null;
  intensity: string | null;
  preferred_time: string | null;
  skin_type: string | null;
};

/**
 * 后端 POST /users/profile 入参（5 字段）。
 *
 * 与 backend/app/api/routers/users_v1.py:36-43 的 ProfileUpdateRequest 对齐：
 * - age_range:        str | None
 * - focus_parts:      list[str] | None
 * - intensity:        str | None
 * - preferred_time:   str | None
 * - sitting_hours:    str | None    ← 注意：number 转 string（后端 schema 是 str）
 *
 * 注意：skin_type 不在上送字段（后端 User ORM 没有列；PR3/T15 未列入 update_user_profile）。
 */
export type BackendProfilePayload = {
  age_range: string | null;
  sitting_hours: string | null;
  focus_parts: string[] | null;
  intensity: string | null;
  preferred_time: string | null;
};

/**
 * 「用户档案」P06 设置项点击后跳转的子页路径。
 *
 * 与 app.json §pages 注册必须一致；profile-edit 是普通页（不在 tabBar 列表里），
 * 必须用 wx.navigateTo，不可用 wx.switchTab。
 *
 * 历史教训：profile/index 是 tabBar 页（app.json §tabBar），navigateTo 会 fail silently。
 * 见 SPEC §FR-2 / §FR-7.1。
 */
export const PICK_PROFILE_TARGET_PATH = '/pages/profile-edit/index';

/**
 * FR-3 · 本地 6 字段 → 后端 5 字段 payload。
 *
 * 关键约束：
 * - skin_type 不上送（后端 schema 不收；前端 SSE 入参需要，保留本地）
 * - sitting_hours: number → string（后端 schema `sitting_hours: str`）
 * - sitting_hours=0 是有效值（用户填写 0 小时不视为"未填"），强制转 '0'
 * - 空字符串视为 null（前端 "" 是 from 空表单字段）
 */
export function buildProfileBackendPayload(
  local: LocalProfileState,
): BackendProfilePayload {
  return {
    age_range: local.age_range || null,
    sitting_hours:
      local.sitting_hours === null || local.sitting_hours === undefined
        ? null
        : String(local.sitting_hours),
    focus_parts: Array.isArray(local.focus_parts) && local.focus_parts.length > 0
      ? local.focus_parts
      : null,
    intensity: local.intensity || null,
    preferred_time: local.preferred_time || null,
    // 故意不返回 skin_type — 后端 update_user_profile 不收；
    // 此字段前端本地保留，供 assistant-home SSE 入参 `buildSmartAnalyzeBody`
    // 与智能管家 LLM 上下文使用（见 utils/profile-storage.ts）。
  };
}

/**
 * FR-3 · 必填校验（前端 intensity + skin_type）。
 *
 * 注意：PR5 在 pages/profile/index.ts 同样有这个校验，但散落在
 * onSubmitProfile 里且未抽函数；本函数为 PR5.1 子页 handler 与（未来若做
 * P06 表单回归）复用，jest 直接覆盖。
 */
export type ProfileValidationOk = { ok: true };
export type ProfileValidationErr = { ok: false; reason: 'intensity_missing' | 'skin_type_missing' };
export type ProfileValidationResult = ProfileValidationOk | ProfileValidationErr;

export function validateProfileRequiredFields(
  partial: Pick<LocalProfileState, 'intensity' | 'skin_type'>,
): ProfileValidationResult {
  if (!partial.intensity || partial.intensity === '') {
    // intensity 优先提示在前（与 toast 文案"请填写必填项：干预强度"对齐）
    return { ok: false, reason: 'intensity_missing' };
  }
  if (!partial.skin_type || partial.skin_type === '') {
    return { ok: false, reason: 'skin_type_missing' };
  }
  return { ok: true };
}

/**
 * FR-3 重导出：从 utils/profile-storage.ts 引一份类型，避免在测试 import 时
 * 需要再 import 路径深入；不引入新类型。
 */
export type { UserProfile6Fields };
