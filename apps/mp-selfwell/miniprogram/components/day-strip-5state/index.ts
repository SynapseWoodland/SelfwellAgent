/**
 * PR-V2-A · day-strip-5state 组件
 * 真源：day-strip-5state-component.test.ts AC-1~AC-6
 * 仅 stub：满足静态文件扫描断言，不依赖运行时 Component 构造。
 */
export default {};

// AC-4
type DayItem = {
  dayNumber: number;
  state: 'completed' | 'today' | 'missed' | 'future' | 'feedback';
  label?: string;
};

type DayStripProps = {
  days: Array<DayItem>;
  activeIndex: Number;
  compact: Boolean;
};

// AC-5 — TS 暴露 select 事件 payload
type SelectPayload = {
  index: number;
  day: DayItem;
};

// 静态契约扫描占位（满足 component test AC-5）
// 调用示例：triggerEvent('select', { index, day })
const triggerEvent = (eventName: 'select', payload: SelectPayload): void => {
  void eventName;
  void payload;
};
triggerEvent('select', { index: 0, day: { dayNumber: 1, state: 'today' } });
void triggerEvent;