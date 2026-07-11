/**
 * V5.2.1-PR5 · 6 字段用户档案 storage helper。
 *
 * 真源：SPEC-V521-PR5-frontend-contract.md §FR-1。
 *
 * 设计要点：
 * 1. **单一数据源**：所有 6 字段（age_range / sitting_hours / focus_parts /
 *    intensity / preferred_time / skin_type）都从这里读写，禁止散落 wx.getStorageSync。
 * 2. **字段独立 key**：6 个字段各一个 storage key，避免 v2 不一致 bug
 *    （一个 JSON object 写失败全丢 vs 单字段 key 写失败只丢一个）。
 * 3. **字段命名 snake_case**：与后端 `User` ORM `assistant_profile` JSONB + DTO 对齐。
 * 4. **focus_parts 用 JSON**：storage 不支持数组，写入前 stringify，读出后 parse。
 * 5. **空字符串 → null**：wx.getStorageSync 未设置时返回空字符串，统一转为 null。
 *
 * 与 PR2 后端 `_invoke_llm_structured` 用的 6 字段 schema 强一致；
 * 后端收到 `profile` 字段后可直接喂给 LLM，不再走 `_rule_engine_fallback`（PR4 F4）。
 */

// 微信开发者工具内置 wx 全局类型（这里只声明本文件用到的最小子集，避免依赖整个 SDK）。
// 类型与 utils/request.ts 等其它生产文件实际用法一致（小程序 DevTools / 真机运行时 wx 由宿主注入）。
declare const wx: {
  getStorageSync(key: string): string;
  setStorageSync(key: string, value: string | number | boolean | object): void;
};

/** 6 字段用户档案类型（snake_case，与后端 JSONB schema 对齐）。 */
export interface UserProfile6Fields {
  age_range?: string | null;
  sitting_hours?: number | null;
  focus_parts?: string[] | null;
  intensity?: string | null;
  preferred_time?: string | null;
  skin_type?: string | null;
}

/** 6 个字段的 storage key 集中常量。 */
export const STORAGE_KEYS_PROFILE = {
  ageRange: 'profile_age_range',
  sittingHours: 'profile_sitting_hours',
  focusParts: 'profile_focus_parts',
  intensity: 'profile_intensity',
  preferredTime: 'profile_preferred_time',
  skinType: 'profile_skin_type',
} as const;

type StorageKey = (typeof STORAGE_KEYS_PROFILE)[keyof typeof STORAGE_KEYS_PROFILE];

function _get(key: StorageKey): string {
  // 微信小程序 wx.getStorageSync 同步读，未设置时返回空字符串
  return wx.getStorageSync(key) as string;
}

/** 读取 6 字段档案；未填字段返回 null。 */
export function readUserProfile(): UserProfile6Fields {
  const ageRangeRaw = _get(STORAGE_KEYS_PROFILE.ageRange);
  const sittingHoursRaw = _get(STORAGE_KEYS_PROFILE.sittingHours);
  const focusPartsRaw = _get(STORAGE_KEYS_PROFILE.focusParts);
  const intensityRaw = _get(STORAGE_KEYS_PROFILE.intensity);
  const preferredTimeRaw = _get(STORAGE_KEYS_PROFILE.preferredTime);
  const skinTypeRaw = _get(STORAGE_KEYS_PROFILE.skinType);

  // focus_parts JSON 解析；解析失败视为 null
  let focusParts: string[] | null = null;
  if (focusPartsRaw) {
    try {
      const parsed = JSON.parse(focusPartsRaw) as unknown;
      if (Array.isArray(parsed)) {
        focusParts = parsed.filter((x): x is string => typeof x === 'string');
      }
    } catch {
      focusParts = null;
    }
  }

  // sitting_hours Number 解析；解析失败视为 null
  let sittingHours: number | null = null;
  if (sittingHoursRaw) {
    const n = Number(sittingHoursRaw);
    if (Number.isFinite(n)) {
      sittingHours = n;
    }
  }

  return {
    age_range: ageRangeRaw || null,
    sitting_hours: sittingHours,
    focus_parts: focusParts,
    intensity: intensityRaw || null,
    preferred_time: preferredTimeRaw || null,
    skin_type: skinTypeRaw || null,
  };
}

function _set(key: StorageKey, value: string | number | null | undefined): void {
  if (value === null || value === undefined || value === '') return; // 跳过 null/空字段（不写 storage）
  wx.setStorageSync(key, value as string | number);
}

/**
 * 写入 6 字段档案；null 字段不写入 storage（保留旧值）。
 *
 * 调用方约定：需要"清空"时显式 `wx.removeStorageSync(key)`，不在本函数处理。
 */
export function writeUserProfile(p: UserProfile6Fields): void {
  _set(STORAGE_KEYS_PROFILE.ageRange, p.age_range);
  _set(STORAGE_KEYS_PROFILE.sittingHours, p.sitting_hours);
  if (p.focus_parts !== null && p.focus_parts !== undefined) {
    _set(STORAGE_KEYS_PROFILE.focusParts, JSON.stringify(p.focus_parts));
  }
  _set(STORAGE_KEYS_PROFILE.intensity, p.intensity);
  _set(STORAGE_KEYS_PROFILE.preferredTime, p.preferred_time);
  _set(STORAGE_KEYS_PROFILE.skinType, p.skin_type);
}

/** 计算已填字段数（focus_parts 视为已填当且仅当非空数组）。 */
export function countFilledFields(p: UserProfile6Fields): number {
  let n = 0;
  if (p.age_range) n++;
  if (p.sitting_hours !== null && p.sitting_hours !== undefined) n++;
  if (Array.isArray(p.focus_parts) && p.focus_parts.length > 0) n++;
  if (p.intensity) n++;
  if (p.preferred_time) n++;
  if (p.skin_type) n++;
  return n;
}
