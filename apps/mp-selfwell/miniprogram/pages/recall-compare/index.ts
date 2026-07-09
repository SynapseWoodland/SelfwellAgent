/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.8 P08 对比回顾
 * 后端端点:
 *   - POST /butler/recall         — 触发主动回忆生成
 *   - GET  /butler/recall/day/:day — 按天获取回忆对比
 *
 * 行为：
 *   - onLoad 默认选中 day=7（第一个可对比节点）
 *   - 用户切换 tab → GET /butler/recall/day/:day
 *   - 无数据时显示空状态文案
 *   - 若当前用户尚未到达对应天数，提示"还有 N 天再来"
 */
import { get, post, ApiException } from '../../utils/request';
import type { RecallDay } from '../../types/api';

const DAYS: RecallDay[] = [7, 14, 21];

interface RecallSnapshot {
  emotionTrend: string;     // 来自 summary_text
  habitStreak: string;     // 来自 diff_tags.join(' / ')
  highlights: string[];     // 来自 diff_tags
  baseline_report_text: string;
  current_report_text: string;
  generated_at: string;
}

interface PageData {
  days: number[];
  activeDay: RecallDay;
  snapshot: RecallSnapshot | null;
  loading: boolean;
  errMsg: string;
}

Page({
  data: {
    days: DAYS,
    activeDay: 7,
    snapshot: null,
    loading: false,
    errMsg: '',
  } as PageData,

  onLoad(options: { day?: string }) {
    const day = options?.day ? (parseInt(options.day, 10) as RecallDay) : 7;
    this.setData({ activeDay: DAYS.includes(day) ? day : 7 });
    this._loadSnapshot(this.data.activeDay);
  },

  onSelectDay(e: WechatMiniprogram.TapEvent) {
    const day = e.currentTarget.dataset.day as RecallDay;
    if (day === this.data.activeDay) return;
    this.setData({ activeDay: day, snapshot: null });
    this._loadSnapshot(day);
  },

  async _loadSnapshot(day: RecallDay) {
    this.setData({ loading: true, errMsg: '' });
    try {
      const data = await get<Record<string, unknown>>(`/butler/recall/day/${day}`);
      if (!data || Object.keys(data).length === 0) {
        // 无数据 — 用户尚未到达该节点
        this.setData({ loading: false, snapshot: null });
        return;
      }

      // API → UI snapshot 映射
      const snapshot: RecallSnapshot = {
        emotionTrend: (data['summary_text'] as string) ?? '',
        habitStreak: ((data['diff_tags'] as string[]) ?? []).join(' / '),
        highlights: ((data['diff_tags'] as string[]) ?? []).filter(Boolean),
        baseline_report_text: (data['baseline_report_text'] as string) ?? '',
        current_report_text: (data['current_report_text'] as string) ?? '',
        generated_at: (data['generated_at'] as string) ?? '',
      };
      this.setData({ snapshot, loading: false });
    } catch (e) {
      const msg = e instanceof ApiException ? e.message : '加载失败';
      this.setData({ loading: false, errMsg: msg });
    }
  },

  onShareAppMessage() {
    const day = this.data.activeDay;
    return {
      title: `第 ${day} 天的蜕变对比`,
      path: `/pages/recall-compare/index?day=${day}`,
    };
  },
});
