import { buildSseStreamUrl } from '../../utils/sse-url';
import { consumeSse, type SseConsumer, type SseEvent } from '../../utils/sse-http';

interface LoadingStep {
  key: string;
  label: string;
  state: 'done' | 'active' | 'pending';
}

const STAGE_STEPS = [
  { key: 'start', label: '连接分析资料' },
  { key: 'preprocess', label: '照片安全预处理' },
  { key: 'analyzing', label: '识别状态细节' },
  { key: 'suggestion', label: '生成养护方向' },
  { key: 'plan', label: '21 天方案编排' },
  { key: 'ready', label: '诊断报告就绪' },
] as const;

const STAGE_TO_STEP: Record<string, number> = {
  start: 0,
  connected: 0,
  preprocess: 1,
  analyzing: 2,
  suggestion: 4,
  ready: 5,
};

const STEP_PROGRESS = [8, 22, 48, 68, 86, 100] as const;

function buildProgressSvg(percent: number): string {
  const radius = 27;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - percent / 100);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><circle cx="32" cy="32" r="27" fill="none" stroke="#E2E8F0" stroke-width="6"/><circle cx="32" cy="32" r="27" fill="none" stroke="#A8C5B5" stroke-width="6" stroke-linecap="round" stroke-dasharray="${circumference}" stroke-dashoffset="${offset}" transform="rotate(-90 32 32)"/></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

function buildSteps(activeIndex: number): LoadingStep[] {
  return STAGE_STEPS.map((step, index) => ({
    ...step,
    state: index < activeIndex ? 'done' : index === activeIndex ? 'active' : 'pending',
  }));
}

Page({
  data: {
    sessionId: '',
    currentStage: 'start',
    activeStepIndex: 0,
    progress: STEP_PROGRESS[0],
    progressSvg: buildProgressSvg(STEP_PROGRESS[0]),
    steps: buildSteps(0),
    errorText: '',
  },

  privateConsumer: null as SseConsumer | null,
  privateMockTimer: null as ReturnType<typeof setInterval> | null,
  privateFallbackTimer: null as ReturnType<typeof setTimeout> | null,
  privateReceivedEvent: false,
  privateRedirected: false,

  onLoad(query: Record<string, string | undefined>) {
    const sessionId = String(query.id ?? '');
    const defaultPath = `/assistant/sessions/${encodeURIComponent(sessionId)}/stream`;
    const streamPath = decodeURIComponent(String(query.stream_url ?? defaultPath));
    this.setData({ sessionId });
    this.startSse(streamPath);
    this.privateFallbackTimer = setTimeout(() => {
      if (!this.privateReceivedEvent) this.startMockProgress();
    }, 3000);
  },

  onUnload() {
    this.privateConsumer?.cancel();
    if (this.privateMockTimer) clearInterval(this.privateMockTimer);
    if (this.privateFallbackTimer) clearTimeout(this.privateFallbackTimer);
  },

  onNavBack() {
    wx.navigateBack({ delta: 1 });
  },

  startSse(streamPath: string) {
    // FE-FIX-08：stream_url 拼接走 utils/sse-url.ts 工厂，规避双前缀 / 漏前缀 / 跨环境 baseURL。
    // 真源：assistant_service.py:442 → `stream_url: f"/diagnosis/jobs/{job_id}/stream"`（无 /api/v1）
    const streamUrl = buildSseStreamUrl(streamPath);
    const consumer = consumeSse(streamUrl, {
      method: 'GET',
      header: { Authorization: `Bearer ${wx.getStorageSync('jwt') || ''}` },
    });
    this.privateConsumer = consumer;
    void this.consumeEvents(consumer);
  },

  async consumeEvents(consumer: SseConsumer) {
    try {
      for await (const event of consumer.events) {
        this.privateReceivedEvent = true;
        const normalized = event as SseEvent & { data?: { stage?: string; message_zh?: string } };
        const eventName = String(normalized.name);
        if (eventName === 'done' || eventName === 'end') {
          this.gotoReport();
          return;
        }
        if (eventName === 'error') {
          this.setData({ errorText: normalized.data?.message_zh || '网络异常，正在为你继续分析' });
          this.startMockProgress();
          return;
        }
        const stage = eventName === 'stage'
          ? normalized.data?.stage
          : normalized.data?.stage ?? eventName;
        if (stage) this.applyStage(stage);
      }
    } catch {
      this.setData({ errorText: '网络异常，正在为你继续分析' });
      this.startMockProgress();
    }
  },

  applyStage(stage: string) {
    const mappedIndex = STAGE_TO_STEP[stage];
    if (mappedIndex === undefined) return;
    this.setStep(mappedIndex, stage);
    if (stage === 'ready') setTimeout(() => this.gotoReport(), 360);
  },

  setStep(index: number, stage: string) {
    const safeIndex = Math.max(0, Math.min(STAGE_STEPS.length - 1, index));
    const progress = STEP_PROGRESS[safeIndex];
    this.setData({
      currentStage: stage,
      activeStepIndex: safeIndex,
      progress,
      progressSvg: buildProgressSvg(progress),
      steps: buildSteps(safeIndex),
    });
  },

  startMockProgress() {
    if (this.privateMockTimer || this.privateRedirected) return;
    let index = this.data.activeStepIndex;
    this.privateMockTimer = setInterval(() => {
      index += 1;
      if (index >= STAGE_STEPS.length) {
        if (this.privateMockTimer) clearInterval(this.privateMockTimer);
        this.privateMockTimer = null;
        this.gotoReport();
        return;
      }
      this.setStep(index, STAGE_STEPS[index].key);
    }, 1500);
  },

  gotoReport() {
    if (this.privateRedirected) return;
    this.privateRedirected = true;
    this.privateConsumer?.cancel();
    wx.redirectTo({
      url: `/pages/diagnosis-report-v2/index?session_id=${encodeURIComponent(this.data.sessionId)}`,
    });
  },
});
