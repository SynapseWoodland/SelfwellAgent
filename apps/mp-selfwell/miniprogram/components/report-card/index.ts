/**
 * report-card 组件（智能分析报告卡）
 * ────────────────────────────────────
 * 设计稿：docs/design/figma-pixso-spec/pages/06-butler-analyze-report.html
 * 用途：在 persona-bubble 的 slot="report-card" 中渲染头像 + N 条改善方向 + 21 天 CTA。
 *
 * Props（与 assistant-home 的 ChatTurn.attachment.kind === 'report_card' 1:1 对齐）：
 *  - avatarText: 头像占位文字（单字，如"满"）
 *  - name:       用户昵称
 *  - directions: [{num, title, level, description}]  改善方向列表
 *  - ctaText:    CTA 按钮文案（可选，默认"开始 21 天"）
 *
 * Events（冒号命名，父组件直接 bind）：
 *  - ctaTap    点击底部"开始 21 天"按钮（父组件负责 wx.navigateTo）
 */

interface Direction {
  num: number;
  title: string;
  level: string;
  description: string;
}

Component({
  options: {
    styleIsolation: 'apply-shared',
    multipleSlots: false,
  },

  properties: {
    avatarText: {
      type: String,
      value: '你',
    },
    name: {
      type: String,
      value: '你',
    },
    directions: {
      type: Array,
      value: [] as Direction[],
    },
    ctaText: {
      type: String,
      value: '',
    },
  },

  data: {},

  methods: {
    onCtaTap() {
      this.triggerEvent('ctaTap', {}, { bubbles: true, composed: true });
    },
  },
});