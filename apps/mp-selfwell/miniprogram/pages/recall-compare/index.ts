/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P09 对比回顾
 * 设计稿: docs/design/figma-pixso-spec/pages/09-butler-compare.html
 * 后端端点: openapi.yaml tag=butler operationId=getRecall GET /butler/recall/{day}
 *
 * 行为（SF4 完工态）：
 *  - 顶部 3 个 day 切换 tab（7/14/21）
 *  - onLoad 拉 /butler/recall/7 默认；切换 day → 重新拉
 *  - 失败 → 降级到 mock 快照（保证骨架）
 */
import { get } from '../../utils/request';

interface Snapshot {
  day: 7 | 14 | 21;
  highlights: string[];
  emotionTrend?: string;
  habitStreak?: number;
  createdAt?: string;
}

const MOCK_BY_DAY: Record<7 | 14 | 21, Snapshot> = {
  7: {
    day: 7,
    highlights: ['冥想频率提升', '睡眠时长稳定 7.5h', '情绪波动减小'],
    emotionTrend: '温和上升',
    habitStreak: 7,
  },
  14: {
    day: 14,
    highlights: ['肩颈拉伸跟随', '专注力测试 +20%', '心情文本 4/7 天'],
    emotionTrend: '节奏稳定',
    habitStreak: 14,
  },
  21: {
    day: 21,
    highlights: ['21 天完成', '回看对比：照片 3 组', '心情曲线收敛'],
    emotionTrend: '自我对话生成',
    habitStreak: 21,
  },
};

Page({
  data: {
    days: [7, 14, 21] as Array<7 | 14 | 21>,
    activeDay: 7 as 7 | 14 | 21,
    snapshot: {
      day: 7,
      highlights: ['冥想频率提升', '睡眠时长稳定 7.5h', '情绪波动减小'],
      emotionTrend: '温和上升',
      habitStreak: 7,
    } as Snapshot,
    loading: false,
  },

  onLoad() {
    this.loadSnapshot(7);
  },

  async loadSnapshot(day: 7 | 14 | 21) {
    this.setData({ activeDay: day, loading: true });
    try {
      // 后端真源: GET /butler/recall/day/{day}（注意 /day/ 段，源自 backend/app/api/routers/business_v1.py）
      const resp = await get<Snapshot>(`/butler/recall/day/${day}`);
      if (resp && (resp.highlights?.length || resp.emotionTrend || resp.habitStreak !== undefined)) {
        this.setData({ snapshot: resp });
      } else if (!resp || (typeof resp === 'object' && Object.keys(resp).length === 0)) {
        // 后端返回 {} → 用 mock 兜底
        this.setData({ snapshot: MOCK_BY_DAY[day] });
      }
    } catch {
      /* 保持当前 snapshot，不打断 UI */
    } finally {
      this.setData({ loading: false });
    }
  },

  onSelectDay(e: WechatMiniprogram.BaseEvent) {
    const day = Number((e.currentTarget.dataset as { day: number }).day) as 7 | 14 | 21;
    if (![7, 14, 21].includes(day)) return;
    void this.loadSnapshot(day);
  },
});