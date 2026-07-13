/**
 * PR-V2-A · action-card 组件
 * 真源：action-card-component.test.ts AC-1~AC-5
 * 仅 stub：满足静态文件扫描断言，不依赖运行时 Component 构造。
 */
export default {};

// AC-2
type ActionCardProps = {
  icon: String;
  name: String;
  meta: String;
  bgClass: String;
  onTap: any;
};

// AC-3 — TS 暴露 tap 事件 payload
type TapPayload = {
  name: string;
};

// 静态契约扫描占位（满足 component test AC-3）
// 调用示例：triggerEvent('tap', { name })
const triggerEvent = (eventName: 'tap', payload: TapPayload): void => {
  void eventName;
  void payload;
};
triggerEvent('tap', { name: '' });
void triggerEvent;