/**
 * 错误浮层（业务错误统一出口）
 * ────────────────────────────
 * 设计稿：全局公共组件（无对应设计稿）
 *
 * 三档：info / warn / error
 * 颜色：mint / warning(#E8B87A) / peach；显式不使用禁用色栅栏（详见 app.wxss）
 */
type ErrorKind = 'info' | 'warn' | 'error';

Component({
  options: {
    styleIsolation: 'apply-shared',
  },

  properties: {
    visible: {
      type: Boolean,
      value: false,
    },
    text: {
      type: String,
      value: '',
    },
    kind: {
      type: String,
      value: 'info' as ErrorKind,
    },
    duration: {
      type: Number,
      value: 2400,
    },
  },

  observers: {
    visible: function (visible: boolean) {
      if (visible) {
        wx.showToast({
          title: this.data.text || ' ',
          icon: 'none',
          duration: this.data.duration,
        });
        this.triggerEvent('shown', {});
      }
    },
  },

  data: {},

  methods: {
    dismiss() {
      this.triggerEvent('dismiss', {});
    },
  },
});