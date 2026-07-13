import { get } from '../../utils/request';

declare const wx: any;
declare function Page(config: any): void;

interface PreviewDay {
  day: number;
  title: string;
  meta: string;
  status: 'completed' | 'active' | 'pending' | 'feedback';
}

interface PlanPreviewResponse {
  days?: Array<{
    day?: number;
    day_index?: number;
    title?: string;
    task?: string;
    duration_minutes?: number;
    source?: string;
    status?: PreviewDay['status'];
  }>;
}

const TASKS = [
  '收下巴训练', '肩颈放松', '面部按摩', '久坐伸展', '收下巴 + 肩颈', '睡前舒缓', '第一周轻反馈',
  '肩背激活', '颈部拉伸', '面部循环', '坐姿重置', '肩胛稳定', '呼吸放松', '第二周轻反馈',
  '全身舒展', '颈肩组合', '面部护理', '核心唤醒', '体态复盘', '自由巩固', '21 天回望',
] as const;

function buildFallbackDays(): PreviewDay[] {
  return TASKS.map((title, index) => ({
    day: index + 1,
    title,
    meta: `${index % 3 === 0 ? 8 : index % 3 === 1 ? 12 : 10} 分钟 · 阶段 ${Math.floor(index / 7) + 1}`,
    status: index === 0 ? 'active' : index === 6 || index === 13 || index === 20 ? 'feedback' : 'pending',
  }));
}

Page({
  data: {
    planId: '',
    expanded: false,
    days: buildFallbackDays(),
    visibleDays: buildFallbackDays().slice(0, 7),
    legends: [
      { label: '已完成', key: 'completed' },
      { label: '进行中', key: 'active' },
      { label: '待办', key: 'pending' },
      { label: '反馈日', key: 'feedback' },
    ],
  },

  onLoad(query: Record<string, string | undefined>) {
    const planId = String(query.plan_id ?? wx.getStorageSync('plan.delivery.id') ?? '');
    this.setData({ planId });
    void this.loadPreview(planId);
  },

  onNavBack() {
    wx.navigateBack({ delta: 1 });
  },

  async loadPreview(planId: string) {
    if (!planId) return;
    const preview = await get<PlanPreviewResponse>(
      `/plans/${encodeURIComponent(planId)}/preview?days=21`,
    ).catch(() => null);
    if (!Array.isArray(preview?.days) || preview.days.length === 0) return;
    const fallback = buildFallbackDays();
    const days = Array.from({ length: 21 }, (_, index) => {
      const source = preview.days?.[index];
      if (!source) return fallback[index];
      const day = source.day ?? source.day_index ?? index + 1;
      const duration = source.duration_minutes ? `${source.duration_minutes} 分钟` : fallback[index].meta;
      return {
        day,
        title: source.title ?? source.task ?? fallback[index].title,
        meta: source.source ? `${duration} · ${source.source}` : duration,
        status: source.status ?? fallback[index].status,
      };
    });
    this.setData({ days, visibleDays: this.data.expanded ? days : days.slice(0, 7) });
  },

  onToggleAllDays() {
    const expanded = !this.data.expanded;
    this.setData({
      expanded,
      visibleDays: expanded ? this.data.days : this.data.days.slice(0, 7),
    });
  },

  onGoToday() {
    // FR-PLAN-01：交付页完成后跳「今天 Tab」看任务。V2 IA 中 today Tab 即 home/index
    // （app.json tabBar[1].pagePath = 'pages/home/index'）。旧 plan-tabs 已废弃。
    wx.switchTab({ url: '/pages/home/index' });
  },
});
