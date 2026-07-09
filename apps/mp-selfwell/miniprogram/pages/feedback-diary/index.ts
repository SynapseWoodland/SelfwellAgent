/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.7 P07 心情日记
 * 后端端点:
 *   - POST /feedback           — 创建心情记录（mood_text / mood_photo / skin_photo）
 *   - GET  /feedback          — 用户历史心情列表
 */
import { get, post, ApiException } from '../../utils/request';
import type { CreateMoodReq, CreateMoodResp } from '../../types/api';

interface FeedbackEntry {
  feedback_id: string;
  feedback_type: 'mood_text' | 'mood_photo' | 'skin_photo';
  text_content?: string;
  photo_url?: string;
  created_at: string;
}

interface PageData {
  text: string;
  submitting: boolean;
  ackText: string;
  /** 历史记录 */
  history: FeedbackEntry[];
  loadingHistory: boolean;
}

Page({
  data: {
    text: '',
    submitting: false,
    ackText: '',
    history: [],
    loadingHistory: false,
  } as PageData,

  onLoad() {
    this._loadHistory();
  },

  onInput(e: WechatMiniprogram.Input) {
    this.setData({ text: e.detail.value as string });
  },

  async onSubmit() {
    const { text } = this.data;
    if (!text.trim()) {
      wx.showToast({ title: '写点什么吧', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });
    try {
      const payload: CreateMoodReq = {
        feedback_type: 'mood_text',
        text_content: text.trim(),
      };
      const resp = await post<CreateMoodResp, CreateMoodReq>('/feedback', payload);
      this.setData({
        text: '',
        submitting: false,
        ackText: resp?.ack?.text ?? '收到你的心情了 💛',
      });
    } catch (e) {
      this.setData({ submitting: false });
      wx.showToast({
        title: e instanceof ApiException ? e.message : '提交失败',
        icon: 'none',
      });
    }
  },

  async _loadHistory() {
    this.setData({ loadingHistory: true });
    try {
      const resp = await get<{ items: FeedbackEntry[] }>('/feedback');
      this.setData({ history: resp?.items ?? [], loadingHistory: false });
    } catch {
      this.setData({ loadingHistory: false });
    }
  },
});
