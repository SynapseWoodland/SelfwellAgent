/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P03c 智能分析报告
 * 设计稿: docs/design/figma-pixso-spec/pages/06-butler-analyze-report.html
 * 后端端点：
 *   - GET  /diagnosis/{report_id}
 *   - POST /plans/generate       （用户点「开始 21 天」）
 *
 * 行为：
 *  1) onLoad 解析 ?report_id=...
 *  2) GET /diagnosis/{report_id} 渲染方向列表 + 报告摘要
 *  3) 「开始 21 天」点击 → POST /plans/generate { report_id } → 成功后 switchTab home
 */
import { get, post } from '../../utils/request';
import { SMART_ANALYZE_COPY } from '../../utils/copy';
import type { DiagnosisReport } from '../../types/api';

interface DirectionView {
  /** 序号 1..3 */
  index: number;
  title: string;
  /** 严重程度：light / mid / heavy */
  level: 'light' | 'mid' | 'heavy';
  /** 展示文案 */
  levelLabel: string;
  description: string;
  /** 推荐频率文案（如「每日 8 分钟」） */
  frequency: string;
}

interface ReportResp {
  report_id: string;
  summary?: string;
  directions?: Array<{
    title?: string;
    description?: string;
    frequency?: string;
    level?: 'light' | 'mid' | 'heavy' | string;
  }>;
}

interface PageData {
  reportId: string;
  reportTitle: string;
  start21Label: string;
  summary: string;
  directions: DirectionView[];
  loading: boolean;
}

Page<PageData>({
  data: {
    reportId: '',
    reportTitle: SMART_ANALYZE_COPY.reportTitle,
    start21Label: SMART_ANALYZE_COPY.start21,
    summary: '',
    directions: [],
    loading: true,
  },

  onLoad(query: Record<string, string | undefined>) {
    const reportId = (query?.report_id ?? '').toString();
    this.setData({ reportId });
    if (!reportId || reportId.startsWith('mock_')) {
      // mock 报告兜底
      this.setData({ loading: false, summary: '我们暂时没能完整分析你的照片，可以稍后再试一次。', directions: this.fallbackDirections() });
      return;
    }
    void this.fetchReport(reportId);
  },

  async fetchReport(reportId: string): Promise<void> {
    try {
      const resp = await get<ReportResp>(`/diagnosis/${encodeURIComponent(reportId)}`);
      this.onReportLoaded(this.normalizeReport(resp, reportId));
    } catch (err) {
      console.warn('[smart-analyze-report] fetch fail, fallback', err);
      this.setData({
        loading: false,
        summary: '我们暂时没能完整拉取报告，可以稍后再来。',
        directions: this.fallbackDirections(),
      });
    }
  },

  normalizeReport(raw: unknown, reportId: string): DiagnosisReport {
    const r = (raw ?? {}) as ReportResp;
    const directions: DirectionView[] = (r.directions ?? []).slice(0, 3).map((d, i) => {
      const lvl = d.level ?? 'light';
      const level: DirectionView['level'] =
        lvl === 'mid' || lvl === 'heavy' ? lvl : 'light';
      return {
        index: i + 1,
        title: d.title ?? '改善方向',
        level,
        levelLabel:
          level === 'light' ? '轻度' : level === 'mid' ? '中度' : '重度',
        description: d.description ?? '',
        frequency: d.frequency ?? '建议每日练习',
      };
    });
    return {
      diagnosis_id: reportId,
      user_id_pseudo: '',
      created_at: new Date().toISOString(),
      tags: [],
      tag_scores: {},
      report_text: r.summary ?? '',
      matched_video_ids: [],
      directions: directions.map((d) => ({
        title: d.title,
        description: d.description,
      })),
      summary: r.summary,
    };
  },

  onReportLoaded(report: DiagnosisReport): void {
    const directions: DirectionView[] = (report.directions ?? []).map((d, i) => ({
      index: i + 1,
      title: d.title ?? '改善方向',
      level: 'light',
      levelLabel: '轻度',
      description: d.description ?? '',
      frequency: '建议每日练习',
    }));
    const summary = report.summary ?? report.report_text ?? '';
    this.setData({ loading: false, summary, directions });
  },

  fallbackDirections(): DirectionView[] {
    return [
      { index: 1, title: '侧颈前伸', level: 'light', levelLabel: '轻度', description: '建议每 2 小时做 1 次收下巴训练', frequency: '建议每日 5 分钟' },
      { index: 2, title: '肩颈僵硬', level: 'mid', levelLabel: '中度', description: '建议每日 8 分钟肩颈放松', frequency: '建议每日 8 分钟' },
      { index: 3, title: '眼周疲劳', level: 'light', levelLabel: '轻度', description: '建议每日 5 分钟眼周穴位按压', frequency: '建议每日 5 分钟' },
    ];
  },

  /** 「开始 21 天」点击 */
  async onStartPlan(): Promise<void> {
    if (!this.data.reportId) {
      wx.showToast({ title: '请先生成报告', icon: 'none' });
      return;
    }
    try {
      await post('/plans/generate', { report_id: this.data.reportId });
      wx.showToast({ title: '已生成 21 天方案', icon: 'success' });
      // 回到首页（tabBar）
      setTimeout(() => {
        wx.switchTab({ url: '/pages/home/index' });
      }, 600);
    } catch (err) {
      console.warn('[smart-analyze-report] generate plan fail', err);
      wx.showToast({ title: '生成失败，请稍后重试', icon: 'none' });
    }
  },
});
