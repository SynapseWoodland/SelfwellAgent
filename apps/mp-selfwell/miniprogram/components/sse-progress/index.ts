/**
 * SSE 进度条（诊断 / 分析中页用）
 * ─────────────────────────────
 * 设计稿：docs/design/figma-pixso-spec/pages/05-butler-analyze-loading.html
 * 后端：openapi.yaml tag=diagnosis operationId=streamDiagnosis
 *
 * 8 阶段（与后端 SPEC-M2 对齐）：
 *  1. 上传校验     upload_verify
 *  2. 排队中       queued
 *  3. 风格分析     style_analyzing
 *  4. 体型分析     body_analyzing
 *  5. 标签聚合     tag_aggregating
 *  6. 改善方向     suggestion
 *  7. 报告渲染     rendering
 *  8. 完成         done
 */
type SseStageKey =
  | 'upload_verify'
  | 'queued'
  | 'style_analyzing'
  | 'body_analyzing'
  | 'tag_aggregating'
  | 'suggestion'
  | 'rendering'
  | 'done';

interface SseStage {
  key: SseStageKey;
  label: string;
}

const STAGES: SseStage[] = [
  { key: 'upload_verify', label: '上传校验' },
  { key: 'queued', label: '排队中' },
  { key: 'style_analyzing', label: '风格分析' },
  { key: 'body_analyzing', label: '体型分析' },
  { key: 'tag_aggregating', label: '标签聚合' },
  { key: 'suggestion', label: '改善方向' },
  { key: 'rendering', label: '报告渲染' },
  { key: 'done', label: '完成' },
];

Component({
  options: {
    styleIsolation: 'apply-shared',
  },

  properties: {
    /** 当前阶段 key */
    current: {
      type: String,
      value: 'upload_verify' as SseStageKey,
    },
    /** 错误文案（红字，但用 #E8B87A 温和提示，避免禁用色栅栏） */
    errorText: {
      type: String,
      value: '',
    },
  },

  data: {
    stages: STAGES,
    currentIndex: 0,
  },

  observers: {
    current: function (current: SseStageKey) {
      const idx = STAGES.findIndex((s) => s.key === current);
      this.setData({ currentIndex: idx === -1 ? 0 : idx });
    },
  },

  methods: {},
});