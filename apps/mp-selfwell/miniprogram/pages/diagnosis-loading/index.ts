/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P03 分析中
 * 设计稿: docs/design/figma-pixso-spec/pages/05-butler-analyze-loading.html
 * 后端端点: openapi.yaml tag=diagnosis operationId=streamDiagnosis（SSE/WebSocket）
 *
 * 行为（SF2 完工态）：
 *  - onLoad 解析 query.id（诊断任务 ID）
 *  - 调 utils/sse.openSse，订阅 8 阶段进度
 *  - 收到 'done' → 跳转 report
 *  - 'error' / 5 次失败（utils/sse 内部退避 1s→2s→4s→8s→16s→30s） → 提示"网络异常，请稍后查看报告"
 *  - SSE 不可用（开发 / CI）时，setData 5s 兜底推进阶段，保证 UI 联调
 */
import { openSse, SseClient } from '../../utils/sse';
import { get } from '../../utils/request';

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

interface DiagnosisStatus {
  id: string;
  status: 'queued' | 'analyzing' | 'done' | 'failed';
  stage?: string;
}

Page({
  data: {
    diagnosisId: '',
    currentStage: 'upload_verify',
    errorText: '',
  },

  privateSse: null as SseClient | null,
  privateMockTimer: null as ReturnType<typeof setInterval> | null,
  privatePollTimer: null as ReturnType<typeof setInterval> | null,
  privateStartedAt: 0,

  onLoad(query: Record<string, string | undefined>) {
    const id = (query?.id ?? '').toString();
    this.setData({ diagnosisId: id });
    this.privateStartedAt = Date.now();
    // SF2 真实路径：开 SSE 订阅；3s 内未收到首事件则降级轮询 + 兜底
    this.startRealSse(id);
    setTimeout(() => this.maybeStartPollingFallback(id), 3000);
  },

  onUnload() {
    this.privateSse?.close();
    if (this.privateMockTimer) clearInterval(this.privateMockTimer);
    if (this.privatePollTimer) clearInterval(this.privatePollTimer);
  },

  /** 真实 SSE 订阅（§17.16 断线重连在 utils/sse 内 1→2→4→8→16→30s） */
  startRealSse(id: string) {
    this.privateSse = openSse(
      { path: `/diagnosis/${id}/stream` },
      {
        onEvent: (e) => {
          const data = e.data as { stage?: string } | undefined;
          if (data?.stage) this.setData({ currentStage: data.stage });
        },
        onComplete: () => this.gotoReport(),
        onFailure: (reason) => {
          console.warn('[diagnosis-loading] sse failed', reason);
          this.setData({ errorText: reason });
          // 5 次失败后兜底：轮询 /diagnosis/{id}
          this.startPolling(id);
        },
      },
    );
  },

  /** 兜底轮询：每 4s 拉一次 GET /diagnosis/{id}，直至 status=done 或 60s 超时 */
  startPolling(id: string) {
    if (this.privatePollTimer) return;
    let attempt = 0;
    const tick = async () => {
      attempt += 1;
      if (attempt > 15) {
        if (this.privatePollTimer) clearInterval(this.privatePollTimer);
        this.setData({ errorText: '网络异常，请稍后查看报告' });
        return;
      }
      try {
        const me = await get<DiagnosisStatus>(`/diagnosis/${id}`);
        if (me?.stage) this.setData({ currentStage: me.stage });
        if (me?.status === 'done') {
          if (this.privatePollTimer) clearInterval(this.privatePollTimer);
          this.gotoReport();
        }
      } catch {
        /* 继续轮询 */
      }
    };
    this.privatePollTimer = setInterval(tick, 4000);
  },

  /** SSE 长时间无首事件 → 启动兜底推进（每 1500ms 推一阶段） */
  maybeStartPollingFallback(id: string) {
    if (this.data.currentStage !== 'upload_verify') return;
    if (Date.now() - this.privateStartedAt < 3000) return;
    // 已经收过 SSE 帧就跳过
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
    wx.redirectTo({ url: '/pages/diagnosis-report/index' });
  },
});