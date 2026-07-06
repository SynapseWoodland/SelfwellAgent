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
      const resp = await get<Snapshot>(`/butler/recall/${day}`);
      if (resp) this.setData({ snapshot: resp });
    } catch {
      /* 保持当前 snapshot，不打断 UI */
    } finally {
      this.setData({ loading: false });
    }
  },

  onSelectDay(e: WechatMiniprogram.CustomEvent<{ day: 7 | 14 | 21 }>) {
    const day = e.detail?.day;
    if (!day) return;
    this.loadSnapshot(day);
  },
});