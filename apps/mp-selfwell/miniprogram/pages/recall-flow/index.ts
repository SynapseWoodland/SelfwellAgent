/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.5 P07 主动回忆对话流
 * 后端端点: POST /api/v1/butler/recall
 *
 * 行为：
 *   - onLoad 默认 days_offset=7，从 options 读 trigger/days_offset
 *   - 用户切换 chip → POST /butler/recall { trigger, days_offset }
 *   - 响应解析对齐 docs/api/openapi.yaml §RecallResponse（V1.1.1）
 *
 * FE-FIX-09 字段映射（与 openapi.yaml RecallResponse 1:1）：
 *   - recall_id（替代旧 id）
 *   - referenced_feedbacks 是内联对象数组（id/body_part/snippet/feedback_type/photo_url/created_at）
 *   - referenced_photos 是内联对象数组（url/body_part/uploaded_at）
 *   - context_photos 是内联对象数组（url/caption）—— V1.1.1 之前在 recall-flow/index.ts
 *     中错把 context_photos 当成 AIMessageContextPhotos 对象（带 summary/directions/tags），
 *     本次按 openapi 修正为 array<{url, caption}>
 *   - summary / encourage / safety_passed / created_at / trigger / days_offset
 */
import { ApiException, post } from '../../utils/request';

const PRESET_DAYS = [3, 7, 14] as const;
type PresetDays = (typeof PRESET_DAYS)[number];
type PeriodValue = PresetDays | 'custom';

interface PeriodChip {
  label: string;
  value: PeriodValue;
}

/** FE-FIX-09：与 openapi.yaml RecallResponse.referenced_photos 一致 */
interface ReferencedPhoto {
  url: string;
  body_part?: string | null;
  uploaded_at?: string | null;
}

/** FE-FIX-09：与 openapi.yaml RecallResponse.referenced_feedbacks 一致 */
interface ReferencedFeedback {
  id: string;
  body_part?: string | null;
  snippet?: string;
  feedback_type?: string | null;
  photo_url?: string | null;
  created_at?: string | null;
  created_by?: string | null;
}

/** FE-FIX-09：与 openapi.yaml RecallResponse.context_photos 一致（V1.1.1 起改为 array） */
interface ContextPhoto {
  url: string;
  caption?: string | null;
}

/** FE-FIX-09：与 openapi.yaml RecallResponse 完整 1:1 锁值 */
interface RecallResult {
  recall_id: string;
  trigger: string;
  summary?: string | null;
  encourage?: string | null;
  safety_passed?: boolean;
  referenced_feedbacks?: ReferencedFeedback[];
  referenced_photos?: ReferencedPhoto[];
  context_photos?: ContextPhoto[];
  is_empty?: boolean | null;
  /** V1.1.1 当前实现不在响应中返回；保留 nullable 兼容 */
  soft_tip?: { message?: string; buttons?: Array<{ label?: string; action?: string; style?: string }> } | null;
  /** V1.1.1 当前实现不在响应中返回 */
  llm_cost?: number | null;
  created_at?: string | null;
  ai_session_id?: string | null;
  days_offset?: number;
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
