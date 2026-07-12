import { ApiException, post } from '../../utils/request';

const PRESET_DAYS = [3, 7, 14] as const;
type PresetDays = (typeof PRESET_DAYS)[number];
type PeriodValue = PresetDays | 'custom';

interface PeriodChip {
  label: string;
  value: PeriodValue;
}

interface ContextDirection {
  num: number;
  title: string;
  level: string;
  description: string;
}

interface AIMessageContextPhotos {
  directions: ContextDirection[];
  tags: string[];
  summary: string;
  injected_at: string;
}

interface RecallPhoto {
  url: string;
  caption?: string;
  created_at?: string;
}

interface RecallResult {
  recall_id: string;
  trigger: string;
  days_offset: number;
  summary: string;
  encourage: string;
  referenced_photos?: RecallPhoto[];
  context_photos?: AIMessageContextPhotos;
  created_at: string;
}

interface PageData {
  periods: PeriodChip[];
  selectedPeriod: PeriodValue;
  daysOffset: number;
  customDate: string;
  maxDate: string;
  customPickerVisible: boolean;
  loading: boolean;
  errorMessage: string;
  recall: RecallResult | null;
}

function formatDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function dateForOffset(daysOffset: number): string {
  const date = new Date();
  date.setDate(date.getDate() - daysOffset);
  return formatDate(date);
}

function daysFromDate(dateValue: string): number {
  const selected = new Date(`${dateValue}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const offset = Math.round((today.getTime() - selected.getTime()) / 86_400_000);
  return Math.max(1, Math.min(365, offset));
}

Page({
  data: {
    periods: [
      { label: '3 天前', value: 3 },
      { label: '7 天前', value: 7 },
      { label: '14 天前', value: 14 },
      { label: '自定义', value: 'custom' },
    ],
    selectedPeriod: 7,
    daysOffset: 7,
    customDate: dateForOffset(7),
    maxDate: formatDate(new Date()),
    customPickerVisible: false,
    loading: false,
    errorMessage: '',
    recall: null,
  } as PageData,

  onLoad(options: { trigger?: string; days_offset?: string }) {
    const parsedOffset = Number.parseInt(options?.days_offset ?? '7', 10);
    const daysOffset = Number.isInteger(parsedOffset) && parsedOffset > 0 ? parsedOffset : 7;
    const selectedPeriod: PeriodValue = PRESET_DAYS.includes(daysOffset as PresetDays)
      ? (daysOffset as PresetDays)
      : 'custom';
    this.setData({
      selectedPeriod,
      daysOffset,
      customDate: dateForOffset(daysOffset),
    });
    void this.loadRecall(options?.trigger ?? 'user_manual', daysOffset);
  },

  onBack() {
    wx.navigateBack();
  },

  onSelectPeriod(event: WechatMiniprogram.TapEvent) {
    const value = event.currentTarget.dataset.value as PeriodValue;
    if (value === 'custom') {
      this.setData({ selectedPeriod: 'custom', customPickerVisible: true });
      return;
    }
    this.setData({ selectedPeriod: value, daysOffset: value });
    void this.loadRecall('user_manual', value);
  },

  onCustomDateChange(event: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ customDate: String(event.detail.value) });
  },

  onCancelCustom() {
    this.setData({ customPickerVisible: false });
  },

  onConfirmCustom() {
    const daysOffset = daysFromDate(this.data.customDate);
    this.setData({
      selectedPeriod: 'custom',
      daysOffset,
      customPickerVisible: false,
    });
    void this.loadRecall('user_manual', daysOffset);
  },

  async loadRecall(trigger: string, daysOffset: number) {
    this.setData({ loading: true, errorMessage: '' });
    try {
      const recall = await post<RecallResult, { trigger: string; days_offset: number }>(
        '/butler/recall',
        { trigger, days_offset: daysOffset },
      );
      this.setData({ recall, loading: false });
    } catch (error) {
      this.setData({
        recall: null,
        loading: false,
        errorMessage: error instanceof ApiException ? error.message : '暂时想不起这段记录，请稍后再试',
      });
    }
  },

  onContinueChat() {
    if (this.data.recall) {
      wx.setStorageSync('recall_chat_context', this.data.recall);
    }
    wx.switchTab({ url: '/pages/assistant-home/index' });
  },

  async onSaveAsDiary() {
    const summary = this.data.recall?.summary?.trim() ?? '';
    if (!summary) {
      wx.showToast({ title: '还没有可保存的回忆', icon: 'none' });
      return;
    }
    try {
      await post('/feedback', {
        feedback_type: 'mood_text',
        text_content: summary,
      });
      wx.showToast({ title: '已保存为日记', icon: 'success' });
    } catch (error) {
      wx.showToast({
        title: error instanceof ApiException ? error.message : '保存失败，请稍后再试',
        icon: 'none',
      });
    }
  },
});
