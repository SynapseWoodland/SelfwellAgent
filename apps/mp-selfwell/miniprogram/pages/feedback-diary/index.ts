/**
 * feedback-diary · 心情日记
 * PR-V2-C · 对齐 15a-butler-home-tab1.html 心情日记入口
 * 后端端点：
 *   - POST /feedback — 创建心情记录（mood_text / mood_photo）
 *   - GET  /feedback — 用户历史心情列表
 */
import { get, post, ApiException } from '../../utils/request';

interface FeedbackEntry {
  feedback_id: string;
  feedback_type: 'mood_text' | 'mood_photo';
  text_content?: string;
  photo_url?: string;
  created_at: string;
}

interface Mood {
  id: string;
  emoji: string;
  label: string;
}

interface PageData {
  text: string;
  selectedMood: string;
  mood: string;
  photoUrl: string;
  photoId: string;
  dateLabel: string;
  moods: Mood[];
  submitting: boolean;
  ackText: string;
  canSubmit: boolean;
  history: FeedbackEntry[];
  loadingHistory: boolean;
}

const MOODS: Mood[] = [
  { id: 'great', emoji: '😊', label: '很好' },
  { id: 'okay', emoji: '🙂', label: '还行' },
  { id: 'tired', emoji: '😔', label: '有点累' },
  { id: 'sad', emoji: '😢', label: '难过' },
  { id: 'anxious', emoji: '😤', label: '焦虑' },
];

Page({
  data: {
    text: '',
    selectedMood: '',
    mood: '',
    photoUrl: '',
    photoId: '',
    dateLabel: '',
    moods: [],
    submitting: false,
    ackText: '',
    canSubmit: false,
    history: [],
    loadingHistory: false,
  } as PageData,

  onLoad() {
    this.setData({ moods: MOODS, dateLabel: this._formatDate() });
    void this._loadHistory();
  },

  _formatDate(): string {
    const now = new Date();
    return `${now.getMonth() + 1}月${now.getDate()}日`;
  },

  onSelectMood(e: WechatMiniprogram.TapEvent) {
    const id = String((e.currentTarget.dataset as { id?: string }).id ?? '');
    const mood = MOODS.find((m) => m.id === id);
    this.setData({
      selectedMood: id,
      mood: mood?.emoji + ' ' + mood?.label ?? '',
    });
  },

  onPickPhoto() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFiles[0]?.tempFilePath ?? '';
        if (tempFilePath) {
          this.setData({ photoUrl: tempFilePath });
        }
      },
      fail: () => {
        wx.showToast({ title: '选择照片失败', icon: 'none' });
      },
    });
  },

  onInput(e: WechatMiniprogram.Input) {
    const text = e.detail.value as string;
    this.setData({ text, canSubmit: text.trim().length > 0 });
  },

  _canSubmit(): boolean {
    return this.data.text.trim().length > 0;
  },

  async onSubmit() {
    if (!this._canSubmit()) {
      wx.showToast({ title: '请写点什么吧', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });
    try {
      // 心情 + 文字记录
      const body: Record<string, unknown> = {
        feedback_type: this.data.photoUrl ? 'mood_photo' : 'mood_text',
        mood: this.data.mood,
        text_content: this.data.text.trim(),
      };
      const resp = await post<{ ack?: { text?: string } } | null, Record<string, unknown>>(
        '/feedback',
        body,
      );
      this.setData({
        text: '',
        submitting: false,
        ackText: resp?.ack?.text ?? '收到你的心情了 💛',
      });
      void this._loadHistory();
    } catch (e) {
      this.setData({ submitting: false });
      wx.showToast({
        title: e instanceof ApiException ? e.message : '保存失败',
        icon: 'none',
      });
    }
  },

  onNavBack() {
    wx.navigateBack();
  },

  async _loadHistory() {
    this.setData({ loadingHistory: true });
    try {
      const resp = await get<{ items?: FeedbackEntry[] }>('/feedback');
      this.setData({ history: resp?.items ?? [], loadingHistory: false });
    } catch {
      this.setData({ loadingHistory: false });
    }
  },
});
