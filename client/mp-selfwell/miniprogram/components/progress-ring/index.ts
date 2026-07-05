/**
 * 进度环组件（首页核心 · 苹果手表风格）
 * ─────────────────────────────────────
 * 设计稿：docs/design/figma-pixso-spec/pages/03-home.html（progress-ring）
 * Token：color/primary/mint=#A8C5B5
 *
 * 属性：
 *  - percent: 0~100
 *  - size:    圆环外径（rpx），默认 240
 *  - strokeWidth: 圆环粗细（rpx），默认 16
 *  - label:   中心文字（可选，如"7/21"）
 *  - subLabel:中心副文字（可选）
 *
 * 计算：
 *  - 圆周长 C = 2πr
 *  - dashOffset = C * (1 - percent/100)
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
    size: {
      type: Number,
      value: 240,
    },
    strokeWidth: {
      type: Number,
      value: 16,
    },
    label: {
      type: String,
      value: '',
    },
    subLabel: {
      type: String,
      value: '',
    },
  },

  data: {
    radius: 100,
    circumference: 0,
    dashOffset: 0,
  },

  observers: {
    'percent, size': function (percent: number, size: number) {
      const r = size / 2 - 16; // 留出 stroke 边距
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