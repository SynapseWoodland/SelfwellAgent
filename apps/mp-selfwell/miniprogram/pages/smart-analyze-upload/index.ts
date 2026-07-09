/**
 * smart-analyze-upload —— 占位页
 *
 * 设计意图（PR-A4）：
 *   原计划独立 3 槽位上传页；真实落地改为 assistant-home 对话气泡内嵌卡片
 *   （见 assistant-home/index.ts `startSmartAnalyze`），本目录不再注册到 app.json。
 *
 * 保留目的：
 *   - 兜底 `assistant_home_entry_pr_a4.test.ts` 中 `wx.navigateTo` 的目标路径
 *   - 兜底 DevTools 历史编译缓存里残留的 wxml 扫描引用
 *
 * data 字段全部用空/默认值兜底，不引入任何业务逻辑，避免与未来 PR 冲突。
 */

interface PageData {
  /** 顶部提示文本（占位） */
  placeholderTitle: string;
}

Page<PageData>({
  data: {
    placeholderTitle: '智能分析上传',
  },

  onLoad() {
    // 占位页：不做任何业务，仅确保可被 wx.navigateTo 安全打开。
  },
});
