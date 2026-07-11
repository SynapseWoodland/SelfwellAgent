/**
 * V5.2.1-PR5 jest test · profile-storage 单元测试。
 *
 * 真源：SPEC-V521-PR5-frontend-contract.md §3.1。
 *
 * 覆盖：
 * - FR-1 readUserProfile: 空 storage 返回全 null 对象
 * - FR-1 writeUserProfile: 写入触发 6 次 setStorageSync
 * - FR-1 countFilledFields: 正确计算已填字段数
 *
 * 注意：
 * - jest.config.js testEnvironment='node'，setup.ts 注入全局 wx mock
 * - wx.getStorageSync 默认返回 ''（setup.ts:69），与 profile-storage 内部
 *   "空字符串 → null" 转换逻辑一致
 * - wx.setStorageSync 是 jest.fn()，可以用 mock.calls 断言调用次数
 */

import {
  readUserProfile,
  writeUserProfile,
  countFilledFields,
  STORAGE_KEYS_PROFILE,
} from '../utils/profile-storage';

const wx = () => (globalThis as unknown as { wx: { getStorageSync: jest.Mock; setStorageSync: jest.Mock } }).wx;

describe('profile-storage · FR-1 read/write/count', () => {
  beforeEach(() => {
    wx().getStorageSync.mockReset();
    wx().setStorageSync.mockReset();
    wx().getStorageSync.mockReturnValue('');
  });

  describe('readUserProfile', () => {
    it('returns nulls for all 6 fields when storage is empty (default mock)', () => {
      const p = readUserProfile();
      expect(p).toEqual({
        age_range: null,
        sitting_hours: null,
        focus_parts: null,
        intensity: null,
        preferred_time: null,
        skin_type: null,
      });
      // 6 个字段全部读取了一次
      expect(wx().getStorageSync).toHaveBeenCalledTimes(6);
    });

    it('returns actual values when storage has data', () => {
      const store: Record<string, string> = {
        [STORAGE_KEYS_PROFILE.ageRange]: '30-39',
        [STORAGE_KEYS_PROFILE.sittingHours]: '8',
        [STORAGE_KEYS_PROFILE.focusParts]: '["面部","肩颈"]',
        [STORAGE_KEYS_PROFILE.intensity]: '标准',
        [STORAGE_KEYS_PROFILE.preferredTime]: '晚上',
        [STORAGE_KEYS_PROFILE.skinType]: '中性',
      };
      wx().getStorageSync.mockImplementation((key: string) => store[key] ?? '');

      const p = readUserProfile();
      expect(p.age_range).toBe('30-39');
      expect(p.sitting_hours).toBe(8);
      expect(p.focus_parts).toEqual(['面部', '肩颈']);
      expect(p.intensity).toBe('标准');
      expect(p.preferred_time).toBe('晚上');
      expect(p.skin_type).toBe('中性');
    });

    it('returns null for individual field when storage value is empty string', () => {
      wx().getStorageSync.mockImplementation((key: string) =>
        key === STORAGE_KEYS_PROFILE.intensity ? '' : 'some-value'
      );
      const p = readUserProfile();
      expect(p.intensity).toBeNull();
      expect(p.age_range).toBe('some-value');
    });
  });

  describe('writeUserProfile', () => {
    it('persists all 6 fields via 6 setStorageSync calls', () => {
      writeUserProfile({
        age_range: '30-39',
        sitting_hours: 8,
        focus_parts: ['面部'],
        intensity: '标准',
        preferred_time: '晚上',
        skin_type: '中性',
      });

      // 6 个字段每个一次 setStorageSync 调用
      expect(wx().setStorageSync).toHaveBeenCalledTimes(6);

      // 验证每个调用都用了正确的 storage key + 值
      expect(wx().setStorageSync).toHaveBeenCalledWith(STORAGE_KEYS_PROFILE.ageRange, '30-39');
      expect(wx().setStorageSync).toHaveBeenCalledWith(STORAGE_KEYS_PROFILE.sittingHours, 8);
      expect(wx().setStorageSync).toHaveBeenCalledWith(
        STORAGE_KEYS_PROFILE.focusParts,
        JSON.stringify(['面部'])
      );
      expect(wx().setStorageSync).toHaveBeenCalledWith(STORAGE_KEYS_PROFILE.intensity, '标准');
      expect(wx().setStorageSync).toHaveBeenCalledWith(STORAGE_KEYS_PROFILE.preferredTime, '晚上');
      expect(wx().setStorageSync).toHaveBeenCalledWith(STORAGE_KEYS_PROFILE.skinType, '中性');
    });

    it('serializes focus_parts as JSON string for storage (storage does not support arrays)', () => {
      writeUserProfile({
        age_range: null,
        sitting_hours: null,
        focus_parts: ['面部', '肩颈', '眼周'],
        intensity: null,
        preferred_time: null,
        skin_type: null,
      });

      expect(wx().setStorageSync).toHaveBeenCalledWith(
        STORAGE_KEYS_PROFILE.focusParts,
        JSON.stringify(['面部', '肩颈', '眼周'])
      );
    });

    it('writes 0 setStorageSync calls when all fields are null (no-op)', () => {
      writeUserProfile({
        age_range: null,
        sitting_hours: null,
        focus_parts: null,
        intensity: null,
        preferred_time: null,
        skin_type: null,
      });
      expect(wx().setStorageSync).toHaveBeenCalledTimes(0);
    });
  });

  describe('countFilledFields', () => {
    it('returns 0 when all fields are null', () => {
      const n = countFilledFields({
        age_range: null,
        sitting_hours: null,
        focus_parts: null,
        intensity: null,
        preferred_time: null,
        skin_type: null,
      });
      expect(n).toBe(0);
    });

    it('returns 6 when all fields are filled', () => {
      const n = countFilledFields({
        age_range: '30-39',
        sitting_hours: 8,
        focus_parts: ['面部'],
        intensity: '标准',
        preferred_time: '晚上',
        skin_type: '中性',
      });
      expect(n).toBe(6);
    });

    it('counts focus_parts as filled only when array is non-empty', () => {
      const n = countFilledFields({
        age_range: '30-39',
        sitting_hours: null,
        focus_parts: [], // 空数组 = 未填
        intensity: '标准',
        preferred_time: null,
        skin_type: null,
      });
      expect(n).toBe(2);
    });

    it('counts sitting_hours=0 as filled (not null)', () => {
      const n = countFilledFields({
        age_range: null,
        sitting_hours: 0,
        focus_parts: null,
        intensity: null,
        preferred_time: null,
        skin_type: null,
      });
      expect(n).toBe(1);
    });

    it('mixed 5 filled + 1 null → 5', () => {
      const n = countFilledFields({
        age_range: '30-39',
        sitting_hours: 8,
        focus_parts: ['面部'],
        intensity: '标准',
        preferred_time: '晚上',
        skin_type: null, // 唯一未填
      });
      expect(n).toBe(5);
    });
  });

  describe('STORAGE_KEYS_PROFILE · contract', () => {
    it('exposes exactly 6 keys with snake_case-prefixed values', () => {
      const keys = Object.keys(STORAGE_KEYS_PROFILE);
      expect(keys).toHaveLength(6);
      const values = Object.values(STORAGE_KEYS_PROFILE);
      for (const v of values) {
        expect(v).toMatch(/^profile_[a-z_]+$/);
      }
    });
  });
});
