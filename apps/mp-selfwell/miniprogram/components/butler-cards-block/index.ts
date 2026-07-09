/**
 * 智能管家入口卡折叠块（SPEC-A2 V1.0 §4.2 / §4.3 / §6.1）
 * ───────────────────────────
 * 三态 FSM：expanded / collapsed / focused
 * - expanded：3 张入口卡横排（沿用 M5 视觉）+ 卡片点击事件 `cards-tap`
 * - collapsed / focused：右侧悬浮 mint 圆形 icon + 点击事件 `floating-tap`
 * - popover：floating-tap 后弹出，6s 自动收起 / 点关闭按钮 / 点外部 → `popover-close`
 *
 * 事件命名约定（native MP 强制字面匹配，不做 kebab ↔ camel 转换）：
 *  子组件 triggerEvent 与 父 wxml bind:xxx 必须**字面一字不差**。
 *  本组件触发 kebab-case 事件名（cards-tap / floating-tap / popover-close），与父级一致。
 */
type ButlerCardsMode = 'expanded' | 'collapsed' | 'focused';

interface ButlerCardItem {
  id: 'smart_analyze' | 'mood_diary' | 'recall_self';
  title: string;
  subtitle: string;
  iconBg: string;
  iconText: string;
}

Component({
  options: {
    styleIsolation: 'apply-shared',
    multipleSlots: false,
  },

  properties: {
    /** 当前 FSM 状态 */
    mode: {
      type: String,
      value: 'expanded' as ButlerCardsMode,
    },
    /** 3 张入口卡数据 */
    cards: {
      type: Array,
      value: [] as ButlerCardItem[],
    },
    /** popover 是否可见（由父组件控制，组件内不再维护 timer） */
    popoverOpen: {
      type: Boolean,
      value: false,
    },
  },

  data: {},

  methods: {
    noop() {
      /** catchtap placeholder —— 阻止冒泡到外层 onPopoverClose */
    },

    /** 点入口卡 → 透传到 page.onTapEntry
     *  事件名用 kebab-case 与父 wxml bind:cards-tap 保持字面一致（native MP bind 不会做 kebab-case ↔ camelCase 转换）。
     *  原版 triggerEvent('cardstap') + bind:cards-tap 不匹配 → 事件全部失效，控制台报"does not have a method" */
    onCardTap(e: WechatMiniprogram.BaseEvent) {
      const id = (e.currentTarget.dataset as { id: string }).id;
      this.triggerEvent('cards-tap', { id });
    },

    /** 点 floating icon → 打开 popover（父组件切状态 + 起 timer） */
    onFloatingTap() {
      this.triggerEvent('floating-tap');
    },

    /** popover 关闭按钮 / popover 外部点击 */
    onPopoverClose() {
      this.triggerEvent('popover-close');
    },
  },
});
