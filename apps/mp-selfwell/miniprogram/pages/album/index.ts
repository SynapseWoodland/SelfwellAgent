/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.7 P17 我的时光 / 相册（V2 我的 Tab 子页）
 *
 * PR-5 · album 子页（不带 tabBar）
 * ─────────────────────────────────────────────────────────────────
 * - 顶部时间段切换（4 个 ISO 周 chip；默认本周）
 * - 照片网格（3 列）：GET /me/album/photos?week=YYYY-WNN
 * - 底部统计卡：GET /me/album/stats（总照片 / 连续打卡 / 日记数 / 在 App 天数）
 */

import { get, ApiException } from '../../utils/request';

interface AlbumPhoto {
  feedback_id: string;
  photo_url: string;
  body_part: string | null;
  feedback_type: string;
  created_at: string | null;
}

interface AlbumWeekData {
  week: string;
  count: number;
  photos: AlbumPhoto[];
}

interface AlbumStats {
  total_photos: number;
  total_checkin_days: number;
  total_diary_entries: number;
  days_in_app: number;
}

interface WeekChip {
  label: string;
  value: string;
}

interface AlbumData {
  /** 候选周列表（含最近 8 周） */
  weeks: WeekChip[];
  selectedWeek: string;
  loading: boolean;
  weekData: AlbumWeekData;
  stats: AlbumStats;
  errorMessage: string;
}

const INITIAL_STATS: AlbumStats = {
  total_photos: 0,
  total_checkin_days: 0,
  total_diary_entries: 0,
  days_in_app: 0,
};

/** 计算 ISO 周号（YYYY-WNN）；返回最近 8 周（含本周） */
function buildRecentWeeks(count: number): WeekChip[] {
  const out: WeekChip[] = [];
  const today = new Date();
  for (let i = 0; i < count; i += 1) {
    const d = new Date(today);
    d.setDate(today.getDate() - i * 7);
    const iso = isoWeek(d);
    const label = i === 0 ? `本周 ${iso}` : i === 1 ? '上周' : `${i} 周前`;
    out.push({ label, value: iso });
  }
  return out;
}

/** 计算 ISO 周字符串 YYYY-WNN（不依赖 date-fns） */
function isoWeek(date: Date): string {
  const target = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  // 周四所在年份 = ISO 周所在年份
  const dayNum = target.getUTCDay() || 7;
  target.setUTCDate(target.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(target.getUTCFullYear(), 0, 1));
  const weekNum = Math.ceil(((target.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return `${target.getUTCFullYear()}-W${String(weekNum).padStart(2, '0')}`;
}

Page<AlbumData>({
  data: {
    weeks: buildRecentWeeks(8),
    selectedWeek: '',
    loading: true,
    weekData: { week: '', count: 0, photos: [] },
    stats: { ...INITIAL_STATS },
    errorMessage: '',
  },

  onLoad() {
    const firstWeek = this.data.weeks[0]?.value ?? isoWeek(new Date());
    this.setData({ selectedWeek: firstWeek });
    void this.fetchAll(firstWeek);
  },

  async fetchAll(week: string) {
    this.setData({ loading: true, errorMessage: '' });
    try {
      const [weekResp, statsResp] = await Promise.all([
        get<AlbumWeekData>(`/me/album/photos?week=${encodeURIComponent(week)}`),
        get<AlbumStats>('/me/album/stats'),
      ]);
      this.setData({
        loading: false,
        weekData: weekResp ?? { week, count: 0, photos: [] },
        stats: statsResp ?? { ...INITIAL_STATS },
      });
    } catch (err) {
      const msg = err instanceof ApiException ? err.message : '加载失败，请下拉重试';
      this.setData({ loading: false, errorMessage: msg });
    }
  },

  onSelectWeek(e: WechatMiniprogram.BaseEvent) {
    const week = (e.currentTarget.dataset as { week?: string }).week;
    if (!week || week === this.data.selectedWeek) return;
    this.setData({ selectedWeek: week });
    void this.fetchAll(week);
  },

  onTapPhoto(e: WechatMiniprogram.BaseEvent) {
    const url = (e.currentTarget.dataset as { url?: string }).url;
    if (!url) return;
    wx.previewImage({ urls: [url], current: url });
  },
});