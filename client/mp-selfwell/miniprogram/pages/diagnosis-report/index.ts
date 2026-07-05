/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.7 P03c 智能分析报告
 * 设计稿: docs/design/figma-pixso-spec/pages/06-butler-analyze-report.html
 * 后端端点: openapi.yaml tag=diagnosis operationId=getDiagnosis
 *
 * 占位：渲染改善方向 + 标签云 + "开始 21 天" CTA。
 */
interface Report {
  id: string;
  improvements: string[];
  tags: string[];
}

Page({
  data: {
    report: {
      id: 'mock_report',
      improvements: [
        '增加每日 5 分钟冥想',
        '练习肩颈拉伸，跟随推荐视频',
        '记录心情日记，关注呼吸',
      ],
      tags: ['安静', '专注', '自我观察', '温和', '可持续', '放松'],
    } as Report,
  },

  onLoad() {},

  onStartPlan() {
    wx.navigateTo({ url: '/miniprogram/pages/plan/index' });
  },

  onBackHome() {
    wx.reLaunch({ url: '/miniprogram/pages/home/index' });
  },
});