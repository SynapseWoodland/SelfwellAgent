/**
 * Selfwell 自愈 · 前端 Vitest 单测 — utils/sse-http consumeSse（PR-A4 新增）
 * ────────────────────────────────────────────────────────────
 * 真源：plan §6.3「小程序 SSE 消费（微信无原生 EventSource）」
 *      apps/mp-selfwell/miniprogram/utils/sse-http.ts
 *
 * 覆盖：
 *  - 完整 event: stage / done 帧解析
 *  - 半帧 + 半帧 拼接后正确解析
 *  - 收到 done 事件触发 onTerminal 回调
 *  - 收到 error 事件触发 onTerminal 回调
 *  - 注释行 : heartbeat 忽略
 *  - cancel() 终止任务（不再派发新事件）
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { consumeSse, type SseEvent } from '../miniprogram/utils/sse-http';

// ─────────────────────────────────────────────────────────────────────────────
// wx mock —— 通过 vi.stubGlobal 注入一个全局 wx；每次测试新建一个 fake task
// ─────────────────────────────────────────────────────────────────────────────
type OnChunkCb = (res: { data: ArrayBuffer | string }) => void;

interface FakeTask {
  onChunkReceived(cb: OnChunkCb): void;
  offChunkReceived(cb: unknown): void;
  abort(): void;
  emit(chunk: string): void;
  done: { aborted: boolean; offCount: number };
}

let tasks: FakeTask[] = [];

function installWxMock(): void {
  tasks = [];
  const fakeRequest = (opts: {
    url: string;
    method: string;
    enableChunked: boolean;
    responseType: string;
    header: Record<string, string>;
    timeout?: number;
    success?: (res: unknown) => void;
    fail?: (err: { errMsg: string }) => void;
  }): FakeTask => {
    let chunkCb: OnChunkCb | null = null;
    const task: FakeTask = {
      onChunkReceived(cb) {
        chunkCb = cb;
      },
      offChunkReceived() {
        task.done.offCount += 1;
      },
      abort() {
        task.done.aborted = true;
      },
      emit(chunk: string) {
        chunkCb?.({ data: chunk });
      },
      done: { aborted: false, offCount: 0 },
    };
    tasks.push(task);
    void opts;
    return task;
  };
  (globalThis as unknown as { wx: { request: typeof fakeRequest } }).wx = {
    request: fakeRequest,
  };
}

beforeEach(() => {
  installWxMock();
});

afterEach(() => {
  // 清理
  tasks = [];
});

// helpers
async function collectEvents(
  url: string,
  opts: Parameters<typeof consumeSse>[1] = {},
): Promise<{ events: SseEvent[]; task: FakeTask }> {
  const c = consumeSse(url, opts);
  // 等一帧 microtask 让 consumeSse 内部发起 wx.request 并注册回调
  await Promise.resolve();
  const task = tasks[0];
  if (!task) throw new Error('fake wx.request 未被调用');
  const events: SseEvent[] = [];
  const iter = c.events[Symbol.asyncIterator]();
  // 启动消费协程
  const consumer = (async () => {
    while (true) {
      const next = await iter.next();
      if (next.done) break;
      events.push(next.value);
      if (next.value.name === 'done' || next.value.name === 'error') break;
    }
  })();
  // 给一个微任务等待消费协程安装好 waiter
  await Promise.resolve();
  return {
    task,
    get events() {
      return events;
    },
    finish: async () => {
      await consumer;
      return events;
    },
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. 完整 SSE 帧解析
// ─────────────────────────────────────────────────────────────────────────────
describe('consumeSse — 帧解析', () => {
  it('event: stage / data: {...} → AsyncIterable 收到 stage 事件 + JSON.parse 后的 data', async () => {
    const onTerminal = vi.fn();
    const c = consumeSse('/x', { onTerminal });
    await Promise.resolve();
    const task = tasks[0]!;
    const events: SseEvent[] = [];
    const consumer = (async () => {
      for await (const evt of c.events) {
        events.push(evt);
        if (evt.name === 'done' || evt.name === 'error') break;
      }
    })();
    await Promise.resolve();
    task.emit(
      'event: stage\ndata: {"stage":"connected"}\n\nevent: stage\ndata: {"stage":"ready","report_id":"r-1"}\n\n',
    );
    c.cancel();
    await consumer;
    expect(events).toHaveLength(2);
    expect(events[0]?.name).toBe('stage');
    expect(events[0]?.data).toEqual({ stage: 'connected' });
    expect(events[1]?.data).toEqual({ stage: 'ready', report_id: 'r-1' });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. done / error 帧终态
// ─────────────────────────────────────────────────────────────────────────────
describe('consumeSse — 终态事件', () => {
  it('event: done → onTerminal 触发一次；不再派发新事件', async () => {
    const onTerminal = vi.fn();
    const c = consumeSse('/x', { onTerminal });
    await Promise.resolve();
    const task = tasks[0]!;
    const events: SseEvent[] = [];
    const consumer = (async () => {
      for await (const evt of c.events) {
        events.push(evt);
        if (evt.name === 'done' || evt.name === 'error') break;
      }
    })();
    await Promise.resolve();
    task.emit(
      'event: stage\ndata: {"stage":"ready"}\n\nevent: done\ndata: {"report_id":"r-1"}\n\n',
    );
    await consumer;
    expect(onTerminal).toHaveBeenCalledTimes(1);
    expect(onTerminal.mock.calls[0]?.[0]?.name).toBe('done');
    expect(events.find((e) => e.name === 'done')).toBeTruthy();
    expect(task.done.aborted).toBe(true);
  });

  it('event: error → onTerminal 触发；data.message_zh 透传', async () => {
    const onTerminal = vi.fn();
    const c = consumeSse('/x', { onTerminal });
    await Promise.resolve();
    const task = tasks[0]!;
    const events: SseEvent[] = [];
    const consumer = (async () => {
      for await (const evt of c.events) {
        events.push(evt);
        if (evt.name === 'done' || evt.name === 'error') break;
      }
    })();
    await Promise.resolve();
    task.emit('event: error\ndata: {"code":"E_TIMEOUT","message_zh":"分析超时，请重试"}\n\n');
    await consumer;
    expect(onTerminal).toHaveBeenCalledTimes(1);
    expect(onTerminal.mock.calls[0]?.[0]?.name).toBe('error');
    const errEvt = events.find((e) => e.name === 'error');
    expect(errEvt?.data).toEqual({
      code: 'E_TIMEOUT',
      message_zh: '分析超时，请重试',
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. 多帧拼接（chunk 跨边界）
// ─────────────────────────────────────────────────────────────────────────────
describe('consumeSse — 多帧拼接', () => {
  it('半帧 + 半帧 合并后正确解析', async () => {
    const c = consumeSse('/x');
    await Promise.resolve();
    const task = tasks[0]!;
    const events: SseEvent[] = [];
    const consumer = (async () => {
      for await (const evt of c.events) {
        events.push(evt);
        if (evt.name === 'done' || evt.name === 'error') break;
      }
    })();
    await Promise.resolve();
    task.emit('event: stage\ndata: {"sta');
    await new Promise((r) => setTimeout(r, 5));
    task.emit('ge":"connected"}\n\nevent: done\ndata: {"report_id":"r-1"}\n\n');
    await consumer;
    expect(events.find((e) => e.name === 'stage')?.data).toEqual({ stage: 'connected' });
    expect(events.find((e) => e.name === 'done')).toBeTruthy();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. 注释行
// ─────────────────────────────────────────────────────────────────────────────
describe('consumeSse — 注释行', () => {
  it(': heartbeat\\n\\n 不派发 stage 事件', async () => {
    const c = consumeSse('/x');
    await Promise.resolve();
    const task = tasks[0]!;
    const events: SseEvent[] = [];
    const consumer = (async () => {
      for await (const evt of c.events) {
        events.push(evt);
        if (evt.name === 'done' || evt.name === 'error') break;
      }
    })();
    await Promise.resolve();
    task.emit(': heartbeat\n\nevent: stage\ndata: {"stage":"queued"}\n\n');
    task.emit('event: done\ndata: {"report_id":"x"}\n\n');
    await consumer;
    expect(events.filter((e) => e.name === 'stage')).toHaveLength(1);
    expect(events.find((e) => e.name === 'done')).toBeTruthy();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. cancel
// ─────────────────────────────────────────────────────────────────────────────
describe('consumeSse — cancel', () => {
  it('cancel() 终止 task；后续 chunk 不再派发新事件', async () => {
    const c = consumeSse('/x');
    await Promise.resolve();
    const task = tasks[0]!;
    const events: SseEvent[] = [];
    const consumer = (async () => {
      for await (const evt of c.events) {
        events.push(evt);
        if (evt.name === 'done' || evt.name === 'error') break;
      }
    })();
    await Promise.resolve();
    task.emit('event: stage\ndata: {"stage":"connected"}\n\n');
    // 等消费侧拉走
    await new Promise((r) => setTimeout(r, 5));
    c.cancel();
    expect(task.done.aborted).toBe(true);
    await consumer;
    expect(events.find((e) => e.name === 'stage')?.data).toEqual({ stage: 'connected' });
  });
});

// Reference to unused-helper function (consumeEvents future use)
void collectEvents;
