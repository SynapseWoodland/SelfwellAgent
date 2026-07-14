/**
 * recall-compare/index.ts
 * PR-V2-D · 对齐 15e-recall-cta-buttons.html 原型
 * 双时间线对比：Day N vs Day today（照片 + 摘要 + AI鼓励）
 * 后端端点：
 *   - GET /butler/recall/day/:day — 按天获取回忆快照
 *   - POST /feedback — 写入心情日记
 */
import { get } from '../../utils/request';

interface RecallPhoto {
  url: string;
  caption: string;
}

interface RecallSnapshot {
  baselineDay: number;
  baselineDate: string;
  baselinePhotos: RecallPhoto[];
  baseline_report_text: string;
  currentDay: number;
  currentDate: string;
  currentPhotos: RecallPhoto[];
  current_report_text: string;
  ai_reply_text: string;
  intro_text: string;
}

interface PageData {
  activeDay: number;
  snapshot: RecallSnapshot | null;
  introText: string;
  loading: boolean;
}

const DAYS = [7, 14, 21] as const;
type DayOption = 7 | 14 | 21;

Page({
  data: {
    activeDay: 7,
    snapshot: null,
    introText: '',
    loading: false,
  } as PageData,

  onLoad(options: Record<string, string | undefined>) {
    const raw = options?.day ? parseInt(String(options.day), 10) : 7;
    const day = DAYS.includes(raw as DayOption) ? (raw as DayOption) : 7;
    this.setData({ activeDay: day });
    void this._loadSnapshot(day);
  },

  onSelectDay(e: WechatMiniprogram.TapEvent) {
    const day = Number((e.currentTarget.dataset as { day?: number }).day ?? 7) as DayOption;
    if (day === this.data.activeDay) return;
    this.setData({ activeDay: day, snapshot: null });
    void this._loadSnapshot(day);
  },

  async _loadSnapshot(day: number) {
    this.setData({ loading: true });
    try {
      const raw = (await get<Record<string, unknown>>(`/butler/recall/day/${day}`)) ?? {};
      const photos = (arr: unknown[]) =>
        (Array.isArray(arr) ? arr : []).map((p) => ({
          url: String((p as { url?: unknown }).url ?? ''),
          caption: String((p as { caption?: unknown }).caption ?? ''),
        }));
      const snapshot: RecallSnapshot = {
        baselineDay: day,
        baselineDate: String(raw['baseline_date'] ?? ''),
        baselinePhotos: photos(raw['baseline_photos']),
        baseline_report_text: String(raw['baseline_report_text'] ?? ''),
        currentDay: 0,
        currentDate: new Date().toLocaleDateString('zh-CN'),
        currentPhotos: photos(raw['current_photos']),
        current_report_text: String(raw['current_report_text'] ?? ''),
        ai_reply_text: String(raw['ai_reply_text'] ?? '你已经在路上了，继续加油 🌿'),
        intro_text: String(raw['intro_text'] ?? raw['summary_text'] ?? ''),
      };
      this.setData({ snapshot, introText: snapshot.intro_text, loading: false });
    } catch {
      this.setData({ loading: false });
    }
  },

  onContinueChat() {
    wx.switchTab({ url: '/pages/assistant-home/index' });
  },

  onSaveAsDiary() {
    const summary = this.data.snapshot?.current_report_text ?? '';
    wx.navigateTo({
      url: `/pages/feedback-diary/index?source=recall&text=${encodeURIComponent(summary)}`,
    });
  },

  onNavBack() {
    wx.navigateBack();
  },
});
