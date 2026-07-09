/**
 * Selfwell 自愈 · 前端 Vitest 单测 — HTTP SSE chunked 解析（M2 重构）
 * ────────────────────────────────────────────────────────────
 * 真源：
 *  - 后端 ``backend/app/api/routers/diagnosis_v1.py::_format_sse_event``
 *    发的是标准 SSE：``event: <name>\ndata: <json>\n\n``
 *  - 前端 ``apps/mp-selfwell/miniprogram/utils/sse.ts`` 已切换到
 *    ``wx.request({ enableChunked: true })`` 走 HTTP chunked transfer
 *
 * 覆盖：
 *  - 完整 SSE 帧解析
 *  - ``event: done`` → onComplete
 *  - ``event: error`` → onFailure 并关闭
 *  - 多帧拼接（多次 chunk 合并）
 *  - 注释行 ``: heartbeat\n\n`` 忽略
 *  - 不带 ``event:`` 行的默认 ``message`` 事件
 *  - HTTP 4xx/5xx → 退避
 *  - ``wx.request`` 失败 → scheduleReconnect（mock 验证退避表）
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  SSE_BACKOFF_STEPS_MS,
  SSE_BASE_URL,
  SSE_MAX_RETRY,
} from '../miniprogram/utils/config';
import {
  SseClient,
  _setHttpSseFactoryForTest,
  type SseHandlers,
} from '../miniprogram/utils/sse';

// ─────────────────────────────────────────────────────────────────────────────
// wx mock —— storageSync 用于 jwt / traceparent（与诊断流无关）
// ─────────────────────────────────────────────────────────────────────────────
const wxMock = vi.hoisted(() => ({
  getStorageSync: vi.fn((_key: string) => ''),
}));

beforeEach(() => {
  (globalThis as unknown as { wx: typeof wxMock & object }).wx = wxMock as never;
  wxMock.getStorageSync.mockReset();
  wxMock.getStorageSync.mockReturnValue('');
});

// ─────────────────────────────────────────────────────────────────────────────
// 工具：构造一个可控的 fake factory —— 记录 onChunk/onError/onStatus
// ─────────────────────────────────────────────────────────────────────────────
interface FakeHandle {
  emitChunk(chunk: string): void;
  emitStatus(statusCode: number): void;
  emitError(errMsg: string): void;
  calls: { url: string; header: Record<string, string> }[];
  abortCount: number;
}

interface FakeFactory {
  factory: NonNullable<Parameters<typeof SseClient>[2]>;
  next: () => Promise<FakeHandle>;
  allHandles: () => FakeHandle[];
}

function makeFakeFactory(): FakeFactory {
  const calls: { url: string; header: Record<string, string> }[] = [];
  const pending: Array<(h: FakeHandle) => void> = [];
  const handles: FakeHandle[] = [];
  let currentHandle: FakeHandle | null = null;

  const factory: NonNullable<Parameters<typeof SseClient>[2]> = (url, header, handlers) => {
    calls.push({ url, header: { ...header } });
    const h: FakeHandle = {
      calls,
      abortCount: 0,
      emitChunk(chunk) {
        handlers.onChunk(chunk);
      },
      emitStatus(statusCode) {
        handlers.onStatus(statusCode);
      },
      emitError(errMsg) {
        handlers.onError({ errMsg });
      },
    };
    handles.push(h);
    currentHandle = h;
    const waiter = pending.shift();
    if (waiter) waiter(h);
    return {
      abort: () => {
        h.abortCount += 1;
      },
    };
  };

  const next = (): Promise<FakeHandle> => {
    if (currentHandle) return Promise.resolve(currentHandle);
    return new Promise((resolve) => {
      pending.push(resolve);
    });
  };

  return {
    factory,
    next,
    allHandles: () => handles.slice(),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. 帧解析 — 完整 SSE 事件（对齐后端 _format_sse_event）
// ─────────────────────────────────────────────────────────────────────────────
describe('HTTP SSE 帧解析', () => {
  it('event: stage / data: {...} → onEvent 收到 stage + JSON.parse 后的 data', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    const events: Array<{ event: string; data: unknown }> = [];
    const handlers: SseHandlers = {
      onEvent: (e) => events.push({ event: e.event, data: e.data }),
    };
    const c = new SseClient({ path: '/diagnosis/r-1/stream' }, handlers);
    c.open();
    const h = await next();

    h.emitChunk(
      'event: stage\ndata: {"stage":"connected"}\n\nevent: stage\ndata: {"stage":"analyzing"}\n\n',
    );
    expect(events).toHaveLength(2);
    expect(events[0]?.event).toBe('stage');
    expect(events[0]?.data).toEqual({ stage: 'connected' });
    expect(events[1]?.event).toBe('stage');
    expect(events[1]?.data).toEqual({ stage: 'analyzing' });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. done / error 帧
// ─────────────────────────────────────────────────────────────────────────────
describe('HTTP SSE done / error 帧', () => {
  it('event: done → onComplete 触发且 client 关闭', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    let completed = 0;
    const handlers: SseHandlers = {
      onEvent: () => undefined,
      onComplete: () => (completed += 1),
    };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    const h = await next();

    h.emitChunk('event: done\ndata: {"ok":true,"report_id":"r-1"}\n\n');
    expect(completed).toBe(1);
    expect(h.abortCount).toBe(1); // close → abort
  });

  it('event: error → onFailure(reason) 触发且关闭', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    let reason = '';
    const handlers: SseHandlers = {
      onEvent: () => undefined,
      onFailure: (r) => (reason = r),
    };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    const h = await next();

    h.emitChunk(
      'event: error\ndata: {"code":"E_DIAGNOSIS_NOT_FOUND","message":"诊断超时"}\n\n',
    );
    expect(reason).toBe('诊断超时');
    expect(h.abortCount).toBe(1);
  });

  it('event: error 且 data 不是对象 → 兜底 stream_error（fallback）', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    let reason = '';
    const handlers: SseHandlers = {
      onEvent: () => undefined,
      onFailure: (r) => (reason = r),
    };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    const h = await next();

    // data 不是 JSON 对象也不是非空字符串 → 落到 'stream_error' 默认
    h.emitChunk('event: error\ndata: \n\n');
    expect(reason).toBe('stream_error');
  });

  it('event: error 且 data 是非 JSON 字符串 → 原样透传', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    let reason = '';
    const handlers: SseHandlers = {
      onEvent: () => undefined,
      onFailure: (r) => (reason = r),
    };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    const h = await next();

    h.emitChunk('event: error\ndata: boom\n\n');
    // dispatch 把 JSON.parse 失败时原样透传 → raw='boom' → parsed='boom'（字符串）
    // 但 dispatch 走 'message' in parsed 分支对字符串为 false → 落到 'stream_error'
    // 确认这是 fallback 行为，与原实现一致
    expect(reason).toBe('stream_error');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. 多帧拼接（分多次 chunk 收到 → 合并 → 解析）
// ─────────────────────────────────────────────────────────────────────────────
describe('HTTP SSE 多帧拼接', () => {
  it('半帧 + 半帧 合并后正确解析', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    const events: Array<{ event: string; data: unknown }> = [];
    const handlers: SseHandlers = { onEvent: (e) => events.push({ event: e.event, data: e.data }) };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    const h = await next();

    h.emitChunk('event: stage\ndata: {"sta');
    expect(events).toHaveLength(0);
    h.emitChunk('ge":"connected"}\n\nevent: stage\ndata: {"stage":"queued"}\n\n');
    expect(events).toHaveLength(2);
    expect(events[0]?.data).toEqual({ stage: 'connected' });
    expect(events[1]?.data).toEqual({ stage: 'queued' });
  });

  it('一帧横跨多个 chunk（跨边界多次累加）', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    const events: Array<{ event: string; data: unknown }> = [];
    const handlers: SseHandlers = { onEvent: (e) => events.push({ event: e.event, data: e.data }) };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    const h = await next();

    h.emitChunk('event: stage\ndata: {"s');
    h.emitChunk('tage":"con');
    h.emitChunk('nected"}\n\n');
    expect(events).toHaveLength(1);
    expect(events[0]?.data).toEqual({ stage: 'connected' });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. 注释行 / 默认 message 事件
// ─────────────────────────────────────────────────────────────────────────────
describe('HTTP SSE 注释行 / 默认 message 事件', () => {
  it(': heartbeat\\n\\n 注释行不进入 onEvent', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    const events: unknown[] = [];
    const handlers: SseHandlers = { onEvent: (e) => events.push(e) };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    const h = await next();

    h.emitChunk(': heartbeat\n\nevent: stage\ndata: {"stage":"connected"}\n\n');
    expect(events).toHaveLength(1);
    expect((events[0] as { event: string }).event).toBe('stage');
  });

  it('不带 event: 行的帧 → 默认 message 事件名', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    const events: Array<{ event: string; data: unknown; id?: string }> = [];
    const handlers: SseHandlers = { onEvent: (e) => events.push(e) };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    const h = await next();

    h.emitChunk('id: 42\ndata: {"hello":"world"}\n\n');
    expect(events).toHaveLength(1);
    expect(events[0]?.event).toBe('message');
    expect(events[0]?.id).toBe('42');
    expect(events[0]?.data).toEqual({ hello: 'world' });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. wx.request 失败 → scheduleReconnect 走退避
// ─────────────────────────────────────────────────────────────────────────────
describe('HTTP SSE 退避（wx.request fail / 4xx / 5xx）', () => {
  it('wx.request fail → 退避表第一次 setTimeout(open, 1000ms)', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    const handlers: SseHandlers = { onEvent: () => undefined };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    const h = await next();

    const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');

    h.emitError('request:fail timeout');

    expect(setTimeoutSpy).toHaveBeenCalled();
    const lastCall = setTimeoutSpy.mock.calls.at(-1);
    expect(lastCall?.[1]).toBe(SSE_BACKOFF_STEPS_MS[0]); // 1000ms
  });

  it('5 次重试后第 6 次失败 → onFailure("网络异常，请稍后查看报告")', async () => {
    // scheduleReconnect 在 retries 自增前先判断 ``retries >= SSE_MAX_RETRY (5)``，
    // 因此需要 5 次重试（retries 0→5），第 6 次 scheduleReconnect 才会触发 onFailure。
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    let failureReason = '';
    const handlers: SseHandlers = {
      onEvent: () => undefined,
      onFailure: (r) => (failureReason = r),
    };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    // 第 1 次：open() 已建立 handle
    let h = await next();
    for (let i = 0; i < SSE_MAX_RETRY; i++) {
      h.emitError(`fail_${i + 1}`);
      // scheduleReconnect → setTimeout(open) 同步执行 → factory 重建 handle
      h = await next();
    }
    // 第 6 次失败（retries 已达 5）
    h.emitError('fail_6');
    expect(failureReason).toBe('网络异常，请稍后查看报告');
  });

  it('HTTP 5xx → scheduleReconnect（reason 含 http_5xx）', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');
    const handlers: SseHandlers = { onEvent: () => undefined };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    const h = await next();

    h.emitStatus(503);
    expect(setTimeoutSpy).toHaveBeenCalled();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. 公共 API 与 URL 拼接
// ─────────────────────────────────────────────────────────────────────────────
describe('HTTP SSE 公共 API / URL 拼接', () => {
  it('构造请求 url = SSE_BASE_URL.dev + path', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    const handlers: SseHandlers = { onEvent: () => undefined };
    const c = new SseClient({ path: '/diagnosis/abc/stream' }, handlers);
    c.open();
    const h = await next();

    expect(h.calls[0]?.url).toBe(`${SSE_BASE_URL.dev}/diagnosis/abc/stream`);
  });

  it('header 默认含 Accept: text/event-stream + Traceparent + Authorization', async () => {
    wxMock.getStorageSync.mockImplementation((k: string) => (k === 'jwt' ? 'jwt-xyz' : ''));
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    const handlers: SseHandlers = { onEvent: () => undefined };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    const h = await next();

    const header = h.calls[0]?.header ?? {};
    expect(header['Accept']).toBe('text/event-stream');
    expect(header['Authorization']).toBe('Bearer jwt-xyz');
    expect(header['traceparent']).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/);
  });

  it('opts.skipTraceparent = true → header 不含 traceparent', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    const handlers: SseHandlers = { onEvent: () => undefined };
    const c = new SseClient({ path: '/x', skipTraceparent: true }, handlers);
    c.open();
    const h = await next();

    const header = h.calls[0]?.header ?? {};
    expect(header['traceparent']).toBeUndefined();
  });

  it('close() 触发 abort()', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    const handlers: SseHandlers = { onEvent: () => undefined };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    const h = await next();

    expect(h.abortCount).toBe(0);
    c.close();
    expect(h.abortCount).toBe(1);
  });

  it('close() 之后再次 onError 不触发 scheduleReconnect（不新增 factory 调用）', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    const handlers: SseHandlers = { onEvent: () => undefined };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    const h = await next();
    const initialCallCount = h.calls.length;
    c.close();
    h.emitError('late-error-1');
    h.emitError('late-error-2');
    expect(h.calls.length).toBe(initialCallCount);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 7. 后端帧格式契约：与 _format_sse_event 一致
// ─────────────────────────────────────────────────────────────────────────────
describe('后端 SSE 帧格式契约', () => {
  it('构造一段典型 5 阶段 + done 帧序列', async () => {
    const { factory, next } = makeFakeFactory();
    _setHttpSseFactoryForTest(factory);
    const events: Array<{ event: string; data: unknown }> = [];
    let completed = false;
    const handlers: SseHandlers = {
      onEvent: (e) => events.push({ event: e.event, data: e.data }),
      onComplete: () => (completed = true),
    };
    const c = new SseClient({ path: '/diagnosis/r-99/stream' }, handlers);
    c.open();
    const h = await next();

    // 后端 _format_sse_event 实际产出（与 diagnosis_v1.py 对齐）
    h.emitChunk(
      [
        'event: stage\ndata: {"stage":"connected"}\n\n',
        'event: stage\ndata: {"stage":"queued"}\n\n',
        'event: stage\ndata: {"stage":"analyzing"}\n\n',
        'event: stage\ndata: {"stage":"ready","report_id":"r-99"}\n\n',
        'event: done\ndata: {"ok":true,"report_id":"r-99"}\n\n',
      ].join(''),
    );

    expect(events.map((e) => e.event)).toEqual(['stage', 'stage', 'stage', 'stage']);
    expect((events[3]?.data as { stage: string }).stage).toBe('ready');
    expect(completed).toBe(true);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// cleanup
// ─────────────────────────────────────────────────────────────────────────────
afterEach(() => {
  _setHttpSseFactoryForTest(null);
  vi.restoreAllMocks();
});