/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.4 P04 21 天方案
 * 设计稿: docs/design/figma-pixso-spec/pages/07-plan.html
 * 后端端点:
 *   - openapi.yaml tag=plans operationId=generatePlan / getActivePlan / getTodayPlan
 *   - openapi.yaml tag=videos operationId=getRecommendedVideos
 *
 * 占位：21 天日历总览 + 阶段说明。
 */
Page({
  data: {
    planDays: Array.from({ length: 21 }, (_, i) => i + 1),
    currentDay: 1,
    phases: [
      { range: '1-7', title: '起步期', desc: '建立基础习惯' },
      { range: '8-14', title: '稳定期', desc: '巩固节奏' },
      { range: '15-21', title: '深入期', desc: '形成自我对话' },
    ],
  },

  onLoad() {
    // SF1 接入 getActivePlan + getTodayPlan
  },
});