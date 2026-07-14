/**
 * day-strip-5state 组件（21 天方案 day-strip · 5 态版）
 * ─────────────────────────────────────────────────────────
 * PR-V2-A P1.2
 * 真源：docs/design/figma-pixso-spec/pages-v2/15b-today-tab2.html
 * Token：styles/v2-tokens.wxss
 *
 * 属性：
 *  - days:        Array<DayItem>，21 个 day 对象
 *  - activeIndex: Number，当前高亮的格下标
 *  - compact:     Boolean，是否紧凑模式（默认 false）
 *
 * 5 态（对齐 v2-tokens.wxss）：
 *  - completed：已完成（mint 填充，白色数字）
 *  - today：    今日（白底 mint 描边 + 外发光）
 *  - missed：   漏打卡（灰色填充，弱文字）
 *  - future：   未来（白底虚线边框）
 *  - feedback： 有反馈（lavender 填充）
 *
 * 事件：
 *  - select：用户点击某格，回调 { index, day }
 *
 * AC 来源：day-strip-5state-component.test.ts AC-1~AC-6
 */
Component({
  options: {
    styleIsolation: 'apply-shared',
    multipleSlots: false,
  },

  properties: {
    /** 21 个 day 对象 */
    days: {
      type: Array,
      value: [],
    } as WechatMiniprogram.Component.Property<Array<DayItem>>,
    /** 当前高亮格下标 */
    activeIndex: {
      type: Number,
      value: -1,
    },
    /** 紧凑模式（默认 false） */
    compact: {
      type: Boolean,
      value: false,
    },
  },

  methods: {
    onSelect(e: WechatMiniprogram.CustomEvent) {
      const index = Number(
        (e.currentTarget as WechatMiniprogram.Target).dataset.index,
      );
      const day: DayItem = (this.data.days as DayItem[])[index];
      // AC-5：select 事件 payload { index: number, day: DayItem }
      this.triggerEvent<{ index: number; day: DayItem }>('select', { index, day });
    },
  },
});

/** DayItem 类型（与 home/index.ts DayStripCell 对齐） */
type DayItem = {
  dayNumber: number;
  state: 'completed' | 'today' | 'missed' | 'future' | 'feedback';
};
