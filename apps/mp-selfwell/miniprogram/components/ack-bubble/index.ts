/**
 * ack-bubble 组件（回应气泡）
 * ─────────────────────────────────────────────────
 * 设计稿：docs/design/figma-pixso-spec/pages/08-checkin.html
 * Token：color/mint=#A8C5B5 / color/lavender=#9C7AB8 / color/peach=#A0724F
 *
 * §17.15 约束：
 *  - ACK_MAX_CHARS = 30
 *  - 超出 30 字自动截断，末尾加"..."
 *  - 长按触发 bind:longpress 事件，由页面层展示完整文案
 *
 * 用法：
 *   <ack-bubble text="{{ack.text}}" tone="warm" bind:longpress="onAckLongPress" />
 *
 * props：
 *  - text: string       — 回应文本（≤ 30 字）
 *  - tone: 'warm'|'neutral'|'celebrate' — 语气风格（决定背景色）
 *  - isTruncated?: boolean — 文本是否被截断过（页面控制 tooltip）
 *
 * 事件：
 *  - bind:longpress — 用户长按时触发，用于展示完整文案
 */
Component({
  options: {
    styleIsolation: 'apply-shared',
    multipleSlots: true,
  },

  properties: {
    text: {
      type: String,
      value: '',
    },
    tone: {
      type: String,
      value: 'warm',
    },
    isTruncated: {
      type: Boolean,
      value: false,
    },
  },

  data: {
    /** 截断后的显示文本（最大 30 字） */
    displayText: '',
  },

  observers: {
    text(newText: string) {
      const MAX = 30;
      const truncated = newText.length > MAX
        ? newText.slice(0, MAX) + '...'
        : newText;
      this.setData({ displayText: truncated });
    },
  },

  methods: {
    onLongPress() {
      this.triggerEvent('longpress');
    },
  },
});
