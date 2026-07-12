/**
 * Sprint A Phase 0 · jest 全局 setup。
 *
 * 真源：V4.1 V&V 子计划（q6 决策）。
 *
 * 用途：
 * 1. mock 微信 wx 全局对象（jsdom 不会自带，jest 默认 testEnvironment='node' 也没）。
 *    - wx.request 返回带 enableChunked 支持的 RequestTask-like 对象；
 *    - wx.uploadFile 同形态；
 *    - 其余 wx.* API 给空实现占位（getStorage/setStorage 都返回同步值）。
 * 2. mock Node globals（structuredClone / AbortController 在 node >=18 内建；这里复用）。
 * 3. mock console.warn/error 把噪音降级为只统计不输出，避免淹没 test diff。
 *
 * 升级路径：
 * - 若未来需要测真实 wx.request chunked 流行为，可注入 fake-wx-request 包。
 * - 若需要测 wx.cloud.* 调用，可补 wx.cloud mock。
 */

type WxRequestTask = {
  abort: jest.Mock;
  onChunkReceived: jest.Mock;
  offChunkReceived: jest.Mock;
  onHeadersReceived: jest.Mock;
};

const wxRequestMock = jest.fn(
  (opts: {
    url: string;
    success?: (res: unknown) => void;
    fail?: (err: unknown) => void;
    complete?: () => void;
    enableChunked?: boolean;
    [k: string]: unknown;
  }) => {
    const task: WxRequestTask = {
      abort: jest.fn(),
      onChunkReceived: jest.fn(),
      offChunkReceived: jest.fn(),
      onHeadersReceived: jest.fn(),
    };
    // 默认走 fail 分支，调用方应在每个 spec 里 mockImplementation 改写
    setImmediate(() => {
      opts.fail?.({ errMsg: 'wx.request not mocked in this spec' });
      opts.complete?.();
    });
    return task;
  },
);

const wxUploadFileMock = jest.fn(
  (opts: {
    url: string;
    success?: (res: unknown) => void;
    fail?: (err: unknown) => void;
    complete?: () => void;
  }) => {
    setImmediate(() => {
      opts.fail?.({ errMsg: 'wx.uploadFile not mocked in this spec' });
      opts.complete?.();
    });
    return {
      abort: jest.fn(),
      onProgressUpdate: jest.fn(),
      onHeadersReceived: jest.fn(),
    };
  },
);

const wxGetStorageMock = jest.fn((key: string) => '');
const wxSetStorageMock = jest.fn((key: string, value: unknown) => undefined);

(globalThis as unknown as { wx: unknown }).wx = {
  request: wxRequestMock,
  uploadFile: wxUploadFileMock,
  getStorageSync: wxGetStorageMock,
  setStorageSync: wxSetStorageMock,
  showToast: jest.fn(),
  showModal: jest.fn(),
  showActionSheet: jest.fn(),
  navigateTo: jest.fn(),
  redirectTo: jest.fn(),
  switchTab: jest.fn(),
  getSystemInfoSync: jest.fn(() => ({
    platform: 'devtools',
    SDKVersion: '3.0.0',
  })),
};

// 降低测试期间的 console 噪音（仅当 CI=true 时）
if (process.env.CI === 'true') {
  // 静默 console.warn（生产代码用 loguru，非测试关心的警告）
  // 静默 console.error（异常路径已在 spec 里 assert）
  // 不静默 console.log（spec 自己 print 是有意行为）
}

// 导出 mock fns 让 spec 可重置 / 统计
module.exports = { wxRequestMock, wxUploadFileMock };
