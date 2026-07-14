/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P03a 智能管家对话主页
 * 设计稿: docs/design/figma-pixso-spec/pages/04a-smart-analyze-dialog.html
 * 后端端点:
 *   - openapi.yaml tag=assistant operationId=createSession    POST /assistant/sessions
 *   - openapi.yaml tag=assistant operationId=sendMessage      POST /assistant/sessions/{id}/messages
 *   - openapi.yaml tag=butler   operationId=triggerRecall     GET  /butler/recall/{day}
 *
 * 行为（PR-8 v2：智能分析 = 独立页面流，聊天页只做 AI 自由对话兜底）：
 *  1) 进入页面 → POST /assistant/sessions 建会话（4 态 FSM：greeting → listening → thinking → answer）
 *  2) 顶部 entry cards 持久化（PRD §3.5.2：3 入口卡持续可见）
 *  3) 点「智能分析」入口卡或 🔍 智能分析 chip → wx.navigateTo /pages/diagnosis-upload-v2/index
 *  4) 用户输入 → listening → medical_guard / A 类路由 / B 类快问 → sendMessage SSE 流（token_delta）
 *  5) A 类路由命中关键词 → wx.navigateTo 到对应业务页
 *  6) chips 4 项：smart_analyze 跳 v2 上传；其它 chips 仅 toast 兜底
 *
 * 历史遗留（PR-A4 chat 流）已全部删除：upload-card / progress-card / report-card
 * 内嵌气泡、`startSmartAnalyze` / `onSubmitUpload` / `runSmartAnalyze` 等 SSE 5 阶段消费逻辑
 * 全部迁出到独立 v2 页面。
 */
// PR-A4 worker Y：用 AbortController 做 SSE 取消；微信基础库 2.32.3 尚未原生支持，
// 必须先 import 本 polyfill 注入 globalThis.AbortController，否则
// `new AbortController()` 抛 ReferenceError。
// 仅 import 即生效，installAbortControllerPolyfill() 会在模块加载时自动执行。
import '../../utils/abort-controller-polyfill';
import { dlog } from '../../utils/dlog';
import { post, ApiException } from '../../utils/request';
import { consumeSse, type SseConsumer, type SseEvent } from '../../utils/sse-http';
import { API_BASE_URL, CURRENT_ENV, getHomeTabUrl } from '../../utils/config';
import { pickRandomAck } from '../../data/ack-pool';

type PersonaState = 'greeting' | 'listening' | 'thinking' | 'answer' | 'medical_guarded';

interface ChatTurn {
  id: string;
  state: PersonaState;
  text: string;
  title?: string;
}

interface AssistantSessionResp {
  session_id: string;
}

/** SPEC-A2 §2.1 / §6.1：入口卡折叠 FSM 三态 */
type ButlerCardsMode = 'expanded' | 'collapsed' | 'focused';

/** A 类意图关键词（≥ 20 条；与 §6.3 实施规范对齐）
 *  v2 路由指向 v2 页面或保留页面（plan-tabs 已删，统一改 plan-delivery 占位）。
 *  本表与 v1 行为兼容，关键词命中 → 路由到对应业务页。
 */
const ROUTE_KEYWORDS: Array<{ kw: RegExp; module: string; page: string }> = [
  { kw: /诊断|分析|照片|皮肤|状态/, module: 'diagnosis', page: '/pages/diagnosis-upload-v2/index' },
  { kw: /方案|计划|21天|21 天/, module: 'plan', page: '/pages/plan-delivery/index' },
  { kw: /打卡|今日|完成/, module: 'checkin', page: '/pages/checkin/index' },
  { kw: /日记|心情|记录|感受/, module: 'diary', page: '/pages/feedback-diary/index' },
  { kw: /回忆|过去|那天/, module: 'recall', page: '/pages/recall-compare/index' },
  { kw: /广场|社区|看看别人/, module: 'plaza', page: '/pages/community/index' },
  { kw: /抱抱|海报|分享/, module: 'hug', page: '/pages/share-hug-card/index' },
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

/** v2 智能分析入口统一跳转路径（PR-8 落地，4 个独立页面流） */
const SMART_ANALYZE_V2_URL = '/pages/diagnosis-upload-v2/index';

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
    /** 3 张入口卡（PRD §3.5.2 持久显示：智能分析 / 心情日记 / 主动回忆）
     *  v2：smart_analyze 走独立页面（无 direct_input 占位）
     */
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
      { id: 'today', text: '📅 今日 · 第 1 天', active: false, dayIndex: 1 },
      { id: 'chat', text: '💬 聊聊今天', active: false },
      { id: 'compare', text: '📊 查看对比', active: false },
    ],
    lastTurnId: 't0',
    /** 抽屉状态 */
    drawerVisible: false,
    /** 当前天数（15a原型 day-banner） */
    currentDay: 0,
    dayEncourageText: '',
  },

  onLoad() {
    this.ensureSession();
    this._loadCurrentDay();
  },

  /** 加载当前天数（day-banner） */
  async _loadCurrentDay() {
    try {
      const me = await import('../../utils/request').then(m => m.get<{ current_streak_days?: number }>('/users/me'));
      const day = me?.current_streak_days ?? 0;
      const encourageText = day === 0
        ? '今天是新开始 🌿'
        : day < 7
        ? '已坚持 1 周，慢慢来'
        : day < 14
        ? '走到一半了，慢慢来'
        : '已坚持两周多，继续加油';
      this.setData({ currentDay: day, dayEncourageText: encourageText });
    } catch { /* 兜底不展示 banner */ }
  },

  /** 抽屉开关 */
  onOpenDrawer() { this.setData({ drawerVisible: true }); },
  onCloseDrawer() { this.setData({ drawerVisible: false }); },

  /** 抽屉内导航 */
  onDrawerNav(e: WechatMiniprogram.TapEvent) {
    const page = String((e.currentTarget.dataset as { page?: string }).page ?? '');
    this.setData({ drawerVisible: false });
    if (!page) return;
    const routes: Record<string, string> = {
      home: '/pages/home/index',
      'diagnosis-upload-v2': '/pages/diagnosis-upload-v2/index',
      'feedback-diary': '/pages/feedback-diary/index',
      album: '/pages/album/index',
      'notification-settings': '/pages/notification-settings/index',
    };
    const url = routes[page];
    if (url) wx.switchTab({ url }).catch(() => wx.navigateTo({ url }));
  },

  /** 心情 chips 快速反馈 */
  onTapChip(e: WechatMiniprogram.TapEvent) {
    const text = String((e.currentTarget.dataset as { text?: string }).text ?? '');
    if (!text) return;
    wx.showToast({ title: `已记录：${text}`, icon: 'none' });
    // 也发送到 chat 流
    this.setData({ inputText: text });
    void this.onSend();
  },

  onUnload() {
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
   * 首次发送后折叠（被 onSend 复用）
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
      // 后端不可达：用占位 session_id 让 UI 仍可渲染；后续 runChatStream
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
    // PR-A2 worker C：发新消息前先 abort 现有 SSE consumer，避免 chat 流被中途打断
    const c = (this.data as { _sseConsumer?: SseConsumer | null })._sseConsumer;
    if (c) {
      try { c.cancel(); } catch { /* ignore */ }
      (this.data as { _sseConsumer: SseConsumer | null })._sseConsumer = null;
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
    // PR-3 commit-3 · chat 模式改 SSE（vision-pipeline Sprint 2）：
    // - 追加 answer 气泡（state=answer，text='' 等打字机拼接）
    // - 调 _stream_chat SSE：start → token_delta ×N → end
    // - medical_guarded / A 类路由已在前面 return，不进 chat 路径
    try {
      const answer: ChatTurn = {
        id: 'a_' + Date.now(),
        state: 'answer',
        text: '',
      };
      this.setData({
        turns: [...this.data.turns, answer],
        personaState: 'answer',
        lastTurnId: answer.id,
      });
      await this.runChatStream({ text, isQuick });
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
        turns: this.data.turns.map((t, i) =>
          i === this.data.turns.length - 1 && t.state === 'answer' && !t.text
            ? answer
            : t,
        ),
        personaState: 'greeting',
        lastTurnId: answer.id,
      });
    }
  },

  /**
   * 点击入口卡（3 张：smart_analyze / mood_diary / recall_self）
   *  v2 行为：
   *  - smart_analyze  → wx.navigateTo /pages/diagnosis-upload-v2/index（独立页面流）
   *  - mood_diary     → 跳转 feedback-diary（保留旧行为）
   *  - recall_self    → 进入主动回忆对话流
   */
  onTapEntry(e: WechatMiniprogram.BaseEvent) {
    // 事件源是 <butler-cards-block bind:cards-tap="onTapEntry">，e.currentTarget 是
    // 整个 butler-cards-block 容器，没有 dataset.id；子组件 triggerEvent 把 id 放在 e.detail 里
    const id = ((e.detail as { id?: string })?.id
      ?? (e.currentTarget?.dataset as { id?: string } | undefined)?.id
      ?? '') as 'smart_analyze' | 'mood_diary' | 'recall_self' | '';
    if (id === 'smart_analyze') {
      wx.navigateTo({ url: SMART_ANALYZE_V2_URL });
      return;
    }
    if (id === 'mood_diary') {
      wx.navigateTo({ url: '/pages/feedback-diary/index' });
      return;
    }
    if (id === 'recall_self') {
      wx.navigateTo({
        url: '/pages/recall-flow/index?trigger=user_manual&days_offset=7',
      });
      return;
    }
  },

  /** 点击 chips（4 项：智能分析 / 今日 / 聊聊今天 / 查看对比）
   *  v2 行为：smart_analyze 跳独立页面，其它 chip 仅更新 active 态 + toast 占位。
   */
  onTapChip(e: WechatMiniprogram.TapEvent) {
    const id = String((e.currentTarget.dataset as { id?: string }).id ?? '');
    const chips = this.data.chips.map((c) => ({ ...c, active: c.id === id }));
    this.setData({ chips });
    if (id === 'smart_analyze') {
      wx.navigateTo({ url: SMART_ANALYZE_V2_URL });
    } else if (id === 'today') {
      wx.showToast({ title: '今天先做 1 件小事', icon: 'none' });
    } else if (id === 'chat') {
      wx.showToast({ title: '跟我说说你今天吧', icon: 'none' });
    } else if (id === 'compare') {
      wx.navigateTo({ url: '/pages/recall-compare/index' });
    }
  },

  /**
   * PR-3 commit-3 · chat 模式 SSE 流（vision-pipeline Sprint 2 · _stream_chat）：
   *  - body 不带 image_keys/body_parts（chat 模式无图）
   *  - 后端走 _stream_chat（assistant_service.py:916），事件序列：start → token_delta ×N → end
   *  - token_delta 走 applyTokenDelta 拼接；end 由 consumeAssistantStream 已有逻辑覆盖
   *  - 取消 / 错误策略：AbortController + AbortError 静默退出
   */
  async runChatStream(opts: { text: string; isQuick: boolean }): Promise<void> {
    const sid = this.data.sessionId;
    if (!sid || sid.startsWith('dev_session_')) {
      await this.ensureSession();
      const sid2 = this.data.sessionId;
      if (!sid2 || sid2.startsWith('dev_session_')) {
        throw new Error('no_session');
      }
    }
    const finalSid = this.data.sessionId;
    const ac = new AbortController();
    (this.data as { _sseAbortController: AbortController | null })._sseAbortController = ac;
    const baseURL = API_BASE_URL[CURRENT_ENV];
    const url = `${baseURL}/assistant/sessions/${encodeURIComponent(finalSid)}/messages`;
    const consumer: SseConsumer = consumeSse(url, {
      method: 'POST',
      // chat 模式：无图 → 后端走 _stream_chat（PR-3 commit-3 关键契约）
      body: { text: opts.text, is_quick: opts.isQuick },
      header: {
        Accept: 'text/event-stream',
        Authorization: `Bearer ${wx.getStorageSync('jwt') || ''}`,
      },
      onTerminal: () => {
        // done / error 触发
      },
    });
    (this.data as { _sseConsumer: SseConsumer | null })._sseConsumer = consumer;

    const abortBridge = () => {
      try { consumer.cancel(); } catch { /* ignore */ }
      (this.data as { _sseAbortController: AbortController | null })._sseAbortController = null;
    };
    if (ac.signal.aborted) {
      abortBridge();
    } else {
      ac.signal.addEventListener('abort', abortBridge, { once: true });
    }
    // 复用同一个 consumeAssistantStream；token_delta 分支自动生效
    await this.consumeAssistantStream(consumer);
  },

  /**
   * PR-3 commit-3 · chat 打字机 SSE 消费循环。
   * v2 简化：chat 流只关心 token_delta 与 terminal（done/error），智能分析 5 阶段
   * （progress/report/end）已迁出到独立 v2 页面，此处不再分发。
   */
  async consumeAssistantStream(consumer: SseConsumer): Promise<void> {
    try {
      for await (const rawEvt of consumer.events) {
        const evt = rawEvt as SseEvent & { name: string };
        const name = (evt as { name?: string }).name ?? '';
        // #region agent log
        dlog('assistant-home/index.ts:consumeAssistantStream.event', 'SSE event received', { name });
        // #endregion
        if (name === 'token_delta') {
          const tokenDelta: { token?: string } = evt.data as { token?: string };
          this.applyTokenDelta(evt.data);
          continue;
        }
        if (name === 'end' || name === 'done' || name === 'error') {
          // chat 流 terminal；personaState 兜底回 greeting，do nothing extra
          break;
        }
        if (name === 'start') {
          // start 事件只是「连接已建」，不动 UI
          continue;
        }
        // 其他事件（stage 等向后兼容）忽略
      }
    } catch (err) {
      // Stream Y / worker Y：用户主动 abort → 不调用 applyAssistantError，不 toast
      if ((err as { name?: string })?.name === 'AbortError') {
        // 已在 onUnload 内重置，不重复 setData
        return;
      }
      // 兜底：补一个网络异常 toast（保留旧行为）
      console.warn('[assistant-home] SSE consume loop fail', err);
    } finally {
      consumer.cancel();
      (this.data as { _sseConsumer: SseConsumer | null })._sseConsumer = null;
    }
  },

  /**
   * PR-3 commit-3 · chat 打字机（vision-pipeline Sprint 2）：
   * - 把 token 增量（payload.token）拼接到最后一个 answer 气泡的 text
   * - 仅在 state === 'answer' 时生效；其他 state 忽略
   * - 防御：token 必须是 string 且非空，避免无效 setData 抖动
   */
  applyTokenDelta(payload: { token?: string }): void {
    const token = typeof payload?.token === 'string' ? payload.token : '';
    if (!token) return;
    const last = this.data.turns[this.data.turns.length - 1];
    if (!last || last.state !== 'answer') return;
    const nextText = (last.text || '') + token;
    this.setData({
      turns: this.data.turns.map((t, i) =>
        i === this.data.turns.length - 1 ? { ...t, text: nextText } : t,
      ),
    });
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
   *  再退化为 reLaunch 跳 home。home tab 路径走 `getHomeTabUrl()` 配置常量，
   *  禁止硬编码 `/pages/home/index` —— FE-FIX-06 §P2 抽常量。 */
  fallbackToHomeTab() {
    const homeUrl = getHomeTabUrl();
    wx.switchTab({
      url: homeUrl,
      fail: () => {
        wx.reLaunch({ url: homeUrl });
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
          });
        }
      },
    });
  },
});
