/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.7 P19 通知设置（V2 我的 Tab 子页）
 * FIGMA  : docs/design/figma-pixso-spec/pages/19-notifications.html
 *
 * PR-5 · 通知设置子页（不带 tabBar）
 * ─────────────────────────────────────────────────────────────────
 * - 顶部：推送通道开关（每日打卡 / 每周回忆 / 反馈确认 / 方案里程碑 / 相册解锁 / 抱抱卡）
 * - PUT /api/v1/me/notification-settings 调后端契约
 * - GET /api/v1/me/notification-settings 首次访问自动 seed（后端兜底）
 * - 防抖闸门：submitting 锁 + 仅 dirty 字段才 PUT（PR-2 接受 prefs 部分替换）
 */

import { get, put, ApiException } from '../../utils/request';

/** 后端 pref_key 白名单（与 notification_service.DEFAULT_PREF_VALUES 字段对齐）
 *  不在白名单的 pref_key 一律不渲染，避免前端误改后端默认 6 键之外的脏数据。
 */
interface PrefValue {
  enabled?: boolean;
  time?: string;
}

interface NotificationPrefRow {
  prefKey: string;
  prefLabel: string;
  prefHint: string;
  enabled: boolean;
  time: string;
}

interface NotificationSettingsData {
  loading: boolean;
  submitting: boolean;
  prefs: NotificationPrefRow[];
  errorMessage: string;
  /** 保存成功 toast 一次性标志 */
  savedFlag: boolean;
}

const PREF_LABELS: Record<string, { label: string; hint: string }> = {
  daily_checkin: { label: '每日打卡提醒', hint: '固定时间推送，鼓励你坚持记录' },
  weekly_recall: { label: '每周主动回忆', hint: '在固定时间回顾过去 7 天的变化' },
  feedback_ack: { label: '反馈确认', hint: '收到反馈后立即推送一条暖心回应' },
  plan_milestone: { label: '方案里程碑', hint: '关键节点（如 Day 7 / Day 14）触发' },
  album_unlock: { label: '相册解锁提醒', hint: '相册达到一定数量时推送' },
  hug_card_ready: { label: '抱抱卡准备好', hint: '生成可分享的抱抱卡时推送' },
};

/** 排列顺序：按白名单顺序固定；后端返回的是 dict map，无序 */
const PREF_ORDER: ReadonlyArray<string> = [
  'daily_checkin',
  'weekly_recall',
  'feedback_ack',
  'plan_milestone',
  'album_unlock',
  'hug_card_ready',
];

/** 从 prefs map（后端 GET 响应）→ UI 列表（含默认值兜底） */
function buildRows(prefs: Record<string, PrefValue>): NotificationPrefRow[] {
  return PREF_ORDER.map((key) => {
    const meta = PREF_LABELS[key] ?? { label: key, hint: '' };
    const v = prefs[key] ?? {};
    return {
      prefKey: key,
      prefLabel: meta.label,
      prefHint: meta.hint,
      enabled: v.enabled !== false,
      time: typeof v.time === 'string' ? v.time : '',
    };
  });
}

/** 把 UI 行 → 后端 PUT 接受的 prefs dict（只含 dirty 字段；本实现为全量替换） */
function rowsToPayload(rows: NotificationPrefRow[]): Record<string, PrefValue> {
  const out: Record<string, PrefValue> = {};
  for (const r of rows) {
    const v: PrefValue = { enabled: r.enabled };
    if (r.time) v.time = r.time;
    out[r.prefKey] = v;
  }
  return out;
}

Page<NotificationSettingsData>({
  data: {
    loading: true,
    submitting: false,
    prefs: [],
    errorMessage: '',
    savedFlag: false,
  },

  onLoad() {
    void this.fetchSettings();
  },

  async fetchSettings() {
    this.setData({ loading: true, errorMessage: '' });
    try {
      const resp = await get<{ prefs: Record<string, PrefValue>; total: number }>(
        '/me/notification-settings',
      );
      const rows = buildRows(resp?.prefs ?? {});
      this.setData({ prefs: rows, loading: false });
    } catch (err) {
      const msg = err instanceof ApiException ? err.message : '加载失败，请下拉重试';
      this.setData({ loading: false, errorMessage: msg });
    }
  },

  onRetry() {
    void this.fetchSettings();
  },

  onToggleEnabled(e: WechatMiniprogram.BaseEvent) {
    const key = (e.currentTarget.dataset as { key?: string }).key;
    if (!key) return;
    const next = this.data.prefs.map((row) =>
      row.prefKey === key ? { ...row, enabled: !row.enabled } : row,
    );
    this.setData({ prefs: next });
  },

  onChangeTime(e: WechatMiniprogram.BaseEvent) {
    const key = (e.currentTarget.dataset as { key?: string }).key;
    const value = (e.detail as { value?: string }).value ?? '';
    const next = this.data.prefs.map((row) =>
      row.prefKey === key ? { ...row, time: value } : row,
    );
    this.setData({ prefs: next });
  },

  async onSubmit() {
    if (this.data.submitting) return;
    this.setData({ submitting: true });
    try {
      const payload = rowsToPayload(this.data.prefs);
      await put<unknown, { prefs: Record<string, PrefValue> }>(
        '/me/notification-settings',
        { prefs: payload },
      );
      this.setData({ savedFlag: true });
      wx.showToast({ title: '设置已保存', icon: 'success' });
    } catch (err) {
      const msg = err instanceof ApiException ? err.message : '保存失败，请稍后重试';
      wx.showToast({ title: msg, icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  },
});