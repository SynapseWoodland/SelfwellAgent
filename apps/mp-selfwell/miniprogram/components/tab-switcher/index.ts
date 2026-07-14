/**
 * tab-switcher 组件（Tab 切换器）
 * ─────────────────────────────────────────────────────────
 * PR-V2-A P1.4
 * 真源：docs/design/figma-pixso-spec/pages-v2/15f-plan-tabs-5state.html
 * Token：styles/v2-tokens.wxss
 *
 * 属性：
 *  - tabs:   Array<string>，Tab 标签列表（如 ["今天", "方案", "时光"]）
 *  - active: Number，当前激活 Tab 下标
 *  - size:   "sm" | "md"，Tab 大小（默认 "md"）
 *
 * 事件：
 *  - change：切换 Tab，回调 { index, label }
 *
 * AC 来源：tab-switcher-component.test.ts AC-1~AC-5
 */
Component({
  options: {
    styleIsolation: 'apply-shared',
    multipleSlots: false,
  },

  properties: {
    tabs: {
      type: Array as WechatMiniprogram.Component.Property<string[]>,
      value: [],
    },
    active: {
      type: Number,
      value: 0,
    },
    size: {
      type: String,
      value: 'md',
    },
  },

  methods: {
    onTap(e: WechatMiniprogram.CustomEvent) {
      const target = e.currentTarget as WechatMiniprogram.Target;
      const index = Number(target.dataset.index);
      const label = (this.data.tabs as string[])[index];
      this.triggerEvent<{ index: number; label: string }>('change', {
        index,
        label,
      });
    },
  },
});
