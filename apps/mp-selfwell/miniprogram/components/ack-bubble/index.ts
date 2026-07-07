/**
 * ACK 气泡（30 字截断，§17.15 强约束）
 * ─────────────────────────────────────
 * 设计稿：docs/design/figma-pixso-spec/pages/08-butler-diary.html
 * 数据源：docs/data/ack-pool.yaml
 *
 * 约束：
 *  - 显示字数 ≤ ACK_MAX_CHARS（30），超出用 "…" 截断
 *  - hover/longpress 时显示完整原文（用 wx.showToast / tooltip 替代，避免换行错觉）
 *  - 类型：warm / neutral / celebrate 三档（避免焦虑色）
 */
import { ACK_MAX_CHARS } from '../../utils/config';

type AckTone = 'warm' | 'neutral' | 'celebrate';

Component({
  options: {
    styleIsolation: 'apply-shared',
  },

  properties: {
    /** 完整 ACK 文案（来自 ack-pool.yaml） */
    text: {
      type: String,
      value: '',
    },
    /** 视觉风格 */
    tone: {
      type: String,
      value: 'warm' as AckTone,
    },
    /** 是否显示完整（默认 false，截断到 30 字） */
    showFull: {
      type: Boolean,
      value: false,
    },
  },

  data: {
    truncated: '',
    isTruncated: false,
  },

  observers: {
    'text, showFull': function (text: string, showFull: boolean) {
      const t = (text ?? '').toString();
      const isTruncated = !showFull && t.length > ACK_MAX_CHARS;
      this.setData({
        truncated: isTruncated ? t.slice(0, ACK_MAX_CHARS) + '…' : t,
        isTruncated,
      });
    },
  },

  methods: {
    onLongPress() {
      if (!this.data.isTruncated) return;
      wx.showToast({
        title: this.data.text,
        icon: 'none',
        duration: 4000,
      });
    },
  },
});