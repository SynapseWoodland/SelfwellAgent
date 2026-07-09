/**
 * progress-card 组件（智能分析进度卡）
 * ────────────────────────────────────
 * 设计稿：docs/design/figma-pixso-spec/pages/05-butler-analyze-loading.html
 * 用途：在 persona-bubble 的 slot="progress-card" 中渲染渐变进度条 + 步骤列表。
 *
 * Props（与 assistant-home 的 ChatTurn.attachment.kind === 'progress_card' 1:1 对齐）：
 *  - title:    顶部标题（如"正在分析，约需 8-15 秒"）
 *  - percent:  进度百分比 0-100（取整显示）
 *  - steps:    [{label, done, current}]  3 步骤（done=✓ / current=▸ / 其它=○）
 *
 * 行为：
 *  - percent ≥ 100 时，所有 steps 视为 done
 *  - 进度条使用 mint→peach 渐变
 *  - percent 通过 Math.round 取整后展示
 *
 * Events：无（纯展示，由父组件 setData 驱动）
 */

interface ProgressStep {
  label: string;
  done: boolean;
  current: boolean;
}

Component({
  options: {
    styleIsolation: 'apply-shared',
    multipleSlots: false,
  },

  properties: {
    title: {
      type: String,
      value: '正在为你生成画像',
    },
    percent: {
      type: Number,
      value: 0,
    },
    steps: {
      type: Array,
      value: [] as ProgressStep[],
    },
  },

  data: {
    percentText: '0',
  },

  observers: {
    'percent': function (percent: number) {
      // 仅同步 percentText 到 data；steps 由父组件驱动，不要回写避免 observer 死循环
      const rounded = Math.max(0, Math.min(100, Math.round(Number(percent) || 0)));
      this.setData({ percentText: String(rounded) });
    },
  },

  methods: {},
});