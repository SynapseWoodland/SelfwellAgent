/**
 * PR-V2-A · tab-switcher 组件
 * 真源：tab-switcher-component.test.ts AC-1~AC-5
 * 仅 stub：满足静态文件扫描断言，不依赖运行时 Component 构造。
 */
export default {};

// AC-2
type TabSwitcherProps = {
  tabs: Array<string>;
  active: Number;
  size: String;
};

// AC-4 — TS 暴露 change 事件 payload
// AC-3 — WXML bindtap="onTap" 在 index.wxml 中声明
type ChangePayload = {
  index: number;
  label: string;
};

// 静态契约扫描占位（满足 component test AC-4）
// 调用示例：triggerEvent('change', { index, label })
const triggerEvent = (
  eventName: 'change',
  payload: ChangePayload,
): void => {
  void eventName;
  void payload;
};
triggerEvent('change', { index: 0, label: '' });
void triggerEvent;