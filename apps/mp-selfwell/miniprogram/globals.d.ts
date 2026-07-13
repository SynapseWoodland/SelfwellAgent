// ──────────────────────────────────────────────────────────────
// globals.d.ts — Selfwell 自愈 · 微信小程序 全局类型声明
// ──────────────────────────────────────────────────────────────
// 真源：plans/v2-unified-parent.md §1 PR-3 commit-1（UI 重制保留 SSE 双模式）
// 用途：为 miniprogram 下的 *.ts 提供 wx / Page / WechatMiniprogram / getApp / Component
//      的全局类型，避免每个 page / component 文件顶部重复 declare。
//
// 历史遗留：PR-A4 时代每个 page 文件都写
//   declare const wx: any;
//   declare function Page(config: any): void;
// 重复且掩盖真实类型。F1 修复后统一在 globals.d.ts 声明，page 文件不再写。
// ──────────────────────────────────────────────────────────────

declare const wx: any;
declare const getApp: any;

declare function Page<T = Record<string, unknown>>(config: any): void;
declare function Component<T = Record<string, unknown>>(config: any): void;

declare namespace WechatMiniprogram {
  interface BaseEvent {
    currentTarget: {
      dataset: Record<string, unknown>;
      dataset?: Record<string, unknown>;
    };
    target: {
      dataset?: Record<string, unknown>;
    };
  }

  interface CustomEvent<T = unknown> {
    detail: T;
  }
}