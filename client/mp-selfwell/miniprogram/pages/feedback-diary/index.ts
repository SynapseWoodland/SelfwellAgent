/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P08 心情日记
 * 设计稿: docs/design/figma-pixso-spec/pages/08-butler-diary.html
 * 后端端点: openapi.yaml tag=feedback operationId=createFeedback
 *
 * 占位：提交一段文字 → 后端返回 30 条 ACK 中的随机 1 条 → ack-bubble 渲染（≤ 30 字）。
 *
 * ACK 数据来自 docs/data/ack-pool.yaml（SF3 接入）。
 */
import { post } from '../../utils/request';

const ACK_POOL = [
  '今天辛苦你了，慢慢来。',
  '听到了你的呼吸，继续。',
  '每一刻都在被温柔记录。',
  '你已经在路上了。',
  '允许自己慢一点。',
  '小小的进步，也是进步。',
  '今晚，好好休息。',
  '你比自己想象的更稳。',
  '别急，时间站在你这边。',
  '先喝杯水，再继续。',
];

Page({
  data: {
    text: '',
    ackText: '',
    submitting: false,
  },

  onInput(e: WechatMiniprogram.InputEvent) {
    this.setData({ text: e.detail.value });
  },

  async onSubmit() {
    if (this.data.submitting) return;
    const text = (this.data.text ?? '').trim();
    if (!text) {
      wx.showToast({ title: '写点什么吧', icon: 'none' });
      return;
    }
    this.setData({ submitting: true });
    try {
      await post('/feedback', { mood_text: text }).catch(() => undefined);
      const ack = ACK_POOL[Math.floor(Math.random() * ACK_POOL.length)];
      this.setData({ ackText: ack, text: '' });
    } finally {
      this.setData({ submitting: false });
    }
  },
});