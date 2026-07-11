/**
 * V5.2.1-PR5 jest test · assistant-home.onSubmitUpload + runSmartAnalyze 缺料校验。
 *
 * 真源：SPEC-V521-PR5-frontend-contract.md §3.1 + FR-7 + FR-6。
 *
 * 覆盖：
 * - FR-7 checkSmartAnalyzePrerequisites 纯函数：<1 张图 / 无 face / <3 项档案
 * - FR-6 buildSmartAnalyzeBody：profile 字段有/无/序列化/数字解析
 *
 * 设计意图（与 SPEC §FR-7 对齐）：
 * - checkSmartAnalyzePrerequisites 是**无副作用**纯函数（不调 wx.showToast/showModal）
 * - wx.showToast/showModal 由 assistant-home/index.ts:onSubmitUpload 内部触发
 * - jest 只测纯函数，Page() 生命周期不在本测试范围（避免 mock 1500 行 page）
 * - onSubmitUpload 集成测试在 vitest 套件（apps/mp-selfwell/tests/）后续补
 */

import {
  checkSmartAnalyzePrerequisites,
  buildSmartAnalyzeBody,
  type SmartAnalyzeSlotState,
} from '../pages/assistant-home/index.smart-body';

const wx = () =>
  (globalThis as unknown as {
    wx: {
      getStorageSync: jest.Mock;
      showToast: jest.Mock;
      showModal: jest.Mock;
      navigateTo: jest.Mock;
      request: jest.Mock;
    };
  }).wx;

/** 构造 N 张已填槽位，按 parts 顺序（face / head / shoulder_neck） */
function makeSlots(parts: Array<'face' | 'head' | 'shoulder_neck'>): SmartAnalyzeSlotState[] {
  return parts.map((p, i) => ({
    index: i,
    label: p === 'face' ? '面部' : p === 'head' ? '头部' : '肩颈',
    bodyPart: p,
    filled: true,
    filledUrl: `wxfile://tmp_${i}.jpg`,
  }));
}

describe('assistant-home smart-body · FR-7 checkSmartAnalyzePrerequisites (pure)', () => {
  beforeEach(() => {
    wx().getStorageSync.mockReset();
    wx().showToast.mockReset();
    wx().showModal.mockReset();
    wx().navigateTo.mockReset();
    wx().request.mockReset();
    wx().getStorageSync.mockReturnValue('');
  });

  describe('校验 1：<1 张图', () => {
    it('returns reason=no_photo when no slot is filled', () => {
      const result = checkSmartAnalyzePrerequisites({
        slots: [],
        profile: { intensity: '标准', skin_type: '中性', age_range: '30-39' },
      });
      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.reason).toBe('no_photo');
      }
    });

    it('returns reason=no_photo when slots exist but none filled', () => {
      const slots: SmartAnalyzeSlotState[] = [
        { index: 0, label: '面部', bodyPart: 'face', filled: false },
        { index: 1, label: '头部', bodyPart: 'head', filled: false },
      ];
      const result = checkSmartAnalyzePrerequisites({ slots, profile: {} });
      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.reason).toBe('no_photo');
      }
    });
  });

  describe('校验 2：无 face 图', () => {
    it('returns reason=no_face when only head/shoulder_neck filled, no face', () => {
      const slots = makeSlots(['head', 'shoulder_neck']);
      const result = checkSmartAnalyzePrerequisites({
        slots,
        profile: { intensity: '标准', skin_type: '中性', age_range: '30-39' },
      });
      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.reason).toBe('no_face');
      }
    });

    it('returns ok=true when face is included', () => {
      const slots = makeSlots(['head', 'face']);
      const result = checkSmartAnalyzePrerequisites({
        slots,
        profile: { intensity: '标准', skin_type: '中性', age_range: '30-39' },
      });
      expect(result.ok).toBe(true);
    });

    it('returns ok=true when 3 slots all filled including face', () => {
      const slots = makeSlots(['face', 'head', 'shoulder_neck']);
      const result = checkSmartAnalyzePrerequisites({
        slots,
        profile: { intensity: '标准', skin_type: '中性', age_range: '30-39' },
      });
      expect(result.ok).toBe(true);
    });
  });

  describe('校验 3：<3 项档案', () => {
    it('returns reason=profile_insufficient + filledCount=2 when 2 filled', () => {
      const slots = makeSlots(['face']);
      const result = checkSmartAnalyzePrerequisites({
        slots,
        profile: { intensity: '标准', skin_type: '中性' }, // 2 项
      });
      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.reason).toBe('profile_insufficient');
        expect(result.filledCount).toBe(2);
        expect(result.missing).toBe(1);
      }
    });

    it('returns ok=true when profile has exactly 3 filled fields', () => {
      const slots = makeSlots(['face']);
      const result = checkSmartAnalyzePrerequisites({
        slots,
        profile: { intensity: '标准', skin_type: '中性', age_range: '30-39' },
      });
      expect(result.ok).toBe(true);
    });

    it('returns filledCount=0 when profile is empty', () => {
      const slots = makeSlots(['face']);
      const result = checkSmartAnalyzePrerequisites({
        slots,
        profile: {},
      });
      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.reason).toBe('profile_insufficient');
        expect(result.filledCount).toBe(0);
        expect(result.missing).toBe(3);
      }
    });

    it('checks 校验顺序：no_photo > no_face > profile_insufficient', () => {
      // 即使 profile 为空，0 张图应优先报 no_photo
      const r1 = checkSmartAnalyzePrerequisites({ slots: [], profile: {} });
      expect(r1.ok).toBe(false);
      if (!r1.ok) expect(r1.reason).toBe('no_photo');

      // 1 张 head（无 face）+ profile 充足 → 应优先报 no_face 而非 profile_insufficient
      const slots = makeSlots(['head']);
      const r2 = checkSmartAnalyzePrerequisites({
        slots,
        profile: { intensity: '标准', skin_type: '中性', age_range: '30-39' },
      });
      expect(r2.ok).toBe(false);
      if (!r2.ok) expect(r2.reason).toBe('no_face');
    });
  });

  describe('happy path', () => {
    it('returns ok=true when ≥1 face + ≥3 profile fields', () => {
      const slots = makeSlots(['face']);
      const result = checkSmartAnalyzePrerequisites({
        slots,
        profile: {
          age_range: '30-39',
          sitting_hours: 8,
          intensity: '标准',
          skin_type: '中性',
        },
      });
      expect(result.ok).toBe(true);
    });
  });

  describe('side-effect freedom', () => {
    it('does NOT call any wx.* API (pure function contract)', () => {
      const slots = makeSlots(['face']);
      checkSmartAnalyzePrerequisites({
        slots,
        profile: { intensity: '标准', skin_type: '中性', age_range: '30-39' },
      });
      expect(wx().showToast).not.toHaveBeenCalled();
      expect(wx().showModal).not.toHaveBeenCalled();
      expect(wx().navigateTo).not.toHaveBeenCalled();
      expect(wx().request).not.toHaveBeenCalled();
    });
  });
});

describe('assistant-home smart-body · FR-6 buildSmartAnalyzeBody', () => {
  beforeEach(() => {
    wx().getStorageSync.mockReset();
    wx().getStorageSync.mockReturnValue('');
  });

  it('includes profile field when storage has data', () => {
    wx().getStorageSync.mockImplementation(
      (key: string) =>
        ({
          profile_age_range: '30-39',
          profile_intensity: '标准',
          profile_skin_type: '中性',
        })[key] ?? ''
    );
    const body = buildSmartAnalyzeBody({
      text: 'smart_analyze',
      imageKeys: ['assistant/uuid/img1.jpg'],
      bodyParts: ['face'],
    });
    expect(body).toMatchObject({
      text: 'smart_analyze',
      image_keys: ['assistant/uuid/img1.jpg'],
      body_parts: ['face'],
      profile: {
        age_range: '30-39',
        intensity: '标准',
        skin_type: '中性',
      },
    });
    expect(body.profile).toBeDefined();
  });

  it('omits profile when storage is empty (all null)', () => {
    const body = buildSmartAnalyzeBody({
      text: 'smart_analyze',
      imageKeys: ['k1'],
      bodyParts: ['face'],
    });
    // profile 全 null → body 不应含 profile 字段（后端 Pydantic Optional 默认 None 兜底）
    expect(body).not.toHaveProperty('profile');
  });

  it('handles focus_parts as JSON array (decoded from string)', () => {
    wx().getStorageSync.mockImplementation(
      (key: string) =>
        ({
          profile_focus_parts: '["面部","肩颈"]',
          profile_intensity: '强效',
          profile_skin_type: '油性',
        })[key] ?? ''
    );
    const body = buildSmartAnalyzeBody({
      text: 'smart_analyze',
      imageKeys: ['k1'],
      bodyParts: ['face', 'shoulder_neck'],
    });
    expect(body.profile).toMatchObject({
      focus_parts: ['面部', '肩颈'],
      intensity: '强效',
      skin_type: '油性',
    });
  });

  it('handles sitting_hours as number (parsed from string)', () => {
    wx().getStorageSync.mockImplementation(
      (key: string) =>
        ({
          profile_sitting_hours: '8',
          profile_intensity: '标准',
          profile_skin_type: '中性',
        })[key] ?? ''
    );
    const body = buildSmartAnalyzeBody({
      text: 'smart_analyze',
      imageKeys: ['k1'],
      bodyParts: ['face'],
    });
    expect(body.profile?.sitting_hours).toBe(8);
    expect(typeof body.profile?.sitting_hours).toBe('number');
  });

  it('preserves body text/imageKeys/bodyParts passthrough', () => {
    const body = buildSmartAnalyzeBody({
      text: 'smart_analyze',
      imageKeys: ['k1', 'k2'],
      bodyParts: ['face', 'head'],
    });
    expect(body.text).toBe('smart_analyze');
    expect(body.image_keys).toEqual(['k1', 'k2']);
    expect(body.body_parts).toEqual(['face', 'head']);
  });
});
