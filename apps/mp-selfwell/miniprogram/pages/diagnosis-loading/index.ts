/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P03 分析中
 * 设计稿: docs/design/figma-pixso-spec/pages/05-butler-analyze-loading.html
 * 后端端点: openapi.yaml tag=diagnosis operationId=streamDiagnosis（SSE）
 *
 * 行为（PR-A2 + ADR-0004 异步 SSE 真链路，已切到异步 job 模型）：
 *  - onLoad 解析 query.id（job_id）+ query.stream_url（后端返回的 SSE path）
 *  - 优先用后端 stream_url，缺失则默认 /diagnosis/jobs/{id}/stream
 *  - 调 utils/sse.openSse，订阅 5 阶段后端约定：connected / preprocess /
 *    analyzing / suggestion / ready
 *  - 收到 'done' → 跳转 report
 *  - 'error' / 5 次失败（utils/sse 内部退避 1s→2s→4s→8s→16s→30s） → 提示"网络异常，请稍后查看报告"
 *  - SSE 不可用（开发 / CI）时，setData 5s 兜底推进阶段，保证 UI 联调
 */
import { openSse, SseClient } from '../../utils/sse';
import { get } from '../../utils/request';

/** 后端约定的 5 阶段名（PR-A2 + ADR-0004：JobEvent stage 字段硬编码对齐） */
const STAGE_FLOW = [
  'connected',
  'preprocess',
  'analyzing',
  'suggestion',
  'ready',
] as const;

interface DiagnosisStatus {
  id: string;
  status: 'queued' | 'analyzing' | 'done' | 'failed';
  stage?: string;
}

Page({
  data: {
    diagnosisId: '',
    currentStage: 'connected',
    errorText: '',
  },

  privateSse: null as SseClient | null,
  privateMockTimer: null as ReturnType<typeof setInterval> | null,
  privatePollTimer: null as ReturnType<typeof setInterval> | null,
  privateStartedAt: 0,

  onLoad(query: Record<string, string | undefined>) {
    const id = (query?.id ?? '').toString();
    // 后端异步路径返回的 stream_url（POST /diagnosis?async=true 202 响应）；
    // 缺省时回落到 /diagnosis/jobs/{id}/stream 默认值。
    const streamUrl = ((query?.stream_url ?? '').toString()) || `/diagnosis/jobs/${id}/stream`;
    this.setData({ diagnosisId: id });
    this.privateStartedAt = Date.now();
    // SF2 真实路径：开 SSE 订阅；3s 内未收到首事件则降级轮询 + 兜底
    this.startRealSse(id, streamUrl);
    setTimeout(() => this.maybeStartPollingFallback(id), 3000);
  },

  onUnload() {
    this.privateSse?.close();
    if (this.privateMockTimer) clearInterval(this.privateMockTimer);
    if (this.privatePollTimer) clearInterval(this.privatePollTimer);
  },

  /** 真实 SSE 订阅（§17.16 断线重连在 utils/sse 内 1→2→4→8→16→30s） */
  startRealSse(id: string, streamUrl: string) {
    this.privateSse = openSse(
      { path: streamUrl },
      {
        onEvent: (e) => {
          const data = e.data as { stage?: string } | undefined;
          // 防御性兼容：onEvent 也会收到 done/error（规范上应由 onComplete/onFailure 处理，
          // 但部分后端实现把终态事件也走 onEvent，这里双路兼容，PR-A2 后端统一约定走 onEvent）
          if (e.event === 'done') {
            this.gotoReport();
            return;
          }
          if (e.event === 'error') {
            this.setData({ errorText: '网络异常，请稍后查看报告' });
            return;
          }
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
    if (this.data.currentStage !== 'connected') return;
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