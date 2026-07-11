/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P03a 智能管家对话主页
 * 设计稿: docs/design/figma-pixso-spec/pages/04a-smart-analyze-dialog.html
 * 后端端点:
 *   - openapi.yaml tag=assistant operationId=createSession    POST /assistant/sessions
 *   - openapi.yaml tag=assistant operationId=sendMessage      POST /assistant/sessions/{id}/messages
 *   - openapi.yaml tag=butler   operationId=triggerRecall     GET  /butler/recall/{day}
 *
 * 行为（PR-A4 Option A：智能分析 = 对话气泡内嵌卡片）：
 *  1) 进入页面 → POST /assistant/sessions 建会话（6 态 FSM：greeting → listening → thinking
 *     → answer / medical_guarded / upload → analyzing → report）
 *  2) 顶部 entry cards 持久化（PRD §3.5.2：3 入口卡持续可见）
 *  3) 点「智能分析」入口卡或 🔍 智能分析 chip → entry cards 隐藏，对话区追加 upload 气泡
 *  4) 上传至少 1 张照片 → 走 ``presignAndUploadOneForAssistant`` 上传到 MinIO；
 *     收集 ``image_keys[]`` + ``body_parts[]`` 后 POST /assistant/sessions/{id}/messages
 *     触发 SSE 流（start → progress → report → end）；100% → 渲染 report 气泡
 *     （无 directions 时回退到 SMART_ANALYZE_FALLBACK_DIRECTIONS，UI 联调兜底用）
 *  5) report 气泡的「开始 21 天」按钮 → wx.navigateTo /pages/plan-tabs/index
 *  6) 用户输入 → listening → medical_guard / A 类路由 / B 类快问 / sendMessage 默认走 answer
 */
// PR-A4 worker Y：用 AbortController 做 SSE 取消；微信基础库 2.32.3 尚未原生支持，
// 必须先 import 本 polyfill 注入 globalThis.AbortController，否则
// `new AbortController()` 抛 ReferenceError。
// 仅 import 即生效，installAbortControllerPolyfill() 会在模块加载时自动执行。
import '../../utils/abort-controller-polyfill';
import { dlog } from '../../utils/dlog';
import { post, ApiException } from '../../utils/request';
import { consumeSse, type SseConsumer, type SseEvent } from '../../utils/sse-http';
import { API_BASE_URL, CURRENT_ENV } from '../../utils/config';
import {
  presignAndUploadOneForAssistant,
  type BodyPart,
  type UploadedPhoto,
} from '../../utils/upload-helper';
import { pickRandomAck } from '../../data/ack-pool';
import {
  readUserProfile,
  countFilledFields,
  type UserProfile6Fields,
} from '../../utils/profile-storage';
import {
  checkSmartAnalyzePrerequisites,
  buildSmartAnalyzeBody,
} from './index.smart-body';

type PersonaState =
  | 'greeting'
  | 'listening'
  | 'thinking'
  | 'answer'
  | 'medical_guarded'
  | 'upload'
  | 'analyzing'
  | 'report';

interface ChatTurn {
  id: string;
  state: PersonaState;
  text: string;
  title?: string;
  /** 内嵌卡片（upload/analyzing/report 用） */
  attachment?: UploadAttachment | ProgressAttachment | ReportAttachment;
}

interface UploadAttachment {
  kind: 'upload_card';
  slots: Array<{ label: string; filled: boolean; filledUrl?: string }>;
  ageRanges: Array<{ value: string; label: string; selected: boolean }>;
}

interface ProgressAttachment {
  kind: 'progress_card';
  percent: number;
  title: string;
  steps: Array<{ label: string; done: boolean; current: boolean }>;
}

interface ReportAttachment {
  kind: 'report_card';
  avatarText: string;
  name: string;
  directions: Array<{
    num: number;
    title: string;
    level: string;
    description: string;
  }>;
}

interface AssistantSessionResp {
  session_id: string;
}

/** SPEC-A2 §2.1 / §6.1：入口卡折叠 FSM 三态 */
type ButlerCardsMode = 'expanded' | 'collapsed' | 'focused';

/** A 类意图关键词（≥ 20 条；与 §6.3 实施规范对齐） */
const ROUTE_KEYWORDS: Array<{ kw: RegExp; module: string; page: string }> = [
  { kw: /诊断|分析|照片|皮肤|状态/, module: 'diagnosis', page: 'pages/diagnosis-upload/index' },
  { kw: /方案|计划|21天|21 天/, module: 'plan', page: 'pages/plan/index' },
  { kw: /打卡|今日|完成/, module: 'checkin', page: 'pages/checkin/index' },
  { kw: /日记|心情|记录|感受/, module: 'diary', page: 'pages/feedback-diary/index' },
  { kw: /回忆|过去|那天/, module: 'recall', page: 'pages/recall-compare/index' },
  { kw: /广场|社区|看看别人/, module: 'plaza', page: 'pages/community/index' },
  { kw: /抱抱|海报|分享/, module: 'hug', page: 'pages/share-hug-card/index' },
];

/** B 类快问正则（≥ 10 条） */
const QUICK_REPLY: RegExp[] = [
  /早安|你好|hi|hello|嗨/,
  /谢谢|感谢|辛苦了/,
  /累了|难过|不开心|沮丧/,
  /推荐.*视频|有.*建议/,
  /今天.*进度|打卡.*了/,
  /陪我|聊聊/,
  /吃了吗|睡得|心情如何/,
  /出去|散步|运动/,
  /冥想|呼吸|放松/,
  /周末|假期|休息/,
];

/** 医疗关键词（命中即 medical_guarded） */
const MEDICAL_KEYWORDS: RegExp[] = [
  /吃药|药物|处方|药/,
  /抑郁|焦虑症|失眠症/,
  /诊断|确诊|症状/,
  /医院|医生|治疗/,
];

const MEDICAL_GUARD_REPLY = '我听到了，但涉及医疗的事，建议找专业医生聊聊比较稳妥。我可以陪你记录心情。';

/** PR-A4 Option A：智能分析 3 槽位默认文案（与 copy.ts SMART_ANALYZE_COPY 对齐） */
const SMART_ANALYZE_SLOTS = [
  { label: '正面脸部', filled: false },
  { label: '侧面体态', filled: false },
  { label: '发质特写', filled: false },
] as const;

const SMART_ANALYZE_AGE_RANGES = [
  { value: '18-22', label: '18-22', selected: false },
  { value: '23-28', label: '23-28', selected: true },
  { value: '29-35', label: '29-35', selected: false },
  { value: '36-45', label: '36-45', selected: false },
] as const;

/** PR-A4 Option A：兜底 directions（后端 smart_analyze 在 sample_rate=0 / LLM 降级时
 *  返回的静态清单；UI 真实分析无方向时也用它兜住"报告卡不空白"的视觉契约） */
const SMART_ANALYZE_FALLBACK_DIRECTIONS = [
  { num: 1, title: '侧颈前伸', level: '轻度', description: '建议每 2 小时做 1 次收下巴训练' },
  { num: 2, title: '肩颈僵硬', level: '中度', description: '建议每日 8 分钟肩颈放松' },
  { num: 3, title: '眼周疲劳', level: '轻度', description: '建议每日 5 分钟眼周穴位按压' },
] as const;

Page({
  data: {
    personaState: 'greeting' as PersonaState,
    sessionId: '',
    turns: [
      {
        id: 't0',
        state: 'greeting',
        title: '早上好，我是 Selfwell',
        text: '今天想做什么？可以从「智能分析」开始，也可以直接跟我说。',
      },
    ] as ChatTurn[],
    inputText: '',
    /** 入口卡是否隐藏（点智能分析 / chip 后消失） */
    entryHidden: false,
    /** SPEC-A2 §2.1 FSM 三态：expanded / collapsed / focused */
    butlerCardsMode: 'expanded' as ButlerCardsMode,
    /** SPEC-A2 §2.3：本会话内是否已首次发送（决定 FSM 起点） */
    hasFirstSent: false,
    /** SPEC-A2 §2.3：popover 是否可见（collapsed/focused → tap → 6s 自动收起） */
    popoverOpen: false,
    /** SPEC-A2 §3.1：popover 自动收起 timer 句柄 */
    _popoverTimer: null as ReturnType<typeof setTimeout> | null,
    /** 4 张入口卡（PRD §3.5.2 持久显示：智能分析 / 心情日记 / 主动回忆 / 直接聊聊） */
    entryCards: [
      {
        id: 'smart_analyze',
        title: '智能分析',
        subtitle: '上传 3 张照片，生成你的养护参考',
        iconBg: '#F5E6D3',
        iconText: '◎',
        action: 'start',
      },
      {
        id: 'mood_diary',
        title: '心情日记',
        subtitle: '想留下点什么吗？没有格式',
        iconBg: '#F0D9C4',
        iconText: '✎',
        action: 'chevron',
      },
      {
        id: 'recall_self',
        title: '问问过去的自己',
        subtitle: '好奇几个月前的你吗？',
        iconBg: '#D4C5E2',
        iconText: '◷',
        action: 'chevron',
      },
    ],
    /** chips 4 项（PRD §3.5.1） */
    chips: [
      { id: 'smart_analyze', text: '🔍 智能分析', active: false },
      { id: 'today', text: '📅 今日 · 第 1 天', active: false },
      { id: 'chat', text: '💬 聊聊今天', active: false },
      { id: 'compare', text: '📊 查看对比', active: false },
    ],
    /** 当前智能分析是否在 analyzing 状态（控制按钮可点击性） */
    smartAnalyzeRunning: false,
    /** progress 定时器 */
    _progressTimer: null as ReturnType<typeof setInterval> | null,
    lastTurnId: 't0',
  },

  onLoad() {
    this.ensureSession();
  },

  onUnload() {
    if (this.data._progressTimer) {
      clearInterval(this.data._progressTimer);
      (this.data as { _progressTimer: null })._progressTimer = null;
    }
    // SPEC-A2 §6.3：清理 popover timer
    if (this.data._popoverTimer) {
      clearTimeout(this.data._popoverTimer);
      (this.data as { _popoverTimer: null })._popoverTimer = null;
    }
    // PR-A2 worker C：清理 SSE consumer
    const c = (this.data as { _sseConsumer?: SseConsumer | null })._sseConsumer;
    if (c) {
      try { c.cancel(); } catch { /* ignore */ }
      (this.data as { _sseConsumer: SseConsumer | null })._sseConsumer = null;
    }
    // Stream Y (worker Y)：清理 AbortController
    const ac = (this.data as { _sseAbortController?: AbortController | null })._sseAbortController;
    if (ac) {
      try { ac.abort(); } catch { /* ignore */ }
      (this.data as { _sseAbortController: AbortController | null })._sseAbortController = null;
    }
  },

  // ────────────────────────────────────────────────────────────
  // SPEC-A2 §6.3 / §6.4：入口卡折叠 FSM 相关方法
  // ────────────────────────────────────────────────────────────

  /**
   * 输入框聚焦：未首次发送前不动 FSM（保留 expanded 入口卡可见）；
   * 已首次发送后切到 focused（floating icon 下沉避让键盘）。
   */
  onInputFocus() {
    if (this.data.hasFirstSent) {
      this.setData({ butlerCardsMode: 'focused' });
    }
  },

  /** 输入框失焦：focused → collapsed */
  onInputBlur() {
    if (this.data.butlerCardsMode === 'focused') {
      this.setData({ butlerCardsMode: 'collapsed' });
    }
  },

  /**
   * 首次发送后折叠（被 onSend / startSmartAnalyze 复用）
   * 安全重复调用：hasFirstSent 已为 true 时直接 return。
   */
  collapseCardsOnFirstSend() {
    if (this.data.hasFirstSent) return;
    if (this.data._popoverTimer) {
      clearTimeout(this.data._popoverTimer);
      (this.data as { _popoverTimer: null })._popoverTimer = null;
    }
    this.setData({
      hasFirstSent: true,
      butlerCardsMode: 'collapsed',
      popoverOpen: false,
      entryHidden: true,
    });
  },

  /**
   * 点 floating icon → 打开 popover（collapsed/focused → expanded 临时态），6s 自动收起。
   * FSM 视觉切到 expanded，popoverOpen 同时为 true，让组件渲染 popover 而非底部卡条。
   */
  onTapFloatingIcon() {
    if (this.data.butlerCardsMode === 'expanded' && this.data.popoverOpen) return;
    if (this.data._popoverTimer) {
      clearTimeout(this.data._popoverTimer);
      (this.data as { _popoverTimer: null })._popoverTimer = null;
    }
    this.setData({
      popoverOpen: true,
      butlerCardsMode: 'expanded',
    });
    const t = setTimeout(() => {
      if (!this.data.popoverOpen) return;
      this.setData({
        popoverOpen: false,
        butlerCardsMode: this.data.butlerCardsMode === 'focused' ? 'focused' : 'collapsed',
      });
      (this.data as { _popoverTimer: null })._popoverTimer = null;
    }, 6000);
    (this.data as { _popoverTimer: ReturnType<typeof setTimeout> })._popoverTimer = t;
  },

  /**
   * popover 关闭按钮 / popover 外部点击 → 立刻收起 timer，回到 collapsed（或 focused 若 input 仍聚焦）
   */
  onPopoverClose() {
    if (this.data._popoverTimer) {
      clearTimeout(this.data._popoverTimer);
      (this.data as { _popoverTimer: null })._popoverTimer = null;
    }
    // 若 input 当前仍聚焦，回到 focused；否则回 collapsed
    const nextMode = this.data.butlerCardsMode === 'focused' ? 'focused' : 'collapsed';
    this.setData({
      popoverOpen: false,
      butlerCardsMode: nextMode,
    });
  },

  async ensureSession() {
    try {
      const s = await post<AssistantSessionResp>('/assistant/sessions', {});
      // 后端契约：AssistantSession.session_id（非旧字段 id），PR-A4 已修复
      const id = (s as unknown as { session_id?: string })?.session_id
        ?? (s as unknown as { id?: string })?.id
        ?? '';
      if (id) this.setData({ sessionId: id });
    } catch {
      // 后端不可达：用占位 session_id 让 UI 仍可渲染；后续 runSmartAnalyze
      // 会先尝试 ensureSession 再发起 SSE，避免拿假 id 调后端触发 404。
      this.setData({ sessionId: 'dev_session_' + Date.now() });
    }
  },

  onInput(e: WechatMiniprogram.InputEvent) {
    this.setData({ inputText: e.detail.value });
  },

  async onSend() {
    const text = (this.data.inputText ?? '').trim();
    if (!text) return;
    // PR-A2 worker C：发新消息前先 abort 现有 SSE consumer，避免 analyzing 流被中途打断
    const c = (this.data as { _sseConsumer?: SseConsumer | null })._sseConsumer;
    if (c) {
      try { c.cancel(); } catch { /* ignore */ }
      (this.data as { _sseConsumer: SseConsumer | null })._sseConsumer = null;
      this.setData({ smartAnalyzeRunning: false });
    }
    const listenTurn: ChatTurn = {
      id: 'u_' + Date.now(),
      state: 'listening',
      text,
    };
    this.setData({
      turns: [...this.data.turns, listenTurn],
      inputText: '',
      personaState: 'thinking',
      lastTurnId: listenTurn.id,
    });

    // SPEC-A2 §3.1 / §6.4：首次发送后折叠入口卡
    if (!this.data.hasFirstSent) {
      this.collapseCardsOnFirstSend();
    }

    // 0) medical_guard 优先（最高优先级）
    if (MEDICAL_KEYWORDS.some((r) => r.test(text))) {
      const guardTurn: ChatTurn = {
        id: 'g_' + Date.now(),
        state: 'medical_guarded',
        text: MEDICAL_GUARD_REPLY,
      };
      this.setData({
        turns: [...this.data.turns, guardTurn],
        personaState: 'medical_guarded',
        lastTurnId: guardTurn.id,
      });
      return;
    }

    // 1) A 类路由（命中即跳）
    for (const r of ROUTE_KEYWORDS) {
      if (r.kw.test(text)) {
        const routeTurn: ChatTurn = {
          id: 'r_' + Date.now(),
          state: 'answer',
          text: `好呀，带你去${r.module}～`,
        };
        this.setData({
          turns: [...this.data.turns, routeTurn],
          personaState: 'greeting',
          lastTurnId: routeTurn.id,
        });
        setTimeout(() => wx.navigateTo({ url: r.page }), 400);
        return;
      }
    }

    // 2) B 类快问 / 默认走 sendMessage
    const isQuick = QUICK_REPLY.some((r) => r.test(text));
    try {
      const resp = await post<{
        reply: string;
        route?: { module: string; params?: Record<string, string> };
        medicalGuarded?: boolean;
      }>(`/assistant/sessions/${this.data.sessionId}/messages`, {
        text,
        is_quick: isQuick,
      });
      const answer: ChatTurn = {
        id: 'a_' + Date.now(),
        state: 'answer',
        text: resp?.reply || pickRandomAck().text,
      };
      this.setData({
        turns: [...this.data.turns, answer],
        personaState: 'greeting',
        lastTurnId: answer.id,
      });
    } catch (err) {
      // 限流错误（429）：toast + 不追加 ack
      if (err instanceof ApiException && err.httpStatus === 429) {
        wx.showToast({ title: err.message || '请求过于频繁，请稍后再试', icon: 'none' });
        return;
      }
      // 其它错误：兜底 ack-pool
      const fallback = pickRandomAck();
      const answer: ChatTurn = {
        id: 'a_' + Date.now(),
        state: 'answer',
        text: fallback.text,
      };
      this.setData({
        turns: [...this.data.turns, answer],
        personaState: 'greeting',
        lastTurnId: answer.id,
      });
    }
  },

  /**
   * 点击入口卡（4 张：smart_analyze / mood_diary / recall_self / direct_input）
   *  - smart_analyze  → 隐藏入口卡 + 追加 upload 气泡（PR-A4 Option A 内嵌卡片）
   *  - mood_diary     → 跳转 feedback-diary（保留旧行为）
   *  - recall_self    → 跳转 recall-compare（保留旧行为）
   */
  onTapEntry(e: WechatMiniprogram.BaseEvent) {
    // 事件源是 <butler-cards-block bind:cards-tap="onTapEntry">，e.currentTarget 是
    // 整个 butler-cards-block 容器，没有 dataset.id；子组件 triggerEvent 把 id 放在 e.detail 里
    // 旧版读 e.currentTarget.dataset.id 永远 undefined → 三个分支全部不命中 → 静默无反应
    const id = ((e.detail as { id?: string })?.id
      ?? (e.currentTarget?.dataset as { id?: string } | undefined)?.id
      ?? '') as 'smart_analyze' | 'mood_diary' | 'recall_self' | 'direct_input' | '';
    if (id === 'smart_analyze') {
      this.startSmartAnalyze();
      return;
    }
    if (id === 'mood_diary') {
      wx.navigateTo({ url: '/pages/feedback-diary/index' });
      return;
    }
    if (id === 'recall_self') {
      wx.navigateTo({ url: '/pages/recall-compare/index' });
      return;
    }
    if (id === 'direct_input') {
      // toast 兜底，实际由用户主动聚焦输入框
      wx.showToast({ title: '直接告诉我吧', icon: 'none' });
    }
  },

  /** 点击 chips（4 项：智能分析 / 今日 / 聊聊今天 / 查看对比） */
  onTapChip(e: WechatMiniprogram.BaseEvent) {
    const id = (e.currentTarget.dataset as { id: string }).id;
    // 切换 chips 激活态：被点的 chip 高亮，其余清空（PRD §3.5.1 单选）
    const chips = this.data.chips.map((c) => ({ ...c, active: c.id === id }));
    this.setData({ chips });
    if (id === 'smart_analyze') {
      this.startSmartAnalyze();
      return;
    }
    // 其它 chips 暂时仅更新激活态 + toast 占位（保留旧 chip 行为）
    if (id === 'today') {
      wx.showToast({ title: '今天先做 1 件小事', icon: 'none' });
    } else if (id === 'chat') {
      wx.showToast({ title: '跟我说说你今天吧', icon: 'none' });
    } else if (id === 'compare') {
      wx.showToast({ title: '看看你走过的痕迹', icon: 'none' });
    }
  },

  /** PR-A4 Option A：触发智能分析 → 隐藏入口卡 + 追加 upload 气泡 */
  startSmartAnalyze() {
    if (this.data.smartAnalyzeRunning) return;
    // 同步 chips active 态：智能分析入口被触发后，chips 同步高亮
    const chips = this.data.chips.map((c) => ({ ...c, active: c.id === 'smart_analyze' }));
    const introTurn: ChatTurn = {
      id: 'u_intro_' + Date.now(),
      state: 'greeting',
      text: '好的，我需要 3 张照片来分析你的状态：\n• 正面脸部（素颜或淡妆）\n• 侧面体态（自然站立）\n• 发质特写（俯视45°）',
    };
    const uploadTurn: ChatTurn = {
      id: 'u_upload_' + Date.now(),
      state: 'upload',
      title: '上传照片（可跳过部分）',
      text: '至少 1 张，1-3 张最好',
      attachment: {
        kind: 'upload_card',
        slots: SMART_ANALYZE_SLOTS.map((s) => ({ ...s })),
        ageRanges: SMART_ANALYZE_AGE_RANGES.map((a) => ({ ...a })),
      },
    };
    // SPEC-A2 §3.1：避免双 source of truth —— 入口卡折叠由 collapseCardsOnFirstSend 统一处理
    this.collapseCardsOnFirstSend();
    this.setData({
      turns: [...this.data.turns, introTurn, uploadTurn],
      lastTurnId: uploadTurn.id,
      personaState: 'upload',
      chips,
    });
  },

  /**
   * PR-A4 Option A：upload 卡片内部交互
   *  - onUploadSlotTap(idx)    从相册/相机选图后填槽位（预览本地 tempFilePath）
   *  - onSelectAge(value)      切换年龄段
   *  - onSubmitUpload()        ≥1 张时 → 调 runSmartAnalyze（MinIO 上传 + SSE 分析）→ report
   *  - onStartPlan()           report 气泡的「开始 21 天」CTA
   */
  onUploadSlotTap(e: WechatMiniprogram.BaseEvent) {
    // upload-card 组件选完图后会把 { index, tempFilePath } 放在 event detail
    // - 旧版只读 e.detail.index（缺 tempFilePath）→ 槽位无图预览
    // - 现版读 e.detail.tempFilePath → 写 slot.filledUrl，wxml 用 <image> 渲染
    const detail = (e.detail ?? {}) as { index?: number; tempFilePath?: string };
    const idx = Number(detail.index);
    const tempFilePath = typeof detail.tempFilePath === 'string' ? detail.tempFilePath : '';
    // #region agent log
    dlog('assistant-home/index.ts:onUploadSlotTap.entry', 'slot tap', { idx, hasTempFilePath: !!tempFilePath, pathPrefix: tempFilePath ? tempFilePath.slice(0, 40) : null });
    // #endregion
    const lastTurn = this.data.turns[this.data.turns.length - 1];
    if (!lastTurn || lastTurn.state !== 'upload') return;
    const att = lastTurn.attachment;
    if (!att || att.kind !== 'upload_card') return;
    const slots = att.slots.map((s, i) =>
      i === idx
        ? { ...s, filled: Boolean(tempFilePath), filledUrl: tempFilePath || undefined }
        : s
    );
    this.setData({
      turns: this.data.turns.map((t, i) =>
        i === this.data.turns.length - 1 ? { ...t, attachment: { ...att, slots } } : t,
      ),
    });
  },

  onSelectAge(e: WechatMiniprogram.BaseEvent) {
    const value = (e.detail as { age?: string })?.age;
    const lastTurn = this.data.turns[this.data.turns.length - 1];
    if (!lastTurn || lastTurn.state !== 'upload') return;
    const att = lastTurn.attachment;
    if (!att || att.kind !== 'upload_card') return;
    const ageRanges = att.ageRanges.map((a) => ({ ...a, selected: a.value === value }));
    this.setData({
      turns: this.data.turns.map((t, i) =>
        i === this.data.turns.length - 1 ? { ...t, attachment: { ...att, ageRanges } } : t,
      ),
    });
  },

  onSubmitUpload() {
    // #region agent log
    dlog('assistant-home/index.ts:onSubmitUpload.entry', 'onSubmitUpload called', { turnCount: this.data.turns.length, lastState: this.data.turns[this.data.turns.length-1]?.state, sessionId: this.data.sessionId, smartAnalyzeRunning: this.data.smartAnalyzeRunning });
    // #endregion
    const lastTurn = this.data.turns[this.data.turns.length - 1];
    if (!lastTurn || lastTurn.state !== 'upload') {
      // #region agent log
      dlog('assistant-home/index.ts:onSubmitUpload.guard.lastTurn', 'guard: lastTurn not upload', { hasLast: !!lastTurn, lastState: lastTurn?.state });
      // #endregion
      return;
    }
    const att = lastTurn.attachment;
    if (!att || att.kind !== 'upload_card') {
      // #region agent log
      dlog('assistant-home/index.ts:onSubmitUpload.guard.att', 'guard: attachment not upload_card', { hasAtt: !!att, attKind: att?.kind });
      // #endregion
      return;
    }

    // V5.2.1-PR5 FR-7 §5.2.1-3 微调 2：缺料前置校验（≥1 张图 + face 必含 + ≥3 项档案）。
    // 纯函数 checkSmartAnalyzePrerequisites 返回 reason，UI 副作用按 reason 分档：
    //   - no_photo / no_face → showToast（硬阻断）
    //   - profile_insufficient → showModal（软阻断，给"继续分析"兜底）
    // 槽位 label → bodyPart 映射：'正面脸部' = face / '侧面体态' = shoulder_neck / '发质特写' = head
    const LABEL_TO_BODYPART: Record<string, string> = {
      '正面脸部': 'face',
      '侧面体态': 'shoulder_neck',
      '发质特写': 'head',
    };
    const slotsForCheck = att.slots.map((s, idx) => ({
      index: idx,
      label: s.label,
      bodyPart: LABEL_TO_BODYPART[s.label] ?? 'face',
      filled: s.filled,
      filledUrl: s.filledUrl,
    }));
    const profile = readUserProfile();
    const prereq = checkSmartAnalyzePrerequisites({ slots: slotsForCheck, profile });

    if (!prereq.ok) {
      if (prereq.reason === 'no_photo') {
        dlog('assistant-home/index.ts:onSubmitUpload.guard.noPhoto', 'guard: no_photo', {});
        wx.showToast({ title: '请至少上传 1 张照片', icon: 'none' });
        return;
      }
      if (prereq.reason === 'no_face') {
        dlog('assistant-home/index.ts:onSubmitUpload.guard.noFace', 'guard: no_face', {});
        wx.showToast({ title: '请上传面部照片（必备）', icon: 'none' });
        return;
      }
      // profile_insufficient：弹 modal 让用户选择
      const filled = prereq.filledCount ?? 0;
      const missing = prereq.missing ?? 3;
      dlog('assistant-home/index.ts:onSubmitUpload.guard.profileInsufficient', 'guard: profile_insufficient', { filled, missing });
      wx.showModal({
        title: '档案未完善',
        content: `已完善 ${filled}/6 项档案，还需 ${missing} 项才能获得针对性分析。是否现在去完善档案？`,
        confirmText: '去完善',
        cancelText: '继续分析',
        success: (res) => {
          if (res.confirm) {
            wx.navigateTo({ url: '/pages/profile/index' });
          } else {
            // "继续分析" 兜底：仍发请求，后端 PR4 F4 is_fallback=true 兜底
            this.runSmartAnalyze();
          }
        },
      });
      return;
    }

    // #region agent log
    dlog('assistant-home/index.ts:onSubmitUpload.invokeStartSmart', 'invoking runSmartAnalyze', { filledCount: slotsForCheck.filter((s) => s.filled).length, profileFilledCount: countFilledFields(profile), sessionId: this.data.sessionId });
    // #endregion
    this.runSmartAnalyze();
  },

  /** SSE-driven smart analyze 入口（PR-A4 Option A + worker 本轮改造）。
   *
   *  调用前需要：用户至少在 upload_card 槽位里选了 1 张图（filledUrl 是本地 tempFilePath）。
   *  本方法执行：
   *    1) 槽位 index → body_part 映射（与后端 ``_validate_image_keys`` 强一致）
   *    2) 对每个 filledUrl 调 ``presignAndUploadOneForAssistant`` 拿到 object_key
   *       （purpose=assistant/，后端 whitelist 已扩）
   *    3) POST /assistant/sessions/{id}/messages 携带
   *       ``{text, image_keys, body_parts}``，触发 send_message_stream
   *       → SSE：start → progress ×N → report → end
   *    4) 消费交给 ``consumeAssistantStream``
   *
   *  取消 / 错误策略：
   *    - 用户主动取消（点 ✕ / 离开页 / 重发）：cancelSmartAnalyze → AbortController.abort()
   *      → 保留 progress_card / report_card，不 toast 失败
   *    - 后端 5xx / 4xx → toast「分析服务暂时不可用」+ 清理 + 重置 smartAnalyzeRunning
   *    - medical_guarded → 走 FSM medical_guarded 分支
   */
  async runSmartAnalyze() {
    const sid = this.data.sessionId;
    // #region agent log
    dlog('assistant-home/index.ts:runSmartAnalyze.entry', 'runSmartAnalyze entry', {
      hasSid: !!sid,
      sidPrefix: sid ? sid.slice(0, 8) : null,
      hasGlobalAbort: typeof AbortController !== 'undefined',
    });
    // #endregion
    // 无可用 session_id（首次进页面后端不通，或 fallback 占位 id）：尝试重试一次再放弃
    if (!sid || sid.startsWith('dev_session_')) {
      await this.ensureSession();
      const sid2 = this.data.sessionId;
      if (!sid2 || sid2.startsWith('dev_session_')) {
        // #region agent log
        dlog('assistant-home/index.ts:runSmartAnalyze.noSid', 'no sessionId after retry', {});
        // #endregion
        wx.showToast({ title: '网络异常，稍后再试', icon: 'none' });
        return;
      }
      // 拿到新 sid 后继续递归；runSmartAnalyze 顶部 setData 上传前会重置 analyzing 气泡
      return this.runSmartAnalyze();
    }

    const lastTurn = this.data.turns[this.data.turns.length - 1];
    if (!lastTurn || lastTurn.state !== 'upload') return;
    const att = lastTurn.attachment;
    if (!att || att.kind !== 'upload_card') return;
    const filledSlots = att.slots
      .map((s, idx) => ({ slot: s, idx }))
      .filter((x) => x.slot.filled && !!x.slot.filledUrl);
    if (filledSlots.length < 1) {
      wx.showToast({ title: '请至少上传 1 张照片', icon: 'none' });
      return;
    }

    // 0) 先追加 analyzing 气泡（percent=0，等 SSE start/progress 真正推进）
    const analyzeTurn: ChatTurn = {
      id: 'a_analyzing_' + Date.now(),
      state: 'analyzing',
      title: '收到，我开始分析你的照片…',
      text: '正在上传并分析，约需 8-15 秒',
      attachment: {
        kind: 'progress_card',
        percent: 0,
        title: '正在分析，约需 8-15 秒',
        steps: [
          { label: '正在识别体态状态', done: false, current: false },
          { label: '分析面部状态', done: false, current: false },
          { label: '生成养护建议', done: false, current: false },
        ],
      },
    };
    this.setData({
      turns: [...this.data.turns, analyzeTurn],
      lastTurnId: analyzeTurn.id,
      personaState: 'analyzing',
      smartAnalyzeRunning: true,
    });

    // 1) 槽位 index → body_part 映射；顺序与 filledSlots 顺序一致（保持 image_keys/body_parts 1:1）。
    const SMART_ANALYZE_INDEX_TO_BODYPART: ReadonlyArray<BodyPart> = [
      'face',
      'shoulder_neck',
      'head',
    ];
    const pickedForUpload = filledSlots.map(({ slot, idx }) => ({
      // 构造 PickedImage 最小子集（utils/upload-helper 仅读 path + compressedSize）
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      picked: { path: slot.filledUrl!, compressedSize: 0, size: 0, width: 0, height: 0 } as any,
      bodyPart: (SMART_ANALYZE_INDEX_TO_BODYPART[idx] ?? 'face') as BodyPart,
    }));

    // 2) 真上传：每张图走 presignAndUploadOneForAssistant → object_key
    let uploaded: UploadedPhoto[];
    try {
      const tasks = pickedForUpload.map(({ picked, bodyPart }) =>
        presignAndUploadOneForAssistant(picked, bodyPart),
      );
      uploaded = await Promise.all(tasks);
      // #region agent log
      dlog(
        'assistant-home/index.ts:runSmartAnalyze.uploaded',
        'presign+upload done',
        {
          objectKeys: uploaded.map((u) => u.objectKey),
          bodyParts: uploaded.map((u) => u.bodyPart),
          count: uploaded.length,
        },
      );
      // #endregion
      // 让 dev 能直接从 console 验证图片进了 MinIO
      // eslint-disable-next-line no-console
      console.log(
        '[assistant-home] presigned keys:',
        uploaded.map((u) => ({
          object_key: u.objectKey,
          cdn_url: u.objectKey,
        })),
      );
    } catch (e) {
      // #region agent log
      dlog('assistant-home/index.ts:runSmartAnalyze.uploadFail', 'presign/upload threw', {
        errMsg: e instanceof Error ? e.message : String(e),
      });
      // #endregion
      wx.showToast({ title: '图片上传失败，请重试', icon: 'none' });
      this.applyAssistantError({ code: 'UPLOAD_FAILED', message_zh: '图片上传失败' });
      return;
    }

    const imageKeys = uploaded.map((u) => u.objectKey);
    const bodyParts = uploaded.map((u) => u.bodyPart);
    // 清空上一轮 SSE 残留的 report directions（避免 end 先到 / report 后到时复用旧数据）
    (this.data as { _pendingReportDirections?: unknown[] })._pendingReportDirections = [];

    // 3) 启动 SSE consumer（AbortController 桥接见 cancelSmartAnalyze）
    let ac: AbortController;
    try {
      ac = new AbortController();
    } catch (e) {
      // #region agent log
      dlog('assistant-home/index.ts:runSmartAnalyze.acThrow', 'AbortController ctor threw', {
        errMsg: e instanceof Error ? e.message : String(e),
      });
      // #endregion
      throw e;
    }
    const consumerSignal = ac.signal;
    (this.data as { _sseAbortController: AbortController | null })._sseAbortController = ac;

    const baseURL = API_BASE_URL[CURRENT_ENV];
    const url = `${baseURL}/assistant/sessions/${encodeURIComponent(sid)}/messages`;
    // #region agent log
    dlog('assistant-home/index.ts:runSmartAnalyze.consumeSse', 'about to call consumeSse', {
      url,
      method: 'POST',
      imageKeysLen: imageKeys.length,
      bodyPartsLen: bodyParts.length,
    });
    // #endregion
    const consumer: SseConsumer = consumeSse(url, {
      method: 'POST',
      // 后端 AssistantMessage（assistant_v1.py）字段：text / image_keys[] / body_parts[] / profile（PR5）
      // image_keys 有值触发 smart_analyze 模式（_stream_smart_analyze）；
      // body_parts 与 image_keys 一一对应，与后端 _validate_image_keys 白名单一致；
      // profile 由 utils/profile-storage.ts 读 storage 拼装，全 null 时省略（PR5 FR-6）。
      // #region agent log
      // body 构造委托给纯函数 buildSmartAnalyzeBody（jest 测试覆盖）；page.ts 不直接拼接 profile。
      body: buildSmartAnalyzeBody({
        text: 'smart_analyze',
        imageKeys,
        bodyParts,
      }) as unknown as Record<string, unknown>,
      // #endregion
      header: {
        Accept: 'text/event-stream',
        Authorization: `Bearer ${wx.getStorageSync('jwt') || ''}`,
      },
      onTerminal: () => {
        // done / error 触发；保留 smartAnalyzeRunning 重置在 caller 处处理
      },
    });
    (this.data as { _sseConsumer: SseConsumer | null })._sseConsumer = consumer;

    // 把 AbortSignal 映射到 consumer.cancel()（一次性；重复 abort 幂等）
    const abortBridge = () => {
      try { consumer.cancel(); } catch { /* ignore */ }
      (this.data as { _sseAbortController: AbortController | null })._sseAbortController = null;
    };
    if (consumerSignal.aborted) {
      abortBridge();
    } else {
      consumerSignal.addEventListener('abort', abortBridge, { once: true });
    }

    void this.consumeAssistantStream(consumer);
  },

  /**
   * Stream Y / worker Y：用户主动取消（点 ✕ / 离开页 / 重发等场景）。
   * - 语义：保留 progress_card / report_card 当前内容，不擦除；
   * - 只重置 smartAnalyzeRunning；
   * - 不调用 applyAssistantError，不 toast 失败（取消不是错误）；
   * - 后端收到 disconnect 后不再继续流式推帧，前端自然结束消费循环。
   */
  cancelSmartAnalyze() {
    const ac = (this.data as { _sseAbortController?: AbortController | null })._sseAbortController;
    if (ac) {
      try { ac.abort(); } catch { /* ignore */ }
      (this.data as { _sseAbortController: AbortController | null })._sseAbortController = null;
    }
    // 兜底：直接清 consumer + 重置 running 标志
    const c = (this.data as { _sseConsumer?: SseConsumer | null })._sseConsumer;
    if (c) {
      try { c.cancel(); } catch { /* ignore */ }
      (this.data as { _sseConsumer: SseConsumer | null })._sseConsumer = null;
    }
    this.setData({ smartAnalyzeRunning: false });
  },

  async consumeAssistantStream(consumer: SseConsumer): Promise<void> {
    try {
      for await (const rawEvt of consumer.events) {
        // 兼容后端事件名（progress/report/end/start）；SseEventName 限制为 stage/done/error，
        // 这里做运行时 cast，types/api.ts 契约不动。
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const evt = rawEvt as SseEvent & { name: string; data: any };
        const name = evt.name as string;
        // #region agent log
        dlog('assistant-home/index.ts:consumeAssistantStream.event', 'SSE event received', { name, dataKeys: evt.data && typeof evt.data === 'object' ? Object.keys(evt.data) : null });
        // #endregion
        if (name === 'progress') {
          this.applyAssistantProgress(evt.data);
          continue;
        }
        if (name === 'report') {
          this.applyAssistantReport(evt.data);
          continue;
        }
        if (name === 'end') {
          this.applyAssistantEnd(evt.data);
          break;
        }
        if (name === 'error') {
          this.applyAssistantError(evt.data);
          break;
        }
        if (name === 'start') {
          // start 事件只是「连接已建」，不动 UI；当前 case 留作未来 hook
          continue;
        }
        if (name === 'done' || name === 'stage') {
          // 与 diagnosis 域事件名兼容（如后端未来切到 stage/done）；当前不消费
          continue;
        }
      }
    } catch (err) {
      // Stream Y / worker Y：用户主动 abort → 不调用 applyAssistantError，不 toast
      if ((err as { name?: string })?.name === 'AbortError') {
        // 已在 cancelSmartAnalyze / onUnload 内重置 smartAnalyzeRunning，不重复 setData
        return;
      }
      // 兜底：补一个网络异常 toast（保留旧行为）
      console.warn('[assistant-home] SSE consume loop fail', err);
      this.applyAssistantError({ code: 'NETWORK_ERROR', message_zh: '网络异常，请稍后重试' });
    } finally {
      consumer.cancel();
      (this.data as { _sseConsumer: SseConsumer | null })._sseConsumer = null;
    }
  },

  applyAssistantProgress(payload: { step?: number; percent?: number; label?: string }): void {
    const last = this.data.turns[this.data.turns.length - 1];
    if (!last || last.state !== 'analyzing') return;
    const att = last.attachment;
    if (!att || att.kind !== 'progress_card') return;
    const percent = Math.max(0, Math.min(100, Number(payload.percent) || 0));
    // 当前激活步：与后端 step 1:1（step=1 → 0, step=2 → 1, step=3 → 2）
    // 防御：后端可能只发 percent 不发 step；NaN 守卫：若 step 不是有限数，按 percent/33 兜底推断
    const rawStep = Number(payload.step);
    const stepIdx = Number.isFinite(rawStep) && rawStep >= 1
      ? Math.min(att.steps.length - 1, Math.floor(rawStep) - 1)
      : Math.min(att.steps.length - 1, Math.floor(percent / 33));
    const steps = att.steps.map((s, i) => {
      if (percent >= (i + 1) * 33) return { ...s, done: true, current: false };
      return { ...s, done: false, current: i === stepIdx };
    });
    this.setData({
      turns: this.data.turns.map((t, i) =>
        i === this.data.turns.length - 1
          ? { ...t, attachment: { ...att, percent, steps } }
          : t,
      ),
    });
  },

  applyAssistantReport(payload: { directions?: Array<{ num: number; title: string; level: string; description: string }> }): void {
    const directions = Array.isArray(payload.directions) ? payload.directions : [];
    // 等 end 事件再渲染 report 气泡（保持节拍一致：progress 100% → 短停顿 → report 淡入）
    (this.data as { _pendingReportDirections: typeof directions })._pendingReportDirections = directions;
  },

  applyAssistantEnd(payload: { ok?: boolean; medical_guarded?: boolean; reply?: string; persona_state?: string }): void {
    if (payload.medical_guarded) {
      // 走 medical_guarded FSM（onSend 已先拦截；此处是兜底）
      const guardTurn: ChatTurn = {
        id: 'g_' + Date.now(),
        state: 'medical_guarded',
        text: '我听到了，但涉及医疗的事，建议找专业医生聊聊比较稳妥。我可以陪你记录心情。',
      };
      this.setData({
        turns: [...this.data.turns, guardTurn],
        lastTurnId: guardTurn.id,
        personaState: 'medical_guarded',
        smartAnalyzeRunning: false,
      });
      return;
    }
    const pending = (this.data as { _pendingReportDirections?: Array<{ num: number; title: string; level: string; description: string }> })._pendingReportDirections ?? [];
    this.renderAssistantReport(pending);
  },

  applyAssistantError(payload: { code?: string; message_zh?: string }): void {
    // #region agent log
    dlog('assistant-home/index.ts:applyAssistantError', 'applyAssistantError called', { code: payload.code, msg: payload.message_zh });
    // #endregion
    const msg = payload.message_zh || '分析服务暂时不可用';
    wx.showToast({ title: msg, icon: 'none' });
    // 清理 analyzing 气泡 → 替换为失败提示
    // personaState 兜底：仅当 turns 最后一个确实是 analyzing 时回退到 upload；否则保持现状避免状态错乱
    const last = this.data.turns[this.data.turns.length - 1];
    const lastIsAnalyzing = !!(last && last.state === 'analyzing');
    this.setData({
      personaState: lastIsAnalyzing ? 'upload' : this.data.personaState,
      smartAnalyzeRunning: false,
      turns: this.data.turns.map((t, i) =>
        i === this.data.turns.length - 1 && t.state === 'analyzing'
          ? { ...t, state: 'answer' as const, text: msg }
          : t,
      ),
    });
  },

  /** 渲染报告气泡：directions 由 SSE report 事件累计，end 事件触发；缺省走 FALLBACK_DIRECTIONS。 */
  renderAssistantReport(
    directions?: Array<{ num: number; title: string; level: string; description: string }>,
  ) {
    const finalDirs =
      directions && directions.length > 0
        ? directions
        : SMART_ANALYZE_FALLBACK_DIRECTIONS.map((d) => ({ ...d }));
    const reportTurn: ChatTurn = {
      id: 'a_report_' + Date.now(),
      state: 'report',
      title: '你的照片我看完了，找到 3 个值得注意的方向。',
      text: '小满，这是你的 3 个改善方向',
      attachment: {
        kind: 'report_card',
        avatarText: '满',
        name: '小满',
        directions: finalDirs,
      },
    };
    this.setData({
      turns: [...this.data.turns, reportTurn],
      lastTurnId: reportTurn.id,
      personaState: 'report',
      smartAnalyzeRunning: false,
    });
  },

  /**
   * SSE 不可用时的本地降级（保留 UI 联调通畅；生产态不应进入）。
   * 仅在 runSmartAnalyze 的 catch/极端异常分支调用；当前实现保留以备后端 SSE
   * 整体不可用时仍能让 UI 走到 analyzing → report 的视觉过渡。
   * 报告方向直接用 ``SMART_ANALYZE_FALLBACK_DIRECTIONS``（与后端 fallback 静态清单同源）。
   */
  runLocalFallbackAnalyze(): void {
    // 清空上一轮 SSE 残留的 report directions（保持 fallback 路径与 SSE 路径状态一致）
    (this.data as { _pendingReportDirections?: unknown[] })._pendingReportDirections = [];
    this.setData({
      turns: [
        ...this.data.turns,
        {
          id: 'a_analyzing_' + Date.now(),
          state: 'analyzing' as const,
          title: '收到，我开始分析你的照片…',
          text: '正在分析，约需 8-15 秒',
          attachment: {
            kind: 'progress_card' as const,
            percent: 0,
            title: '正在分析，约需 8-15 秒',
            steps: [
              { label: '正在识别体态状态', done: false, current: true },
              { label: '分析面部状态', done: false, current: false },
              { label: '生成养护建议', done: false, current: false },
            ],
          },
        },
      ],
      personaState: 'analyzing' as const,
      smartAnalyzeRunning: true,
    });
    let percent = 0;
    const timer = setInterval(() => {
      percent = Math.min(100, percent + 20);
      const last = this.data.turns[this.data.turns.length - 1];
      if (!last || last.state !== 'analyzing') {
        clearInterval(timer);
        return;
      }
      const att = last.attachment;
      if (!att || att.kind !== 'progress_card') {
        clearInterval(timer);
        return;
      }
      const steps = att.steps.map((s, i) => {
        if (percent >= (i + 1) * 33) return { ...s, done: true, current: false };
        return { ...s, current: i === Math.floor(percent / 33) };
      });
      this.setData({
        turns: this.data.turns.map((t, i) =>
          i === this.data.turns.length - 1
            ? { ...t, attachment: { ...att, percent, steps } }
            : t,
        ),
      });
      if (percent >= 100) {
        clearInterval(timer);
        setTimeout(() => this.renderAssistantReport(), 400);
      }
    }, 300);
    (this.data as { _progressTimer: ReturnType<typeof setInterval> | null })._progressTimer = timer;
  },

  /** report 气泡的「开始 21 天」CTA → /pages/plan-tabs/index（PR-A4 已就绪） */
  onStartPlan() {
    wx.navigateTo({ url: '/pages/plan-tabs/index' });
  },

  onTapHistory() {
    wx.showToast({ title: '查看历史', icon: 'none' });
  },

  onTapSettings() {
    wx.showToast({ title: '设置', icon: 'none' });
  },

  onTapMic() {
    wx.showToast({ title: '按住开始录音', icon: 'none' });
  },

  onTapCamera() {
    wx.showToast({ title: '拍照上传', icon: 'none' });
  },

  onNavBack() {
    // assistant-home 是 tabBar 页面（app.json tabBar.list 第 2 项）：
    //   - wx.navigateBack 在 tabBar 上静默失败（无 toast、无 fail），用户看不到任何反应
    //   - wx.reLaunch 跳 tabBar 在不同基础库行为不一致（部分版本会被忽略）
    //   - 业务预期"点 ‹ 回聊天页（首页 tab）"—— 正确做法是 wx.switchTab
    // 兜底链：navigateBack(可退回) → switchTab(回 home tab) → reLaunch(所有手段都失败)
    const pages = getCurrentPages();
    console.log('[assistant-home] onNavBack tapped, stack depth =', pages.length);
    if (pages.length > 1) {
      wx.navigateBack({
        delta: 1,
        fail: () => this.fallbackToHomeTab(),
      });
      return;
    }
    this.fallbackToHomeTab();
  },

  /** nav-back 兜底链：优先 switchTab 回 home tab（tabBar 页面只能这么跳），
   *  再退化为 reLaunch 跳 home。 */
  fallbackToHomeTab() {
    wx.switchTab({
      url: '/pages/home/index',
      fail: () => {
        wx.reLaunch({ url: '/pages/home/index' });
      },
    });
  },

  onNavAction() {
    wx.showActionSheet({
      itemList: ['清空对话', '退出登录', '帮助'],
      success: (res) => {
        if (res.tapIndex === 0) {
          this.setData({
            turns: [],
            entryHidden: false,
            personaState: 'greeting',
            lastTurnId: '',
            smartAnalyzeRunning: false,
          });
        }
      },
    });
  },
});