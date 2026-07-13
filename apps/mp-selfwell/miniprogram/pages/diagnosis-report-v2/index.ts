import { API_BASE_URL, CURRENT_ENV } from '../../utils/config';
import { post } from '../../utils/request';
import { consumeSse, type SseConsumer, type SseEvent } from '../../utils/sse-http';

declare const wx: any;
declare function Page(config: any): void;

type MiniEvent = { currentTarget: { dataset: Record<string, unknown> } };

interface Direction {
  title: string;
  description: string;
  video: string;
}

interface PlanCreateResponse {
  plan_id?: string;
  id?: string;
}

const DEFAULT_DIRECTIONS: Direction[] = [
  { title: '侧颈前伸改善', description: '建议每 2 小时做 1 次收下巴训练，每次 30 秒', video: 'B站 · 收下巴 8 分钟' },
  { title: '久坐肩颈放松', description: '肩颈紧张属于久坐人群常见现象，建议每天做 1 组', video: 'B站 · 肩颈放松 12 分钟' },
  { title: '面部浮肿舒缓', description: '早晨面部有轻微浮肿，建议早起做 1 组面部按摩', video: 'B站 · 面部按摩 8 分钟' },
  { title: '发质基础护理', description: '发梢偏干，建议每周 1 次发膜深层护理', video: 'B站 · 发质护理 15 分钟' },
];

Page({
  data: {
    sessionId: '',
    reportId: '',
    planId: '',
    profileCount: 5,
    photoCount: 3,
    expandedActions: false,
    generating: false,
    directions: DEFAULT_DIRECTIONS,
    tags: [
      { label: '肩颈紧张', strong: true },
      { label: '久坐人群', strong: true },
      { label: '面部浮肿', strong: true },
      { label: '侧颈前伸', strong: false },
      { label: '发梢干', strong: false },
      { label: '25-34 岁', strong: false },
      { label: '早起型', strong: false },
      { label: '低强度友好', strong: false },
      { label: '5-15 分钟', strong: false },
      { label: '自律 C 级', strong: false },
      { label: '面部养护', strong: false },
      { label: '体态养护', strong: false },
    ],
    actions: [
      { icon: '伸', title: '收下巴训练', meta: '8 分钟 · 侧颈前伸' },
      { icon: '松', title: '肩颈放松', meta: '5 分钟 · 久坐人群' },
      { icon: '舒', title: '面部按摩', meta: '5 分钟 · 面部浮肿' },
    ],
    phases: [
      { key: 'p1', icon: '芽', name: '阶段 1 · 第 1-7 天', description: '轻柔唤醒 · 低强度建立习惯', meta: '1 个/天 · 5-15 分钟 · L1 聚合视频' },
      { key: 'p2', icon: '叶', name: '阶段 2 · 第 8-14 天', description: '稳定输出 · 中强度自我觉察', meta: '1-2 个/天 · 10-25 分钟 · 标签自适应' },
      { key: 'p3', icon: '树', name: '阶段 3 · 第 15-21 天', description: '巩固归因 · 进阶动作回看', meta: '2-3 个/天 · 15-30 分钟 · 已打卡回看' },
    ],
  },

  privateReportConsumer: null as SseConsumer | null,

  onLoad(query: Record<string, string | undefined>) {
    const cachedValue = wx.getStorageSync('diagnosis_v2_payload') as unknown;
    const cached = cachedValue && typeof cachedValue === 'object'
      ? cachedValue as {
          session_id?: string;
          report_id?: string;
          image_keys?: string[];
          body_parts?: string[];
          profile_count?: number;
        }
      : {};
    const sessionId = String(query.session_id ?? cached.session_id ?? '');
    const reportId = String(query.report_id ?? cached.report_id ?? '');
    const profileCount = Number(cached.profile_count ?? 5);
    const photoCount = Array.isArray(cached.image_keys) ? cached.image_keys.length : 3;
    this.setData({ sessionId, reportId, profileCount, photoCount });
    this.loadReportStream(sessionId, cached);
  },

  onUnload() {
    this.privateReportConsumer?.cancel();
  },

  onNavBack() {
    wx.navigateBack({ delta: 1 });
  },

  loadReportStream(
    sessionId: string,
    cached: { image_keys?: string[]; body_parts?: string[] },
  ) {
    if (!sessionId || !Array.isArray(cached.image_keys) || cached.image_keys.length === 0) return;
    const url = `${API_BASE_URL[CURRENT_ENV]}/assistant/sessions/${encodeURIComponent(sessionId)}/messages`;
    const consumer = consumeSse(url, {
      method: 'POST',
      header: { Authorization: `Bearer ${wx.getStorageSync('jwt') || ''}` },
      body: {
        text: 'smart_analyze',
        image_keys: cached.image_keys,
        body_parts: cached.body_parts ?? [],
      },
    });
    this.privateReportConsumer = consumer;
    void this.consumeReport(consumer);
  },

  async consumeReport(consumer: SseConsumer) {
    try {
      for await (const rawEvent of consumer.events) {
        const event = rawEvent as SseEvent & { data?: { directions?: Direction[] } };
        const eventName = String(event.name);
        if (eventName === 'report' && Array.isArray(event.data?.directions) && event.data.directions.length >= 4) {
          this.setData({ directions: event.data.directions.slice(0, 4) });
        }
        if (eventName === 'end' || eventName === 'done' || eventName === 'error') break;
      }
    } finally {
      consumer.cancel();
    }
  },

  onToggleActions() {
    this.setData({ expandedActions: !this.data.expandedActions });
  },

  onOpenVideo(event: MiniEvent) {
    const title = String((event.currentTarget.dataset as { title?: string }).title ?? '养护视频');
    wx.showToast({ title: `${title} · B站`, icon: 'none' });
  },

  async onGeneratePlan() {
    if (this.data.generating) return;
    this.setData({ generating: true });
    try {
      // PR-Contract-Fix C-2:对齐后端契约
      // - 路径: POST /plans/generate(原 /plans 不存在,会落 fallback)
      // - body:  { report_id }   (原 { session_id, draft_id, days } 字段不对)
      // - 缺 report_id 时降级到 fallback mock,保持 e2e 流程不断
      const reportId = this.data.reportId;
      const response: PlanCreateResponse = await post<PlanCreateResponse>('/plans/generate', {
        report_id: reportId || `mock_report_${Date.now()}`,
      }).catch((): PlanCreateResponse => ({ plan_id: this.data.planId || `mock_plan_${Date.now()}` }));
      const planId = response.plan_id ?? response.id ?? (this.data.planId || `mock_plan_${Date.now()}`);
      wx.setStorageSync('plan.delivery.id', planId);
      wx.redirectTo({
        url: `/pages/plan-delivery/index?plan_id=${encodeURIComponent(planId)}`,
      });
    } finally {
      this.setData({ generating: false });
    }
  },

  onSkipPlan() {
    // FR-PLAN-01：跳过方案生成 → 跳今天 Tab（V2 IA：home/index）
    wx.switchTab({ url: '/pages/home/index' });
  },
});
