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
 *   pages/checkin/index       — 今日打卡
 *   pages/assistant-home/     — 智能管家（AI 自由对话兜底；v2 后不含 chat 内嵌卡片）
 *   pages/feedback-diary      — 心情日记
 *   pages/recall-compare      — 主动回忆
 *   pages/community           — 蜕变广场
 *   pages/profile             — 我的
 *   pages/share-hug-card      — 抱抱卡
 *   pages/diagnosis-upload-v2     — v2 智能分析：3 张照片上传
 *   pages/diagnosis-loading-v2    — v2 智能分析：SSE 进度
 *   pages/diagnosis-report-v2     — v2 智能分析：报告 + 21 天 CTA
 *   pages/plan-delivery           — v2 方案交付页
 *
 * 约束：PageInstance 仅声明跨文件会被消费的最小方法集；
 *      真实实现以页面 index.ts 的 Page({...}) 为准。
 */

declare global {
  interface AppOption<TData extends Record<string, unknown>> {
    globalData: TData;
  }
}

export {};
