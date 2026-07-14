/**
 * progress-ring 组件（苹果手表风格）
 * ─────────────────────────────────────────────────────────
 * PR-V2-A P1.1
 * 设计稿：docs/design/figma-pixso-spec/pages-v2/15b-today-tab2.html
 *
 * 属性（V2 支持 3 档 px 尺寸）：
 *  - size:    圆环外径（px），默认 90。选项：60 / 90 / 160
 *  - percent: 0~100，完成度
 *  - label:   中心主文字（如 "33%" / "7/21"）
 *  - subLabel:中心副文字（如 "今日完成" / "已坚持 3 天"）
 *  - variant: "ring"（SVG stroke）或 "gradient"（conic-gradient）
 *             默认 "ring"。15b 今天 Tab 用 "gradient" 风格
 *
 * Token（styles/v2-tokens.wxss）：
 *  --ring-size-sm: 60px
 *  --ring-size-md: 90px
 *  --ring-size-lg: 160px
 *  --ring-stroke: 6px
 *  --ring-stroke-lg: 8px
 *  --ring-fg: #A8C5B5
 *  --ring-bg: #E2E8F0
 *
 * AC 来源：progress-ring-component.test.ts
 */
Component({
  options: {
    styleIsolation: 'apply-shared',
    multipleSlots: false,
  },

  properties: {
    percent: {
      type: Number,
      value: 0,
    },
    /** 外径（px）。60 / 90 / 160 三档。 */
    size: {
      type: Number,
      value: 90,
    },
    strokeWidth: {
      type: Number,
      value: 6,
    },
    label: {
      type: String,
      value: '',
    },
    subLabel: {
      type: String,
      value: '',
    },
    /** "ring"（SVG stroke）或 "gradient"（conic-gradient） */
    variant: {
      type: String,
      value: 'ring',
    },
  },

  data: {
    radius: 39,
    circumference: 0,
    dashOffset: 0,
  },

  observers: {
    'percent, size, strokeWidth': function (
      percent: number,
      size: number,
      strokeWidth: number,
    ) {
      const r = size / 2 - strokeWidth;
      const c = 2 * Math.PI * r;
      const safe = Math.max(0, Math.min(100, Number(percent) || 0));
      this.setData({
        radius: r,
        circumference: c,
        dashOffset: c * (1 - safe / 100),
      });
    },
  },

  methods: {},
});
