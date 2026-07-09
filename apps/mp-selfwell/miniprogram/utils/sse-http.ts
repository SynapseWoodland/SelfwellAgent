/**
 * Selfwell · SSE chunked-HTTP 消费者（PR-A4）
 * ────────────────────────────────────────
 * 真源：plan §6.3「小程序 SSE 消费（微信无原生 EventSource）」
 *       backend/app/api/routers/diagnosis_v1.py::event_stream_for_job
 *
 * 协议：text/event-stream，每个 event 以 ``\n\n`` 分隔：
 *     event: <name>\n
 *     data: <json>\n
 *     \n
 *
 * 实现：
 *  - 走 ``wx.request({ enableChunked: true, responseType: 'text/plain' })``
 *  - 通过 ``onChunkReceived(res)`` 增量接收 → 字符串 → 拼到 buffer
 *  - 按 ``\n\n`` 切分；每段按 SSE 规范解析（event: / id: / data: 字段，注释行 :... 忽略）
 *  - 收齐一帧后通过 AsyncIterable yield SseEvent
 *  - 收到 event:done 或 event:error 时，自动 cancel + 调 onTerminal 回调
 *
 * 兼容性：
 *  - 微信基础库 ≥ 2.21.0 才暴露 enableChunked/onChunkReceived；低版本会由 ``fail`` 路径走 NETWORK_ERROR，本 PR 不实现轮询降级
 *  - 不引入任何 npm 依赖
 */

import type { SseEventName } from '../types/api';
import { dlog } from './dlog';

/** 单条已解析事件 */
export interface SseEvent {
  name: SseEventName;
  data: unknown;
}

/** 消费者句柄 */
export interface SseConsumer {
  events: AsyncIterable<SseEvent>;
  cancel: () => void;
}

/** consumeSse 选项 */
export interface ConsumeSseOptions {
  /** 自定义 header（与默认 Accept 合并，传入的同名字段会覆盖默认） */
  header?: Record<string, string>;
  /** 收到终态事件（done / error）回调；调用方用于停止 UI spinner */
  onTerminal?: (evt: SseEvent) => void;
  /** 自定义超时（ms），控制连接建立超时 */
  timeoutMs?: number;
  /** HTTP 方法（默认 GET；assistant 流式端点是 POST） */
  method?: 'GET' | 'POST';
  /** POST body（JSON 字符串或对象；undefined 时按 GET 处理） */
  body?: string | Record<string, unknown>;
}

/** 微信原生 ``wx.request`` 在 enableChunked 下返回的最小 task 形状 */
interface WxChunkedTask {
  abort(): void;
  onChunkReceived(cb: (res: { data: ArrayBuffer | string }) => void): void;
  offChunkReceived(cb: (res: { data: ArrayBuffer | string }) => void): void;
}

/** 单消费者事件分发器：push 事件 → 把 evt 直接传给第一个 waiter，或放入 queue */
function createEventDispatcher() {
  const queue: SseEvent[] = [];
  /** waiter 接收 evt；null 表示 close 信号 */
  const waiters: Array<(evt: SseEvent | null) => void> = [];
  let closed = false;

  function push(evt: SseEvent): void {
    if (closed) return;
    if (waiters.length > 0) {
      const waiter = waiters.shift()!;
      waiter(evt);
      return;
    }
    queue.push(evt);
  }

  function next(): IteratorResult<SseEvent> | Promise<IteratorResult<SseEvent>> {
    if (closed && queue.length === 0) {
      return { value: undefined as unknown as SseEvent, done: true };
    }
    if (queue.length > 0) {
      const evt = queue.shift()!;
      return { value: evt, done: false };
    }
    return new Promise<IteratorResult<SseEvent>>((resolve) => {
      waiters.push((evt) => {
        if (evt === null) {
          resolve({ value: undefined as unknown as SseEvent, done: true });
        } else {
          resolve({ value: evt, done: false });
        }
      });
    });
  }

  function close(): void {
    closed = true;
    while (waiters.length > 0) {
      const waiter = waiters.shift()!;
      waiter(null);
    }
  }

  return { push, next, close };
}

/** 解析单帧 SSE 文本 */
function parseFrame(frame: string): SseEvent | null {
  if (!frame) return null;
  let event = '';
  const dataLines: string[] = [];
  for (const rawLine of frame.split('\n')) {
    const line = rawLine.replace(/\r$/, '');
    if (!line || line.startsWith(':')) continue;
    const colon = line.indexOf(':');
    const field = colon === -1 ? line : line.slice(0, colon);
    const value = colon === -1 ? '' : line.slice(colon + 1).replace(/^ /, '');
    if (field === 'event') event = value;
    else if (field === 'data') dataLines.push(value);
  }
  if (!dataLines.length || !event) return null;
  const raw = dataLines.join('\n');
  let parsed: unknown = raw;
  try {
    parsed = JSON.parse(raw);
  } catch {
    /* 非 JSON 原样透传 */
  }
  return { name: event as SseEventName, data: parsed };
}

/**
 * 消费 ``text/event-stream``；返回 ``AsyncIterable<SseEvent>`` + cancel。
 *
 * @example
 *   const c = consumeSse('/api/v1/diagnosis/jobs/abc/stream', {
 *     onTerminal: (evt) => console.log('done/error', evt.name),
 *   });
 *   for await (const evt of c.events) {
 *     if (evt.name === 'stage') { ... }
 *   }
 */
export function consumeSse(
  url: string,
  opts: ConsumeSseOptions = {},
): SseConsumer {
  const dispatcher = createEventDispatcher();

  const buffer: { value: string } = { value: '' };
  let task: WxChunkedTask | null = null;

  function feed(chunk: string): void {
    buffer.value += chunk;
    let idx = buffer.value.indexOf('\n\n');
    while (idx !== -1) {
      const frame = buffer.value.slice(0, idx);
      buffer.value = buffer.value.slice(idx + 2);
      const evt = parseFrame(frame);
      if (evt) dispatchEvent(evt);
      idx = buffer.value.indexOf('\n\n');
    }
  }

  function dispatchEvent(evt: SseEvent): void {
    if (evt.name === 'done' || evt.name === 'error') {
      dispatcher.push(evt);
      opts.onTerminal?.(evt);
      cleanup();
      return;
    }
    dispatcher.push(evt);
  }

  function onChunk(res: { data: ArrayBuffer | string }): void {
    let chunk = '';
    if (typeof res.data === 'string') {
      chunk = res.data;
    } else if (res.data instanceof ArrayBuffer) {
      chunk = new TextDecoder('utf-8').decode(new Uint8Array(res.data));
    } else if (res.data) {
      chunk = String(res.data);
    }
    if (chunk) feed(chunk);
  }

  function cleanup(): void {
    if (task) {
      try {
        task.offChunkReceived(onChunk);
        task.abort();
      } catch {
        /* ignore */
      }
      task = null;
    }
    dispatcher.close();
  }

  const header: Record<string, string> = {
    Accept: 'text/event-stream',
    ...(opts.header ?? {}),
  };

  // 启动 wx.request（提供最小类型确保编译通过）
  const wxRequest = (wx as unknown as {
    request: (o: {
      url: string;
      method: string;
      enableChunked: true;
      responseType: 'text/plain';
      header: Record<string, string>;
      data?: string;
      timeout?: number;
      success?: (res: unknown) => void;
      fail?: (err: { errMsg: string }) => void;
    }) => WxChunkedTask;
  }).request;

  const httpMethod = opts.method ?? 'GET';
  const bodyData =
    httpMethod === 'POST' && opts.body !== undefined
      ? typeof opts.body === 'string' ? opts.body : JSON.stringify(opts.body)
      : undefined;
  // POST + JSON body 时显式声明 Content-Type（后端 Pydantic 强依赖 application/json）
  if (httpMethod === 'POST' && bodyData && !('Content-Type' in header)) {
    header['Content-Type'] = 'application/json';
  }

  try {
    task = wxRequest({
      url,
      method: httpMethod,
      enableChunked: true,
      responseType: 'text/plain',
      header,
      ...(bodyData ? { data: bodyData } : {}),
      timeout: opts.timeoutMs,
      success: (res: unknown) => {
        // #region agent log
        const status = (res as { statusCode?: number; status?: number } | undefined)?.statusCode
          ?? (res as { status?: number } | undefined)?.status;
        dlog('sse-http.ts:wxRequest.success', 'wx.request success', { url, method: httpMethod, status, resKeys: res && typeof res === 'object' ? Object.keys(res) : null });
        // #endregion
        /* chunked success 在流关闭时触发；done/error 已独立处理 */
      },
      fail: (err) => {
        // #region agent log
        dlog('sse-http.ts:wxRequest.fail', 'wx.request fail', { url, method: httpMethod, errMsg: err?.errMsg, errKeys: err && typeof err === 'object' ? Object.keys(err) : null });
        // #endregion
        if (err === undefined) return;
        const errEvt: SseEvent = {
          name: 'error',
          data: { code: 'NETWORK_ERROR', message_zh: err.errMsg ?? '网络异常' },
        };
        dispatcher.push(errEvt);
        opts.onTerminal?.(errEvt);
        cleanup();
      },
    });
    task.onChunkReceived(onChunk);
  } catch (e) {
    // 微信基础库 < 2.21 或 enableChunked 不存在 → 同步抛错
    const errEvt: SseEvent = {
      name: 'error',
      data: {
        code: 'CHUNKED_UNSUPPORTED',
        message_zh: e instanceof Error ? e.message : '当前微信版本不支持 SSE',
      },
    };
    queueMicrotask(() => {
      dispatcher.push(errEvt);
      opts.onTerminal?.(errEvt);
      dispatcher.close();
    });
  }

  const iterable: AsyncIterable<SseEvent> = {
    [Symbol.asyncIterator]() {
      return {
        next: () => Promise.resolve(dispatcher.next() as IteratorResult<SseEvent>),
      };
    },
  };

  return {
    events: iterable,
    cancel: cleanup,
  };
}
