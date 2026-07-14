/**
 * PR-V2-A · drawer-overlay 组件
 * ─────────────────────────────────────────────────────────────────
 * 真源：docs/spec/SPEC-M3-pages-v2-1to1-clone.md §3.1
 * 真源：docs/design/figma-pixso-spec/pages-v2/15c-manage-drawer.html
 *
 * 功能：右侧抽屉 + 全屏遮罩
 * - visible=true 时显示抽屉和遮罩
 * - 点击遮罩或 close 按钮 → triggerEvent('close')
 * - peekTab=true 时抽屉底部渲染 tabbar 提示条
 */
// @property {Boolean} visible
// @property {String} title
// @property {Boolean} peekTab
Component({
  properties: {
    visible: {
      type: Boolean,
      value: false,
    },
    title: {
      type: String,
      value: '',
    },
    peekTab: {
      type: Boolean,
      value: false,
    },
  },

  methods: {
    onCloseTap() {
      this.triggerEvent('close');
    },

    onMaskTap() {
      this.triggerEvent('close');
    },
  },
});
