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

/**
 * ArrayBuffer → string 转换
 * - 微信小程序 iOS 客户端不支持 TextDecoder，需自实现 UTF-8 解码
 * - 小程序基础库 ≥ 2.19.0 提供 ArrayBuffer 工具；本实现零依赖
 */
function arrayBufferToString(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let result = '';
  // 按 chunk 处理，避免一次性转 string 触发超大字符串
  const CHUNK_SIZE = 0x8000;
  for (let i = 0; i < bytes.length; i += CHUNK_SIZE) {
    const slice = bytes.subarray(i, Math.min(i + CHUNK_SIZE, bytes.length));
    result += String.fromCharCode.apply(null, Array.from(slice));
  }
  // UTF-8 解码
  try {
    // 尝试使用 decodeURIComponent 转义（仅对 ASCII 安全部分）
    // 微信小程序环境不提供 TextDecoder，但提供 wx.arrayBufferToBase64 / wx.base64ToArrayBuffer
    // 这里采用 BinaryString + decodeURIComponent 的经典兼容写法
    const utf8Bytes = result;
    let str = '';
    let i = 0;
    while (i < utf8Bytes.length) {
      const c1 = utf8Bytes.charCodeAt(i);
      if (c1 < 0x80) {
        str += String.fromCharCode(c1);
        i += 1;
      } else if ((c1 & 0xe0) === 0xc0) {
        const c2 = utf8Bytes.charCodeAt(i + 1);
        str += String.fromCharCode(((c1 & 0x1f) << 6) | (c2 & 0x3f));
        i += 2;
      } else if ((c1 & 0xf0) === 0xe0) {
        const c2 = utf8Bytes.charCodeAt(i + 1);
        const c3 = utf8Bytes.charCodeAt(i + 2);
        str += String.fromCharCode(((c1 & 0x0f) << 12) | ((c2 & 0x3f) << 6) | (c3 & 0x3f));
        i += 3;
      } else {
        // 4 字节代理对 (UTF-16)
        const c2 = utf8Bytes.charCodeAt(i + 1);
        const c3 = utf8Bytes.charCodeAt(i + 2);
        const c4 = utf8Bytes.charCodeAt(i + 3);
        const codePoint =
          ((c1 & 0x07) << 18) |
          ((c2 & 0x3f) << 12) |
          ((c3 & 0x3f) << 6) |
          (c4 & 0x3f);
        const offset = codePoint - 0x10000;
        str += String.fromCharCode(0xd800 + (offset >> 10));
        str += String.fromCharCode(0xdc00 + (offset & 0x3ff));
        i += 4;
      }
    }
    return str;
  } catch (e) {
    // 降级：返回原始字节字符串（可能含乱码，但不会崩溃）
    return result;
  }
}

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
      chunk = arrayBufferToString(res.data);
    } else if (res.data) {
      chunk = String(res.data);
    }
    if (chunk) {
      dlog('sse-http:onChunk', 'chunk length:', chunk.length, 'preview:', chunk.substring(0, 80));
      feed(chunk);
    }
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
  // POST + JSON body 时强制声明 Content-Type（后端 Pydantic 强依赖 application/json；
  // 注意：部分微信基础库在 enableChunked 时可能默认覆盖 Content-Type，在此显式设置）
  if (httpMethod === 'POST' && bodyData) {
    header['Content-Type'] = 'application/json';
  }

  try {
    task = wxRequest({
      url,
      method: httpMethod,
      enableChunked: true,
      responseType: 'arraybuffer',
      header,
      ...(bodyData ? { data: bodyData } : {}),
      timeout: opts.timeoutMs,
      success: (res: unknown) => {
        // #region agent log
        const status = (res as { statusCode?: number; status?: number } | undefined)?.statusCode
          ?? (res as { status?: number } | undefined)?.status;
        dlog('sse-http.ts:wxRequest.success', 'wx.request success', { url, method: httpMethod, status, resKeys: res && typeof res === 'object' ? Object.keys(res) : null });
        // #endregion
        // HTTP 4xx/5xx：statusCode 存在且 >= 400 → 解析 body → 触发 error 事件（触发前端 toast）
        if (status !== undefined && status >= 400) {
          const resObj = res as { data?: string; statusCode?: number };
          let code = 'E_UNKNOWN_HTTP_ERROR';
          let message_zh = `请求失败 (${status})`;
          // 尝试解析 JSON body 中的 error.code / error.message_zh
          if (resObj.data) {
            try {
              const parsed = JSON.parse(resObj.data);
              if (parsed?.error?.code) code = parsed.error.code;
              if (parsed?.error?.message_zh) message_zh = parsed.error.message_zh;
            } catch { /* use defaults */ }
          }
          const errEvt: SseEvent = {
            name: 'error',
            data: { code, message_zh },
          };
          dispatcher.push(errEvt);
          opts.onTerminal?.(errEvt);
          cleanup();
          return;
        }
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
