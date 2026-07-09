/**
 * Selfwell 自愈 · 用户可见文案集中常量
 * ────────────────────────────────────────────────
 * 真源：
 * - backend/app/conf/assistant_copy.yaml（前后端同源）
 * - ADR-0017 Recall Safety（不评判坚持时长 / 不前后对比 / 不效果承诺）
 *
 * 约束（不可绕过）：
 * - 任何用户可见字符串不得在本文件之外硬编码
 * - 改文案改本文件（与后端 yaml 同步）
 */
import type { AssistantEntryState } from './constants';

/** 4 张入口卡的 (title, subtitle)，与 yaml ``entry_card`` 1:1 对齐。 */
export const ASSISTANT_ENTRY_CARD_COPY: Readonly<
  Record<string, Readonly<Record<AssistantEntryState, { title: string; subtitle: string }>>>
> = {
  smart_analyze: {
    not_started: { title: '智能分析', subtitle: '上传照片生成你的画像' },
    in_progress: { title: '智能分析', subtitle: '正在为你生成画像，再等一会儿' },
    completed: { title: '智能分析', subtitle: '已生成你的画像，回看一下吗' },
    inactive_7d: { title: '智能分析', subtitle: '离上次互动有点久了，先看画像吗' },
  },
  mood_diary: {
    not_started: { title: '心情日记', subtitle: '今天有什么想记录的？' },
    in_progress: { title: '心情日记', subtitle: '继续把这一段写完吧' },
    completed: { title: '心情日记', subtitle: '最近一次记录还在，可以接着记' },
    inactive_7d: { title: '心情日记', subtitle: '好久没写了，从今天重新开始' },
  },
  recall_self: {
    not_started: { title: '主动回忆', subtitle: '走过的痕迹都在，可以回看' },
    in_progress: { title: '主动回忆', subtitle: '回忆正在生成，先看看其他的' },
    completed: { title: '主动回忆', subtitle: '我们已经一起走过了，要不要回看一下' },
    inactive_7d: { title: '主动回忆', subtitle: '回看下以前的痕迹，也许有惊喜' },
  },
  direct_input: {
    not_started: { title: '直接聊聊', subtitle: '想聊什么都可以' },
    in_progress: { title: '直接聊聊', subtitle: '我在听，请继续' },
    completed: { title: '直接聊聊', subtitle: '上一次的对话还在，要继续吗' },
    inactive_7d: { title: '直接聊聊', subtitle: '什么时候回来都可以，我在' },
  },
} as const;

/** 基线问候文案（4 段位；按 last_feedback_days_ago 选取）。 */
export const BASELINE_GREETING = {
  never_recorded: {
    title: '嗨，今天想聊点什么？',
    subtitle: '从一张照片或一句心里话开始都行。',
  },
  recorded_today: {
    title: '嗨，今天我在这儿。',
    subtitle: '你刚记录过了，要是还想继续聊，我在。',
  },
  recent_within_a_week: {
    title: '嗨，又见面了。',
    subtitle: '想继续聊上次的话题，还是换个方向？',
  },
  inactive_7d_or_more: {
    title: '嗨，你回来啦。',
    subtitle: '什么时候回来都行，我在。',
  },
} as const;

/** 4 个 chips（PRD §3.5.1）。 */
export const ASSISTANT_CHIPS: ReadonlyArray<string> = [
  '智能分析',
  '今日·第 N 天',
  '聊聊今天',
  '查看对比',
] as const;

/** 顶部回忆气泡（Sprint D — Day N 触发）。 */
export const RECALL_BUBBLE_PROMPT = '我们已经一起走了 N 天，要不要看看 N 天前的自己？';

/** 回忆 soft-tip 3 按钮文案（recall-compare 空态）。 */
export const RECALL_SOFT_TIP = {
  message: '今天还没有可以回看的痕迹。',
  buttons: {
    addSet: '补一组',
    chat: '就这样聊',
    cancel: '取消',
  },
} as const;

/** 回忆对比页 day 切换 tab 文案。 */
export const RECALL_DAY_TABS: ReadonlyArray<string> = ['第 7 天', '第 14 天', '第 21 天'] as const;

/**
 * 智能管家网络/LLM 错误兜底文案（assistant-home onSend catch）
 * ───────────────────────────────────────────────────────
 * 双轨制：
 *  - isQuick=true（QUICK_REPLY 命中）：仍显示 ack（用户本来就不期待深度回答）
 *  - isQuick=false（非快问）：显式标注"管家暂时没想好…"，不假装成功
 * toast 标题两种情况共用，确保 L5 错误处理门禁"禁止静默 fallback"。
 */
export const ASSISTANT_ERROR_REPLY = {
  /** toast 标题（双轨共用） */
  toastTitle: '回复遇到点问题，请稍后再试',
  /** 非快问：bubble 文本（明确告知"没想好怎么回"，不假装成功） */
  nonQuickBubbleText: '管家暂时没想好怎么回，我再缓缓。',
  /** mock_reason audit 字段值，用于前端埋点区分 */
  mockReason: 'network_or_llm_error',
} as const;

/**
 * PR-A4：A 场景「智能分析」全链路文案（upload + loading + report 三页共用）
 * ─────────────────────────────────────────────────────────────
 * 真源：docs/design/figma-pixso-spec/pages/04a-smart-analyze-dialog.html
 *       docs/design/figma-pixso-spec/pages/05-butler-analyze-loading.html
 *       docs/design/figma-pixso-spec/pages/06-butler-analyze-report.html
 *
 * 禁止在 .wxml/.ts 中硬编码新的中文短语；改文案先改本文件。
 */
export const SMART_ANALYZE_COPY = {
  uploadTitle: '上传照片，让小愈更懂你',
  uploadHint: '可跳过部分 · 1-3 张',
  slotFace: '正面脸部',
  slotHead: '侧面体态',
  slotShoulder: '发质特写',
  submit: '开始分析',
  loadingTitle: '小愈正在分析中…',
  stages: [
    '正在识别体态状态',
    '分析面部状态',
    '生成养护建议',
    '分析完成',
  ] as const,
  reportTitle: '你的状态画像',
  start21: '开始 21 天',
  /** 「少 1 张 face」 校验提示 */
  needFace: '请先上传一张正面脸部照片',
  /** 「超出 3 张」 校验提示 */
  overThree: '最多上传 3 张照片',
  /** loading 页底部小字（用户可关闭） */
  closeHint: '可关闭',
  /** 「点击重试」按钮 */
  retry: '点击重试',
} as const;

/**
 * PR-A4：21 天方案 Tab（今日 / 全部 21 天）文案
 * ──────────────────────────────────────────────
 * 真源：docs/design/figma-pixso-spec/pages/07d-plan-tabs.html
 */
export const PLAN_TABS_COPY = {
  segToday: '今日',
  segAll: '全部 21 天',
  week1: '第一阶段 · 习惯启动',
  week2: '第二阶段 · 强化提升',
  week3: '第三阶段 · 稳定养成',
  lockHint: '坚持到这里就会解锁',
  /** 「全部视图」阶段角标 */
  todayBadge: '今天',
  doneBadge: '已完成',
  lockedBadge: '待开启',
  /** 空态文案（未生成方案） */
  noPlan: '还没有方案，先去看看智能分析？',
  generate: '去生成方案',
  /**
   * 「已走到 第 N 天」进度文案。
   * 用函数而非模板字符串，避免业务侧散落 `${...}天`。
   * 真源：docs/design/figma-pixso-spec/pages/07d-plan-tabs.html
   */
  weekProgress: (day: number): string => `已走到 第 ${day} 天`,
} as const;