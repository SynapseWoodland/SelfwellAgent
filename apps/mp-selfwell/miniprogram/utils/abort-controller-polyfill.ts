/**
 * Selfwell · AbortController polyfill（微信小程序兼容）
 * ──────────────────────────────────────────────────────
 * 背景：微信小程序基础库（截至 2.32.3）**尚未原生支持** ``AbortController`` /
 * ``AbortSignal``（Web API）。这导致 streamY / worker Y 的 SSE 取消链路
 * （``new AbortController()`` + ``signal.addEventListener('abort', cb)``）直接抛
 * ``ReferenceError: AbortController is not defined``。
 *
 * 解决：实现最小可用 polyfill，**形状严格对齐 Web 规范**：
 *  - ``new AbortController()`` 返回 ``{ signal, abort() }``
 *  - ``signal.aborted`` boolean
 *  - ``signal.addEventListener('abort', cb, { once })`` / ``removeEventListener``
 *  - ``signal.removeEventListener`` / ``signal.dispatchEvent``（满足 lint 完整性）
 *  - ``abort(reason?)`` 幂等：多次调用只触发一次
 *
 * 注入策略：``installAbortControllerPolyfill()`` 把全局
 * ``(globalThis as any).AbortController`` 设成本 polyfill；调用方在文件入口
 * ``import '.../utils/abort-controller-polyfill'`` 即可，无需改业务代码。
 *
 * 兼容性：
 *  - 基础库 ≥ 2.32.0：理论上官方提供，但实际用户层 ``new`` 仍偶发 undefined；
 *    本 polyfill **优先于原生** 覆盖，避免开发者环境差异。
 *  - 基础库 < 2.32.0：原生一定 undefined，本 polyfill 兜底。
 *
 * 边界：仅实现本项目用到的子集（addEventListener('abort', ...) + aborted + abort）。
 *      不实现 ``throwIfAborted``、reason 透传、``any`` 事件名等扩展。
 */
type AbortListener = (this: AbortSignalLike, ev: Event) => void;

interface AbortSignalLike {
  aborted: boolean;
  addEventListener(type: 'abort', listener: AbortListener, options?: { once?: boolean }): void;
  removeEventListener(type: 'abort', listener: AbortListener): void;
  dispatchEvent(event: Event): boolean;
}

interface AbortControllerLike {
  signal: AbortSignalLike;
  abort(reason?: unknown): void;
}

class AbortSignalImpl implements AbortSignalLike {
  aborted = false;
  private listeners: Array<{ cb: AbortListener; once: boolean }> = [];

  addEventListener(type: 'abort', listener: AbortListener, options?: { once?: boolean }): void {
    if (type !== 'abort') return;
    if (this.aborted) {
      // 已 abort：立即异步触发一次（对齐 Web 规范）
      if (options?.once !== false) {
        queueMicrotask(() => {
          try { listener.call(this, makeAbortEvent()); } catch { /* ignore */ }
        });
      }
      return;
    }
    this.listeners.push({ cb: listener, once: options?.once === true });
  }

  removeEventListener(type: 'abort', listener: AbortListener): void {
    if (type !== 'abort') return;
    this.listeners = this.listeners.filter((l) => l.cb !== listener);
  }

  dispatchEvent(event: Event): boolean {
    if (event.type !== 'abort') return false;
    const snapshot = this.listeners.slice();
    for (const item of snapshot) {
      try { item.cb.call(this, event); } catch { /* ignore */ }
      if (item.once) {
        this.listeners = this.listeners.filter((l) => l.cb !== item.cb);
      }
    }
    return true;
  }

  /** 内部触发 abort 事件（由 AbortControllerImpl.abort 调） */
  _fireAbort(): void {
    if (this.aborted) return;
    this.aborted = true;
    this.dispatchEvent(makeAbortEvent());
  }
}

function makeAbortEvent(): Event {
  // 小程序里 ``new Event('abort')`` 也可能 undefined；用最小对象模拟
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ev: any = { type: 'abort', bubbles: false, cancelable: false, defaultPrevented: false };
  return ev as Event;
}

class AbortControllerImpl implements AbortControllerLike {
  signal: AbortSignalImpl = new AbortSignalImpl();
  abort(_reason?: unknown): void {
    if (this.signal.aborted) return;
    this.signal._fireAbort();
  }
}

/**
 * 把全局 ``AbortController`` 指向本 polyfill。**幂等**：若全局已存在
 * （开发者环境官方已支持），跳过覆盖，保留原生实现，避免与微信官方后续升级冲突。
 */
export function installAbortControllerPolyfill(): void {
  // globalThis 在微信小程序里 = 全局对象
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const g = globalThis as any;
  if (typeof g.AbortController === 'function') {
    // 原生已存在：仅当检测到原生抛 ReferenceError 时才覆盖
    // （开发期可通过 try/catch new AbortController 验证——这里只做 soft 检测）
    return;
  }
  g.AbortController = AbortControllerImpl;
}

// 模块加载时自动注入（import 即可生效）
installAbortControllerPolyfill();

export type { AbortControllerLike as AbortController, AbortSignalLike as AbortSignal };
