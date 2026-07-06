/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P08 心情日记
 * 设计稿: docs/design/figma-pixso-spec/pages/08-butler-diary.html
 * 后端端点: openapi.yaml tag=feedback operationId=createFeedback POST /feedback
 *
 * 行为（SF3 完工态）：
 *  1) 用户输入文字（≤ 200 字）
 *  2) 调 /feedback → 后端返回 ack_text（30 条池中的随机 1 条）
 *  3) ack-bubble 渲染（≤ 30 字截断 + 长按 tooltip）
 *  4) 后端失败时本地 ack-pool 兜底（保证 UX 不被网络打断）
 *  5) 文案禁用：禁止 "会变白" / "会变小" / "会提升" / "分数" / "排名" 等焦虑词
 */
import { post } from '../../utils/request';
import { pickRandomAck } from '../../data/ack-pool';

interface FeedbackResp {
  ack_text: string;
  ack_id: number;
}

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
      const resp = await post<FeedbackResp>('/feedback', { mood_text: text });
      const ackText = resp?.ack_text || pickRandomAck().text;
      this.setData({ ackText, text: '' });
    } catch {
      // 兜底：本地池随机 1 条
      const ack = pickRandomAck();
      this.setData({ ackText: ack.text, text: '' });
    } finally {
      this.setData({ submitting: false });
    }
  },
});