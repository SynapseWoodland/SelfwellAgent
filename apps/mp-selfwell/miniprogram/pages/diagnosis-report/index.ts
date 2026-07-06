/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.7 P03c 智能分析报告
 * 设计稿: docs/design/figma-pixso-spec/pages/06-butler-analyze-report.html
 * 后端端点: openapi.yaml tag=diagnosis operationId=getDiagnosis GET /diagnosis/{id}
 *
 * 行为（SF2 完工态）：
 *  - onLoad 解析 query.id，调 GET /diagnosis/{id}
 *  - 渲染改善方向 + 标签云 + "开始 21 天" CTA
 *  - 失败 → 降级到 mock 报告（UI 联调不被阻塞）
 */
import { get } from '../../utils/request';

interface Report {
  id: string;
  improvements: string[];
  tags: string[];
  summary?: string;
  createdAt?: string;
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

  onLoad(query: Record<string, string | undefined>) {
    const id = (query?.id ?? '').toString();
    if (id && !id.startsWith('mock_')) {
      get<Report>(`/diagnosis/${id}`)
        .then((resp) => {
          if (resp) this.setData({ report: resp });
        })
        .catch((e) => console.warn('[diagnosis-report] fetch fail, fallback', e));
    }
  },

  onStartPlan() {
    wx.navigateTo({ url: '/miniprogram/pages/plan/index' });
  },

  onBackHome() {
    wx.reLaunch({ url: '/miniprogram/pages/home/index' });
  },
});