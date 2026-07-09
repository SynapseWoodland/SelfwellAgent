/**
 * Selfwell 自愈 · 微信小程序 PageInstance 类型声明
 * ──────────────────────────────────────────
 * 真源：每个页面的 index.ts(Page({})) 与自动派生的 PageInstance 接口。
 * 本文件仅放跨页面共享、未来 PR 需要引用的接口。
 *
 * - app.json 已注册页面一览（按目录）：
 *   pages/splash/index        — 启动页
 *   pages/login/index         — 登录
 *   pages/home/index          — 首页（今日打卡）
 *   pages/diagnosis-upload    — SF2 旧版（M2 100% 落地时使用）
 *   pages/diagnosis-loading   — SF2 旧版
 *   pages/diagnosis-report    — SF2 旧版
 *   pages/plan/index          — 旧方案页
 *   pages/checkin/index       — 今日打卡
 *   pages/assistant-home/     — 智能管家（4 态对话）
 *   pages/feedback-diary      — 心情日记
 *   pages/recall-compare      — 主动回忆
 *   pages/community           — 蜕变广场
 *   pages/profile             — 我的
 *   pages/share-hug-card      — 抱抱卡
 *   pages/smart-analyze-upload    — 【PR-A4】A 场景 3 槽位上传
 *   pages/smart-analyze-loading   — 【PR-A4】A 场景 SSE 进度
 *   pages/smart-analyze-report    — 【PR-A4】A 场景 报告 + 21 天 CTA
 *   pages/plan-tabs           — 【PR-A4】21 天方案 Tab（今日/全部）
 *
 * 约束：PageInstance 仅声明跨文件会被消费的最小方法集；
 *      真实实现以页面 index.ts 的 Page({...}) 为准。
 */

declare global {
  interface AppOption<TData extends Record<string, unknown>> {
    globalData: TData;
  }

  // ────────────────────────────────────────────────────────────────
  // PR-A4 新页面 PageInstance —— 给后续 PR 集成测试 / 静态分析使用
  // ────────────────────────────────────────────────────────────────

  /** pages/smart-analyze-upload/index.ts —— 3 槽位上传页 */
  interface PageSmartAnalyzeUpload {
    /** 用户选择图片后填充某槽位 */
    onPickImage: (slotIdx: number) => void;
    /** 切换某槽位 body_part（face / head / shoulder_neck） */
    onSelectBodyPart: (slotIdx: number, part: 'face' | 'head' | 'shoulder_neck') => void;
    /** 移除某槽位已选图片 */
    onRemoveSlot: (slotIdx: number) => void;
    /** 点击「开始分析」 → POST /diagnosis?async=true → jumpToLoading */
    onSubmitAnalysis: () => Promise<void>;
    /** 校验生效后跳转 loading 页 */
    submitAnalysis: () => void;
  }

  /** pages/smart-analyze-loading/index.ts —— SSE 进度页 */
  interface PageSmartAnalyzeLoading {
    /** 收到 SSE stage 事件 → 更新 data.stages / data.percent */
    onSseStage: (payload: import('./types/api').SseStagePayload) => void;
    /** 收到 SSE done 事件 → redirectTo report */
    onSseDone: (payload: import('./types/api').SseDonePayload) => void;
    /** 收到 SSE error 事件 → toast + 重试入口 */
    onSseError: (payload: import('./types/api').SseErrorPayload) => void;
  }

  /** pages/smart-analyze-report/index.ts —— 报告 + CTA */
  interface PageSmartAnalyzeReport {
    /** GET /diagnosis/{report_id} 渲染完成 */
    onReportLoaded: (report: import('./types/api').DiagnosisReport) => void;
    /** 「开始 21 天」点击 → POST /plans/generate → switchTab home */
    onStartPlan: () => Promise<void>;
  }

  /** pages/plan-tabs/index.ts —— 21 天方案 Tab */
  interface PagePlanTabs {
    /** GET /plans/current?view=... 数据返回 → 渲染 */
    onPlanLoaded: (
      data:
        | import('./types/api').PlanAllViewData
        | { current_day_index: number; plan_id: string; view: 'today' },
    ) => void;
    /** GET /plans/today?day=N 返回 → 详情 */
    onDayLoaded: (dayData: import('./types/api').TodayPlan) => void;
  }
}

export {};
