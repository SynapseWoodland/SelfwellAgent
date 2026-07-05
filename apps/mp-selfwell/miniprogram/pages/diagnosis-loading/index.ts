/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P03 分析中
 * 设计稿: docs/design/figma-pixso-spec/pages/05-butler-analyze-loading.html
 * 后端端点: openapi.yaml tag=diagnosis operationId=streamDiagnosis（SSE/WebSocket）
 *
 * 行为：
 *  - onLoad 解析 query.id（诊断任务 ID）
 *  - 调用 utils/sse.openSse，订阅 8 阶段进度
 *  - 收到 'done' → 跳转 report；'error' / 5 次失败 → 提示重试
 *
 * 占位：未真实联调前，所有阶段用 setInterval mock 走完一遍，便于 UI 联调。
 */
import { openSse, SseClient } from '../../utils/sse';

const STAGE_FLOW = [
  'upload_verify',
  'queued',
  'style_analyzing',
  'body_analyzing',
  'tag_aggregating',
  'suggestion',
  'rendering',
  'done',
] as const;

Page({
  data: {
    diagnosisId: '',
    currentStage: 'upload_verify',
    errorText: '',
    mockMode: true,
  },

  privateSse: null as SseClient | null,
  privateMockTimer: null as ReturnType<typeof setInterval> | null,

  onLoad(query: Record<string, string | undefined>) {
    const id = (query?.id ?? '').toString();
    this.setData({ diagnosisId: id });
    if (this.data.mockMode) {
      this.startMock();
    } else {
      this.startRealSse(id);
    }
  },

  onUnload() {
    this.privateSse?.close();
    if (this.privateMockTimer) clearInterval(this.privateMockTimer);
  },

  /** 真实 SSE 订阅 */
  startRealSse(id: string) {
    this.privateSse = openSse(
      { path: `/diagnosis/${id}/stream` },
      {
        onEvent: (e) => {
          const data = e.data as { stage?: string } | undefined;
          if (data?.stage) this.setData({ currentStage: data.stage });
        },
        onComplete: () => this.gotoReport(),
        onFailure: (reason) => this.setData({ errorText: reason }),
      },
    );
  },

  /** Mock：每 1500ms 推进一阶段，9 步走完（约 12s） */
  startMock() {
    let i = 0;
    this.privateMockTimer = setInterval(() => {
      i += 1;
      if (i >= STAGE_FLOW.length) {
        if (this.privateMockTimer) clearInterval(this.privateMockTimer);
        this.gotoReport();
        return;
      }
      this.setData({ currentStage: STAGE_FLOW[i] });
    }, 1500);
  },

  gotoReport() {
    wx.redirectTo({ url: '/miniprogram/pages/diagnosis-report/index' });
  },
});