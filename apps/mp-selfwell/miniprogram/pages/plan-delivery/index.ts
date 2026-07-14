import { get } from '../../utils/request';
import { mapPlanDays, type PreviewDay } from '../../services/plan';
import { getHomeTabUrl } from '../../utils/config';

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
  return TASKS.map((title, index) => {
    const phase = index < 7 ? 'p1' : index < 14 ? 'p2' : 'p3';
    const minutes = index % 3 === 0 ? 8 : index % 3 === 1 ? 12 : 10;
    const phaseNum = Math.floor(index / 7) + 1;
    return {
      day: index + 1,
      title,
      meta: `${minutes} 分钟 · 阶段 ${phaseNum}`,
      phase,
      status: index === 0 ? 'active' : index === 6 || index === 13 || index === 20 ? 'feedback' : 'pending',
    };
  });
}

Page({
  data: {
    planId: '',
    expanded: false,
    days: buildFallbackDays(),
    visibleDays: buildFallbackDays().slice(0, 7),
    remainingDays: 16,
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
    // FE-FIX-07：21 天预览字段映射统一走 services/plan.ts 层（mapPlanDays 纯函数）
    const fallbacks = buildFallbackDays();
    const days = mapPlanDays(preview.days, fallbacks);
    const visibleCount = this.data.expanded ? days.length : 5;
    this.setData({
      days,
      visibleDays: days.slice(0, visibleCount),
      remainingDays: Math.max(0, 21 - visibleCount),
    });
  },

  onToggleAllDays() {
    const expanded = !this.data.expanded;
    const visibleDays = expanded ? this.data.days : this.data.days.slice(0, 5);
    const remainingDays = expanded ? 0 : Math.max(0, 21 - 5);
    this.setData({ expanded, visibleDays, remainingDays });
  },

  onGoToday() {
    // FR-PLAN-01：交付页完成后跳「今天 Tab」看任务。
    wx.switchTab({ url: getHomeTabUrl() });
  },

  onGoPlanTabs() {
    // 展开全部 21 天方案（对齐 15h 原型"先看完整方案"按钮）
    this.onToggleAllDays();
  },
});
