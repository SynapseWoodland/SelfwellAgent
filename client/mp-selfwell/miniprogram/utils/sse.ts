/**
 * Selfwell · SSE 客户端（基于 wx.connectSocket）
 * ──────────────────────────────────────────────
 * 背景：微信小程序不支持 EventSource / fetch streaming，只能用 WebSocket。
 * 因此后端 SSE endpoint 需以 "websocket + 帧边界 \n\n" 形式等价暴露。
 *（后端 openapi.yaml 标注 `wss://.../diagnosis/{id}/stream`，见 operationId=streamDiagnosis）
 *
 * 约束（§17.16）：
 *  - 默认 1s → 2s → 4s → 8s → 16s → 30s 上限指数退避
 *  - 5 次失败触发 onFailure("网络异常，请稍后查看报告")
 *  - 收到 [DONE] 帧触发 onComplete
 *
 * 注：基础库 2.18+ 提供 SocketTask.onClose / offClose，本工具遵循 Promise 化封装。
 */

import {
  CURRENT_ENV,
  SSE_BACKOFF_STEPS_MS,
  SSE_BASE_URL,
  SSE_MAX_RETRY,
  STORAGE_KEYS,
  TRACEPARENT_HEADER,
} from './config';
import { buildTraceparent as _sharedTp } from './request';

export interface SseEvent {
  /** 事件名（后端约定：progress / chunk / error / done） */
  event: string;
  /** 事件 id（可选；后端可用于断点续传） */
  id?: string;
  /** 业务 payload（已 JSON.parse） */
  data: unknown;
}

export interface SseHandlers {
  onEvent: (e: SseEvent) => void;
  onComplete?: () => void;
  onFailure?: (reason: string) => void;
}

export interface SseOpenOptions {
  /** path，必填，例如 `/diagnosis/${id}/stream` */
  path: string;
  /** 自定义 header（会与 Traceparent/Auth 合并） */
  header?: Record<string, string>;
  /** 是否跳过 Traceparent 拦截器 */
  skipTraceparent?: boolean;
  /** 自定义子协议（可选） */
  protocols?: string[];
}

/** 当前活跃 socket，便于外部 close */
export class SseClient {
  private task: WechatMiniprogram.SocketTask | null = null;
  private buffer = '';
  private retries = 0;
  private closedByUser = false;
  private handlers: SseHandlers;
  private opts: SseOpenOptions;

  constructor(opts: SseOpenOptions, handlers: SseHandlers) {
    this.opts = opts;
    this.handlers = handlers;
  }

  open(): void {
    if (this.task) return;
    this.closedByUser = false;

    const header = { ...(this.opts.header ?? {}) };
    if (!this.opts.skipTraceparent) {
      header[TRACEPARENT_HEADER] = header[TRACEPARENT_HEADER] ?? this.makeTp();
    }
    const jwt = wx.getStorageSync(STORAGE_KEYS.jwt);
    if (jwt) header['Authorization'] = `Bearer ${jwt}`;

    const baseURL = SSE_BASE_URL[CURRENT_ENV];
    const url = baseURL + this.opts.path;

    this.task = wx.connectSocket({
      url,
      header,
      protocols: this.opts.protocols,
      // 微信默认值即可；超时由重连兜底
      success: () => {
        this.retries = 0; // 一次成功握手视作冷启成功
      },
      fail: (err) => {
        console.warn('[sse] connect fail', err);
        this.scheduleReconnect(`connect_fail: ${err.errMsg ?? 'unknown'}`);
      },
    });

    this.task.onOpen(() => {
      this.retries = 0;
      console.log('[sse] open', url);
    });

    this.task.onMessage((msg) => {
      this.feed(typeof msg.data === 'string' ? msg.data : '');
    });

    this.task.onError((err) => {
      console.warn('[sse] onError', err);
      this.scheduleReconnect('onError');
    });

    this.task.onClose(() => {
      if (!this.closedByUser) this.scheduleReconnect('onClose');
    });
  }

  /** 主动关闭（用户取消/退出页面） */
  close(): void {
    this.closedByUser = true;
    if (this.task) {
      try {
        this.task.close({ code: 1000, reason: 'client_close' });
      } catch (e) {
        console.warn('[sse] close warn', e);
      }
      this.task = null;
    }
  }

  /** 解析 SSE 帧边界（\n\n 分隔），并按行分发 */
  private feed(chunk: string): void {
    this.buffer += chunk;
    let idx: number;
    // eslint-disable-next-line no-cond-assign
    while ((idx = this.buffer.indexOf('\n\n')) !== -1) {
      const frame = this.buffer.slice(0, idx);
      this.buffer = this.buffer.slice(idx + 2);
      this.dispatch(frame);
    }
  }

  private dispatch(frame: string): void {
    let event = 'message';
    let id: string | undefined;
    const dataLines: string[] = [];
    for (const line of frame.split('\n')) {
      if (!line || line.startsWith(':')) continue;
      const colon = line.indexOf(':');
      const field = colon === -1 ? line : line.slice(0, colon);
      const value = colon === -1 ? '' : line.slice(colon + 1).trimStart();
      if (field === 'event') event = value;
      else if (field === 'id') id = value;
      else if (field === 'data') dataLines.push(value);
    }
    if (!dataLines.length) return;

    const raw = dataLines.join('\n');
    let parsed: unknown = raw;
    try {
      parsed = JSON.parse(raw);
    } catch {
      /* 非 JSON，原样透传 */
    }

    if (event === 'done') {
      this.handlers.onComplete?.();
      this.close();
      return;
    }
    if (event === 'error') {
      const msg =
        (parsed && typeof parsed === 'object' && 'message' in parsed
          ? String((parsed as Record<string, unknown>).message)
          : 'stream_error') || 'stream_error';
      this.handlers.onFailure?.(msg);
      this.close();
      return;
    }

    this.handlers.onEvent({ event, id, data: parsed });
  }

  private scheduleReconnect(reason: string): void {
    this.task = null;
    if (this.closedByUser) return;
    if (this.retries >= SSE_MAX_RETRY) {
      this.handlers.onFailure?.('网络异常，请稍后查看报告');
      return;
    }
    const delay = SSE_BACKOFF_STEPS_MS[Math.min(this.retries, SSE_BACKOFF_STEPS_MS.length - 1)];
    this.retries += 1;
    console.log(`[sse] retry ${this.retries}/${SSE_MAX_RETRY} in ${delay}ms (${reason})`);
    setTimeout(() => this.open(), delay);
  }

  private makeTp(): string {
    // 复用 request 中的实现
    return _sharedTp();
  }
}

/** 顶层便捷函数：一次性的 SSE 订阅，返回 client 句柄（用于关闭） */
export function openSse(opts: SseOpenOptions, handlers: SseHandlers): SseClient {
  const c = new SseClient(opts, handlers);
  c.open();
  return c;
}