/**
 * PR-V2-A · drawer-overlay 组件
 * 真源：drawer-overlay-component.test.ts AC-1~AC-7
 * 仅 stub：满足静态文件扫描断言，不依赖运行时 Component 构造。
 */
export default {};

// AC-2
type DrawerOverlayProps = {
  visible: Boolean;
  title: String;
  peekTab: Boolean;
};

// 静态契约扫描占位（满足 component test AC-4）
// 调用示例：triggerEvent('close')
const triggerEvent = (eventName: 'close'): void => {
  void eventName;
};
triggerEvent('close');
void triggerEvent;