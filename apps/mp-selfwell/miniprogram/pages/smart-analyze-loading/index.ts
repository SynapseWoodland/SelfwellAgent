/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P03b 智能分析加载
 * 设计稿: docs/design/figma-pixso-spec/pages/05-butler-analyze-loading.html
 * 后端端点：
 *   - GET /diagnosis/jobs/{job_id}/stream  （SSE chunked，PR-A2 提供）
 *
 * 行为：
 *  1) onLoad 解析 ?job_id=...
 *  2) 启动 consumeSse（utils/sse-http.ts）
 *  3) for-await 收到 SseEvent：
 *     - stage: 更新 data.stages / data.percent
 *     - done : redirectTo /pages/smart-analyze-report/index?report_id=...
 *     - error: toast + 「点击重试」入口
 *  4) 卸载时 cancel consumer，避免泄漏
 */
import { consumeSse, type SseEvent } from '../../utils/sse-http';
import {
  isTerminalStage,
  resolveUiStage,
  type UiSseStageKey,
} from '../../utils/sse-stage';
import { SMART_ANALYZE_COPY } from '../../utils/copy';
import { API_BASE_URL, CURRENT_ENV } from '../../utils/config';
import { get } from '../../utils/request';
import type {
  DiagnosisJob,
  SseDonePayload,
  SseErrorPayload,
  SseStagePayload,
} from '../../types/api';

interface StageRow {
  key: UiSseStageKey | 'connected' | 'preprocess' | 'analyzing' | 'suggestion' | 'ready';
  text: string;
  /** done 完成 / doing 进行中 / pending 待办 / done-and-done 真正完成 */
  state: 'done' | 'doing' | 'pending' | 'finished';
}

/** 把后端 5 阶段 string 映射到 UI 4 行（设计稿 4 行进度） */
const UI_STAGE_FLOW: ReadonlyArray<{
  raw: SseStagePayload['stage'];
  row: StageRow;
}> = [
  { raw: 'connected', row: { key: 'connected', text: SMART_ANALYZE_COPY.stages[0], state: 'done' } },
  { raw: 'preprocess', row: { key: 'preprocess', text: SMART_ANALYZE_COPY.stages[1], state: 'doing' } },
  { raw: 'analyzing', row: { key: 'analyzing', text: SMART_ANALYZE_COPY.stages[2], state: 'pending' } },
  { raw: 'suggestion', row: { key: 'suggestion', text: SMART_ANALYZE_COPY.stages[3], state: 'pending' } },
];

interface PageData {
  jobId: string;
  loadingTitle: string;
  closeHint: string;
  retryLabel: string;
  /** 4 行 stage（视觉位置固定） */
  stages: StageRow[];
  /** 当前 percent 0..100 */
  percent: number;
  /** 当前激活阶段（对应 stages 数组 index） */
  activeIndex: number;
  /** 错误文案（空 = 无错误） */
  errorText: string;
  /** SSE 是否已关闭（用于停止 spinner） */
  closed: boolean;
}

Page<PageData>({
  data: {
    jobId: '',
    loadingTitle: SMART_ANALYZE_COPY.loadingTitle,
    closeHint: SMART_ANALYZE_COPY.closeHint,
    retryLabel: SMART_ANALYZE_COPY.retry,
    stages: UI_STAGE_FLOW.map((s) => ({ ...s.row })),
    percent: 0,
    activeIndex: 0,
    errorText: '',
    closed: false,
  },

  privateConsumer: null as ReturnType<typeof consumeSse> | null,
  privateCancelTimer: null as ReturnType<typeof setTimeout> | null,

  onLoad(query: Record<string, string | undefined>) {
    const jobId = (query?.job_id ?? '').toString();
    this.setData({ jobId });
    if (!jobId) {
      this.setData({ errorText: '缺少 job_id', closed: true });
      return;
    }
    this.startSse(jobId);
    // 6s 内没有任何 stage 事件 → 兜底推进（dev / 网络抖动）
    this.privateCancelTimer = setTimeout(() => {
      if (!this.data.closed && this.data.percent === 0) {
        this.advanceToFallback();
      }
    }, 6000);
  },

  onUnload() {
    this.privateConsumer?.cancel();
    this.privateConsumer = null;
    if (this.privateCancelTimer) {
      clearTimeout(this.privateCancelTimer);
      this.privateCancelTimer = null;
    }
  },

  startSse(jobId: string): void {
    const baseURL = API_BASE_URL[CURRENT_ENV];
    const url = `${baseURL}/diagnosis/jobs/${encodeURIComponent(jobId)}/stream`;
    this.privateConsumer = consumeSse(url, {
      header: { Accept: 'text/event-stream' },
      onTerminal: () => {
        this.setData({ closed: true });
      },
    });
    void this.consumeLoop();
  },

  async consumeLoop(): Promise<void> {
    const c = this.privateConsumer;
    if (!c) return;
    try {
      for await (const evt of c.events) {
        this.handleEvent(evt);
        if (evt.name === 'done' || evt.name === 'error') break;
      }
    } catch (err) {
      console.warn('[smart-analyze-loading] consume loop fail', err);
      this.setData({ errorText: '网络异常，请稍后重试', closed: true });
    }
  },

  handleEvent(evt: SseEvent): void {
    if (evt.name === 'stage') {
      const payload = evt.data as SseStagePayload;
      this.onSseStage(payload);
      return;
    }
    if (evt.name === 'done') {
      const payload = evt.data as SseDonePayload;
      this.onSseDone(payload);
      return;
    }
    if (evt.name === 'error') {
      const payload = evt.data as SseErrorPayload | { message?: string };
      const msg =
        (payload && typeof payload === 'object' && 'message_zh' in payload && typeof (payload as SseErrorPayload).message_zh === 'string'
          ? (payload as SseErrorPayload).message_zh
          : '') || '分析过程出现问题';
      this.onSseError({ code: '', message_zh: msg });
    }
  },

  /** 收到 stage 事件 — 更新进度与高亮阶段 */
  onSseStage(payload: SseStagePayload): void {
    if (!payload || typeof payload !== 'object') return;
    const uiKey = resolveUiStage(payload.stage);
    const stages = this.data.stages.slice();
    let activeIndex = this.data.activeIndex;
    // 把当前位置之前的全标 done；当前标 doing；之后的保持 pending
    if (payload.stage === 'connected' || payload.stage === 'preprocess') {
      stages[0].state = 'done';
      activeIndex = 1;
      stages[1].state = 'doing';
    } else if (payload.stage === 'analyzing') {
      stages[0].state = 'done';
      stages[1].state = 'done';
      activeIndex = 2;
      stages[2].state = 'doing';
    } else if (payload.stage === 'suggestion') {
      stages[0].state = 'done';
      stages[1].state = 'done';
      stages[2].state = 'done';
      activeIndex = 3;
      stages[3].state = 'doing';
    } else if (isTerminalStage(payload.stage)) {
      stages[0].state = 'done';
      stages[1].state = 'done';
      stages[2].state = 'done';
      stages[3].state = 'finished';
      activeIndex = 3;
    }
    const percent = Math.min(100, Math.max(this.data.percent, payload.percent ?? 0));
    this.setData({ stages, activeIndex, percent });
  },

  /** 收到 done 事件 — 跳转报告 */
  onSseDone(payload: SseDonePayload): void {
    if (this.privateCancelTimer) {
      clearTimeout(this.privateCancelTimer);
      this.privateCancelTimer = null;
    }
    const stages = this.data.stages.map((s, i) =>
      i === this.data.stages.length - 1 ? { ...s, state: 'finished' as const } : { ...s, state: 'done' as const },
    );
    this.setData({ stages, percent: 100, activeIndex: stages.length - 1, closed: true });
    const reportId = payload?.report_id || '';
    setTimeout(() => {
      if (!reportId) {
        // mock / 异常 fallback — 直接关闭
        wx.navigateBack({ delta: 1 });
        return;
      }
      wx.redirectTo({
        url: `/pages/smart-analyze-report/index?report_id=${encodeURIComponent(reportId)}`,
      });
    }, 600);
  },

  /** 收到 error 事件 — toast + 重试按钮 */
  onSseError(payload: SseErrorPayload): void {
    if (this.privateCancelTimer) {
      clearTimeout(this.privateCancelTimer);
      this.privateCancelTimer = null;
    }
    this.setData({ errorText: payload.message_zh || '分析过程出现问题', closed: true });
    wx.showToast({ title: payload.message_zh || '分析失败', icon: 'none' });
  },

  /** SSE 兜底推进（dev / chunked 模式失效时也可见进度） */
  advanceToFallback(): void {
    let i = this.data.activeIndex;
    const ticks = setInterval(() => {
      if (i >= this.data.stages.length) {
        clearInterval(ticks);
        return;
      }
      const stages = this.data.stages.slice();
      const prev = stages.slice(0, i).map((s) => ({ ...s, state: 'done' as const }));
      const next = stages.slice(i + 1).map((s) => ({ ...s, state: 'pending' as const }));
      const cur = { ...stages[i], state: 'doing' as const };
      this.setData({
        stages: [...prev, cur, ...next],
        activeIndex: i,
        percent: Math.min(100, Math.round(((i + 1) / this.data.stages.length) * 100)),
      });
      i += 1;
    }, 1500);
  },

  /** 「点击重试」按钮 */
  onTapRetry(): void {
    this.setData({ errorText: '', closed: false, percent: 0, activeIndex: 0 });
    this.data.stages.forEach((_, idx) => {
      const stages = this.data.stages.slice();
      stages[idx] = { ...stages[idx], state: idx === 0 ? 'doing' : 'pending' };
      this.setData({ stages });
    });
    this.startSse(this.data.jobId);
  },
});
