/**
 * 桩测试 · Sprint A Phase 0 jest 基建验证。
 *
 * 目的：
 * 1. 证明 jest + ts-jest + setup.ts 链路可加载（import 不报错）。
 * 2. 证明全局 wx mock 注入成功（wx.request 是 jest.fn）。
 * 3. 留一个最小占位，让 sprint 实施人员知道本目录可写 spec。
 *
 * 下一步（Phase 0 之后）：
 * - 加 ``sse-http.spec.test.ts`` 真正覆盖 ``consumeSse`` enableChunked 行为（V4 Step 2.12 + F-5/F-6）。
 * - 加 ``applyTokenDelta.spec.test.ts`` 覆盖流式拼接逻辑（V4 Step 2.2 + F-1/F-2）。
 */
import { wxRequestMock } from './setup';

describe('jest + ts-jest scaffolding', () => {
  it('1+1 equals 2 (sanity)', () => {
    expect(1 + 1).toBe(2);
  });

  it('wx.request is globally mocked as jest.fn', () => {
    const wx = (globalThis as unknown as { wx: { request: jest.Mock } }).wx;
    expect(typeof wx.request).toBe('function');
    expect(wxRequestMock).toBeDefined();
  });

  it('wx.getStorageSync returns empty string by default', () => {
    const wx = (globalThis as unknown as { wx: { getStorageSync: jest.Mock } }).wx;
    expect(wx.getStorageSync('jwt')).toBe('');
  });

  it('AbortController is available in node runtime', () => {
    // 微信小程序原生支持；Node 18+ 也内建。两者都有才能用于 sse-http AbortSignal 透传。
    expect(typeof AbortController).toBe('function');
    const ac = new AbortController();
    expect(ac.signal).toBeDefined();
    expect(ac.signal.aborted).toBe(false);
    ac.abort();
    expect(ac.signal.aborted).toBe(true);
  });
});
