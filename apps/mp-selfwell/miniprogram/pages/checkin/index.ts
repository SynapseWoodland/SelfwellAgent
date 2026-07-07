/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.5 P05 打卡完成
 * FIGMA  : docs/design/figma-pixso-spec/pages/08-checkin.html
 * API    :
 *   - openapi.yaml tag=checkins operationId=createCheckin POST /checkins
 *   - openapi.yaml tag=feedback operationId=createMood POST /feedback
 *   - openapi.yaml tag=plans    operationId=getTodayPlan GET /plans/today
 *   - openapi.yaml tag=checkins operationId=getCheckinCalendar GET /checkins/today
 *
 * 真实接入：
 *  - 勾选任务列表 → POST /checkins（每日去重）
 *  - 可选反馈 → POST /feedback（mood_text）
 *  - 后端返回 ack_text，前端用 ack-bubble 组件展示
 *
 * SF1 强化（§17.15）：
 *  - ack_text 在页面级按 ACK_MAX_CHARS 预截断（ack-bubble 内部 observers 二次兜底）
 *  - isAckTruncated 暴露给 wxml 用于"长按显示完整"tooltip 开关
 *  - 提交后 ack 区段延时 1200ms 切回 home，让用户有"看 ACK → 鼓励 → 离场"的过渡
 */
import { post, get, ApiException } from '../../utils/request';
import { ACK_MAX_CHARS } from '../../utils/config';
import type {
  TodayPlan,
  CheckinToday,
  CreateCheckinReq,
  CreateCheckinResp,
  CreateMoodReq,
  CreateMoodResp,
} from '../../types/api';

interface AckView {
  text: string;
  truncated: string;
  isTruncated: boolean;
}

Page({
  data: {
    text: '',
    todayItems: [] as Array<{ id: string; title: string; done: boolean }>,
    submitting: false,
    ack: '' as AckView | string,
    newStreak: 0,
  },

  onLoad() {
    this.loadToday();
  },

  async loadToday() {
    try {
      const [plan, today] = await Promise.all([
        get<TodayPlan>('/plans/today'),
        get<CheckinToday>('/checkins/today'),
      ]);
      const doneIds = new Set(today.done_task_ids || []);
      const items = (plan.tasks || []).map((t) => ({
        id: t.task_id,
        title: t.title,
        done: doneIds.has(t.task_id),
      }));
      this.setData({ todayItems: items });
    } catch (e) {
      console.warn('[checkin] load today fail', e);
    }
  },

  onToggleItem(e: WechatMiniprogram.BaseEvent) {
    const { id, done } = e.currentTarget.dataset as { id: string; done: string };
    const isDone = done === 'true' || done === true;
    const items = this.data.todayItems.map((t) => (t.id === id ? { ...t, done: isDone } : t));
    this.setData({ todayItems: items });
  },

  onInput(e: WechatMiniprogram.InputEvent) {
    this.setData({ text: e.detail.value });
  },

  /** §17.15: ack 截断后长按显示完整原文 tooltip */
  onAckLongPress() {
    const ack = this.data.ack;
    if (!ack || typeof ack === 'string') return;
    if (!ack.isTruncated) return;
    wx.showToast({
      title: ack.text,
      icon: 'none',
      duration: 4000,
    });
  },

  /** 把后端 ack_text 包成 AckView，附带 §17.15 截断信息 */
  packAck(raw: string): AckView {
    const text = (raw ?? '').toString();
    const isTruncated = text.length > ACK_MAX_CHARS;
    return {
      text,
      truncated: isTruncated ? text.slice(0, ACK_MAX_CHARS) + '…' : text,
      isTruncated,
    };
  },

  async onSubmit() {
    if (this.data.submitting) return;
    const checked = this.data.todayItems.filter((t) => t.done);
    if (!checked.length && !this.data.text.trim()) {
      wx.showToast({ title: '至少完成一项或写下心情', icon: 'none' });
      return;
    }
    this.setData({ submitting: true });

    try {
      // 1) 打卡
      let lastAckText = '';
      let lastStreak = 0;
      if (checked.length) {
        const req: CreateCheckinReq = {
          date: new Date().toISOString().slice(0, 10),
          task_ids: checked.map((t) => t.id),
          mood_text: this.data.text.trim() || undefined,
        };
        const resp = await post<CreateCheckinResp>('/checkins', req);
        lastAckText = resp.ack_text;
        lastStreak = resp.new_streak;
      }

      // 2) 心情反馈（与 checkin 并存时，mood_text 已上送；这里再发一次以兼容反馈独立通道）
      //    后端 FeedbackCreate schema 要求：feedback_type(必填) + text_content
      //    后端 ack 实际返回 string（feedback_service.create_feedback:225），不是对象
      //    见 backend/app/api/routers/business_v1.py: FeedbackCreate
      const text = this.data.text.trim();
      if (text && !checked.length) {
        const moodReq: CreateMoodReq = {
          feedback_type: 'mood_text',
          text_content: text,
        };
        const moodResp = await post<CreateMoodResp>('/feedback', moodReq);
        lastAckText = typeof moodResp?.ack === 'string'
          ? moodResp.ack
          : (moodResp?.ack as { text?: string })?.text || '';
      }

      if (lastAckText) {
        this.setData({ ack: this.packAck(lastAckText), newStreak: lastStreak });
      }

      wx.showToast({ title: '打卡完成', icon: 'success' });
      setTimeout(() => wx.reLaunch({ url: '/pages/home/index' }), 1200);
    } catch (e) {
      let msg = '提交失败，请稍后再试';
      if (e instanceof ApiException) {
        msg = e.message || msg;
      } else if (e instanceof Error) {
        msg = e.message || msg;
      }
      wx.showToast({ title: msg.slice(0, 24), icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
