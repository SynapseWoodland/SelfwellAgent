/**
 * SSE 阶段映射（后端 5 阶段 → 前端 8 阶段）
 * ─────────────────────────────────────────
 * 后端 SSE 真正接通后，会按 §4 推送后端 5 阶段：
 *   connected / preprocess / analyzing / suggestion / ready
 *
 * 前端 UI 沿用 8 阶段（更细的视觉推进），
 * 故在此提供别名映射；命中不到则原样返回。
 */

/** SSE 原始 stage 与 UI stage 的别名 helper（PR-A4 新增终端判断） */
const TERMINAL_UI_STAGES: ReadonlySet<UiSseStageKey> = new Set<UiSseStageKey>([
  'rendering',
  'done',
]);

/** 判断 stage 是否已经走到"出报告/结束"的视觉末端（ready/done/error） */
export function isTerminalStage(stage: string | undefined): boolean {
  if (!stage) return false;
  // 原始后端 stage 名直接判定
  if (stage === 'ready' || stage === 'done' || stage === 'error') return true;
  const ui = resolveUiStage(stage);
  return TERMINAL_UI_STAGES.has(ui);
}

export type UiSseStageKey =
  | 'upload_verify'
  | 'queued'
  | 'style_analyzing'
  | 'body_analyzing'
  | 'tag_aggregating'
  | 'suggestion'
  | 'rendering'
  | 'done';

export const UI_SSE_STAGES: ReadonlyArray<{ key: UiSseStageKey; label: string }> = [
  { key: 'upload_verify', label: '上传校验' },
  { key: 'queued', label: '排队中' },
  { key: 'style_analyzing', label: '风格分析' },
  { key: 'body_analyzing', label: '体型分析' },
  { key: 'tag_aggregating', label: '标签聚合' },
  { key: 'suggestion', label: '改善方向' },
  { key: 'rendering', label: '报告渲染' },
  { key: 'done', label: '完成' },
];

/**
 * 后端 5 阶段 → 前端 8 阶段 别名映射
 *
 * PR-A4 修订：plan §6.3 决定把后端新 5 阶段（connected/preprocess/analyzing/suggestion/ready）
 * 显式接到前端 8 阶段关键点：
 *   preprocess  → upload_verify          （图片预处理）
 *   analyzing   → body_analyzing        （覆盖 SF2 的 style_analyzing — 新版不再走风格分析）
 *   suggestion  → suggestion             （改善方向，文案一致）
 *   ready       → rendering              （报告渲染）
 *   done        → done                   （结束，原值已一致）
 *
 * 注意：analyzing → style_analyzing 的旧映射已由 analyzing → body_analyzing 取代
 *       （PR-A2 pipeline 不再发 style_analyzing）；保留前者是为了向后兼容 SF2 stub。
 */
export const BACKEND_STAGE_ALIAS: Readonly<Record<string, UiSseStageKey>> = {
  connected: 'upload_verify',
  queued: 'queued',
  // PR-A4：新映射优先于旧 style_analyzing；旧映射通过 distinct key 兼容保留
  analyzing: 'body_analyzing',
  preprocess: 'upload_verify',
  suggestion: 'suggestion',
  ready: 'rendering',
  done: 'done',
};

/** 把任意后端 stage 字符串规范成前端 8 阶段 key（命中不到则原样返回） */
export function resolveUiStage(rawStage: string | undefined): UiSseStageKey {
  if (!rawStage) return 'upload_verify';
  if (UI_SSE_STAGES.some((s) => s.key === rawStage)) return rawStage as UiSseStageKey;
  return BACKEND_STAGE_ALIAS[rawStage] ?? (rawStage as UiSseStageKey);
}