/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.4 P04 21 天方案
 * 设计稿: docs/design/figma-pixso-spec/pages/07-plan.html
 * 后端端点:
 *   - openapi.yaml tag=plans   operationId=getActivePlan  GET  /plans/current
 *   - openapi.yaml tag=plans   operationId=generatePlan   POST /plans/generate
 *   - openapi.yaml tag=videos  operationId=getRecommendedVideos GET /videos/match?tag=...
 *
 * 行为（SF4 完工态）：
 *  - onLoad 拉 /plans/current 拿到 dayIndex + 阶段 + 今日任务
 *  - 无方案时显示"生成方案"按钮 → POST /plans/generate
 *  - 失败 → mock 21 天骨架
 */
import { get, post } from '../../utils/request';

interface PlanPhase {
  range: string;
  title: string;
  desc: string;
}

interface PlanResp {
  id: string;
  dayIndex: number;
  totalDays: number;
  phases: PlanPhase[];
  todayTasks: Array<{ id: string; title: string; subtitle: string; done: boolean }>;
}
Page({
  data: {
    planDays: Array.from({ length: 21 }, (_, i) => i + 1),
    currentDay: 1,
    phases: [
      { range: '1-7', title: '起步期', desc: '建立基础习惯' },
      { range: '8-14', title: '稳定期', desc: '巩固节奏' },
      { range: '15-21', title: '深入期', desc: '形成自我对话' },
    ],
    todayTasks: [] as Array<{ id: string; title: string; subtitle: string; done: boolean }>,
    planId: '',
    generating: false,
  },

  onLoad() {
    this.fetchActivePlan();
  },

  async fetchActivePlan() {
    try {
      const resp = await get<PlanResp>('/plans/current');
      if (resp) {
        this.setData({
          planId: resp.id,
          currentDay: resp.dayIndex || 1,
          phases: resp.phases?.length ? resp.phases : this.data.phases,
          todayTasks: resp.todayTasks || [],
        });
      }
    } catch {
      /* mock 兜底；保持骨架 */
    }
  },

  async onGeneratePlan() {
    if (this.data.generating) return;
    this.setData({ generating: true });
    try {
      await post('/plans/generate', {});
      await this.fetchActivePlan();
      wx.showToast({ title: '方案已生成', icon: 'success' });
    } catch (e) {
      wx.showToast({ title: '生成失败，请稍后', icon: 'none' });
    } finally {
      this.setData({ generating: false });
    }
  },
});