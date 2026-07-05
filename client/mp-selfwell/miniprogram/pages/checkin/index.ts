/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.5 P05 打卡完成
 * 设计稿: docs/design/figma-pixso-spec/pages/08-checkin.html
 * 后端端点:
 *   - openapi.yaml tag=checkins operationId=createCheckin
 *   - openapi.yaml tag=feedback operationId=createFeedback（顺手 ack）
 *
 * 占位：今日已完成的任务列表 + 反馈输入 + 提交按钮。
 */
import { post } from '../../utils/request';

Page({
  data: {
    text: '',
    todayItems: [
      { id: 't1', title: '冥想 5 分钟', done: true },
      { id: 't2', title: '肩颈拉伸', done: true },
    ],
    submitting: false,
  },

  onInput(e: WechatMiniprogram.InputEvent) {
    this.setData({ text: e.detail.value });
  },

  async onSubmit() {
    if (this.data.submitting) return;
    this.setData({ submitting: true });
    try {
      // SF1 接入：先 /checkins → /feedback
      await post('/checkins', {
        items: this.data.todayItems.map((t) => t.id),
        date: new Date().toISOString().slice(0, 10),
      }).catch(() => undefined);
      if (this.data.text.trim()) {
        await post('/feedback', {
          mood_text: this.data.text.trim(),
        }).catch(() => undefined);
      }
      wx.showToast({ title: '打卡完成', icon: 'success' });
      setTimeout(() => wx.reLaunch({ url: '/miniprogram/pages/home/index' }), 600);
    } catch (e) {
      const msg = e instanceof Error ? e.message : '提交失败';
      wx.showToast({ title: msg, icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  },
});