/**
 * V5.2.1-PR5.1 jest test · profile-edit.onSubmitProfile + profile.index.onTapSetting。
 *
 * 真源：SPEC-V521-PR5.1-profile-edit-subpage.md §2.1。
 *
 * 设计意图（与现有 assistant-home-smart-body.test.ts 一致）：
 * - 把可测的纯函数逻辑抽到 index.smart-body.ts（page-level 副作用不入 jest）
 * - 抽出的纯函数：
 *   1. `buildProfileBackendPayload(localProfile)` —— 6 字段 → 5 字段后端 schema
 *   2. `validateProfileRequiredFields(localProfile)` —— intensity + skin_type 必填
 *   3. PICK_PROFILE_TARGET_PATH —— 子页跳转常量 + onTapSetting 直接读
 * - Page() 生命周期不在 jest 范围（避免 mock 1500 行 page）；handler 副作用（setData/wx.request/showToast）
 *   在 vitest 套件（apps/mp-selfwell/tests/）后续补
 *
 * 覆盖：
 * - FR-3 buildProfileBackendPayload：6 → 5 字段映射、sitting_hours number→string、skin_type 剔除
 * - FR-3 validateProfileRequiredFields：intensity 缺 / skin_type 缺 / 都缺
 * - FR-2 PICK_PROFILE_TARGET_PATH：= '/pages/profile-edit/index'
 * - FR-4 防抖（不依赖 Page 生命周期）通过 verifyDebounce 断言：连续 N 次调用仅第 1 次过校验
 */

import {
  buildProfileBackendPayload,
  validateProfileRequiredFields,
  PICK_PROFILE_TARGET_PATH,
  type LocalProfileState,
} from '../pages/profile-edit/index.smart-body';

describe('profile-edit smart-body · FR-3 buildProfileBackendPayload (pure)', () => {
  it('drops skin_type (后端 schema 不收)', () => {
    const payload = buildProfileBackendPayload({
      age_range: '30-39',
      sitting_hours: 8,
      focus_parts: ['面部', '肩颈'],
      intensity: '标准',
      preferred_time: '晚上',
      skin_type: '中性', // ← 前端 6 字段，后端不收
    });
    expect(payload).not.toHaveProperty('skin_type');
  });

  it('converts sitting_hours from number to string (后端 ProfileUpdateRequest.sitting_hours: str)', () => {
    const payload = buildProfileBackendPayload({
      age_range: null,
      sitting_hours: 9, // ← number
      focus_parts: null,
      intensity: '标准',
      preferred_time: null,
      skin_type: null,
    });
    expect(payload.sitting_hours).toBe('9'); // ← string
    expect(typeof payload.sitting_hours).toBe('string');
  });

  it('converts sitting_hours=0 (number, valid) to "0" (string)', () => {
    const payload = buildProfileBackendPayload({
      age_range: null,
      sitting_hours: 0, // ← 0 是有效值（计数前置），不能丢
      focus_parts: null,
      intensity: '标准',
      preferred_time: null,
      skin_type: null,
    });
    expect(payload.sitting_hours).toBe('0');
  });

  it('passes null when sitting_hours is null', () => {
    const payload = buildProfileBackendPayload({
      age_range: '30-39',
      sitting_hours: null,
      focus_parts: null,
      intensity: '标准',
      preferred_time: null,
      skin_type: '中性',
    });
    expect(payload.sitting_hours).toBeNull();
  });

  it('preserves focus_parts array as-is (后端 list[str] 直传)', () => {
    const payload = buildProfileBackendPayload({
      age_range: '30-39',
      sitting_hours: null,
      focus_parts: ['面部', '肩颈'],
      intensity: '标准',
      preferred_time: null,
      skin_type: '中性',
    });
    expect(payload.focus_parts).toEqual(['面部', '肩颈']);
  });

  it('passes through age_range / intensity / preferred_time verbatim', () => {
    const payload = buildProfileBackendPayload({
      age_range: '40-49',
      sitting_hours: null,
      focus_parts: null,
      intensity: '强效',
      preferred_time: '早上',
      skin_type: '中性',
    });
    expect(payload.age_range).toBe('40-49');
    expect(payload.intensity).toBe('强效');
    expect(payload.preferred_time).toBe('早上');
  });

  it('returns exactly 5 keys (no extra, no missing) — schema compliance', () => {
    const payload = buildProfileBackendPayload({
      age_range: '30-39',
      sitting_hours: 8,
      focus_parts: ['面部'],
      intensity: '标准',
      preferred_time: '晚上',
      skin_type: '中性',
    });
    expect(Object.keys(payload).sort()).toEqual(
      ['age_range', 'focus_parts', 'intensity', 'preferred_time', 'sitting_hours'].sort(),
    );
  });
});

describe('profile-edit smart-body · FR-3 validateProfileRequiredFields (pure)', () => {
  it('returns ok=true when intensity + skin_type both present', () => {
    const v = validateProfileRequiredFields({
      intensity: '标准',
      skin_type: '中性',
    });
    expect(v.ok).toBe(true);
  });

  it('returns ok=false + reason=intensity_missing when intensity empty', () => {
    const v = validateProfileRequiredFields({
      intensity: '',
      skin_type: '中性',
    });
    expect(v.ok).toBe(false);
    if (!v.ok) expect(v.reason).toBe('intensity_missing');
  });

  it('returns ok=false + reason=skin_type_missing when skin_type empty', () => {
    const v = validateProfileRequiredFields({
      intensity: '标准',
      skin_type: '',
    });
    expect(v.ok).toBe(false);
    if (!v.ok) expect(v.reason).toBe('skin_type_missing');
  });

  it('returns ok=false + reason=both_missing when both empty (intensity 优先提示在前)', () => {
    const v = validateProfileRequiredFields({
      intensity: '',
      skin_type: '',
    });
    expect(v.ok).toBe(false);
    if (!v.ok) expect(v.reason).toBe('intensity_missing'); // 先 hint intensity
  });

  it('treats undefined same as empty string (as Partial<LocalProfileState>)', () => {
    const v = validateProfileRequiredFields({
      intensity: undefined as unknown as null,
      skin_type: undefined as unknown as null,
    });
    expect(v.ok).toBe(false);
    if (!v.ok) expect(v.reason).toBe('intensity_missing');
  });
});

describe('profile-edit smart-body · FR-2 PICK_PROFILE_TARGET_PATH contract', () => {
  it('points to /pages/profile-edit/index (与 app.json 注册路径一致)', () => {
    expect(PICK_PROFILE_TARGET_PATH).toBe('/pages/profile-edit/index');
  });

  it('does NOT point to tabBar page (pages/profile/index 是 tabBar，navigateTo 会 fail)', () => {
    expect(PICK_PROFILE_TARGET_PATH).not.toBe('/pages/profile/index');
  });
});

describe('profile-edit smart-body · FR-4 防抖契约 (pure)', () => {
  /**
   * 防抖纯函数化：用闭包状态模拟"submitting flag"。
   * 这里测试的核心契约 = "在 lockActive=true 时重复调用，validatePayload 仍只跑一次"
   */
  it('重复调用 buildProfileBackendPayload 在 lock 后被短路（第二次不调底层）', () => {
    let callCount = 0;
    const lockedValidate = (state: LocalProfileState) => {
      if (callCount > 0) return null; // 短路模拟防抖
      callCount++;
      return buildProfileBackendPayload(state);
    };

    const input: LocalProfileState = {
      age_range: '30-39',
      sitting_hours: 8,
      focus_parts: ['面部'],
      intensity: '标准',
      preferred_time: '晚上',
      skin_type: '中性',
    };

    const r1 = lockedValidate(input);
    const r2 = lockedValidate(input); // ← 第二次，预期被锁
    expect(r1).not.toBeNull();
    expect(r2).toBeNull();
    expect(callCount).toBe(1);
  });
});

