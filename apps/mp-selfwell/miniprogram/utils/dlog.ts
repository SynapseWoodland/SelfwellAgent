/**
 * Selfwell · debug-e3bb88 异步日志 helper（业界 wx.request + console 兜底）
 * ──────────────────────────────────────────────────────────────────
 * 微信小程序 v2.32.3 没有 Web fetch API；远程日志走 ``wx.request``，完全异步
 * + 不抛 + 不阻塞主流程，失败静默。本地同步 echo 到 console 让 IDE 控制台可见。
 *
 * 用法：
 *   import { dlog } from '../../utils/dlog';
 *   dlog('onSubmitUpload.entry', 'called', { x: 1 });
 *
 * 协议：POST JSON 到 ${DEBUG_INGEST_URL}，X-Debug-Session-Id='e3bb88'。
 * 服务端把 NDJSON 写到 ${LOG_PATH}，可由 /workspace/debug-e3bb88.log 读。
 */
const DEBUG_INGEST_URL =
  'http://127.0.0.1:7556/ingest/1bc90c1f-0b68-4af6-b6b5-155d72835ebd';
const SESSION_ID = 'e3bb88';

export function dlog(location: string, message: string, data: unknown): void {
  // 1) 本地 console fallback（IDE 控制台立刻可见，调试最稳）
  try {
    // eslint-disable-next-line no-console
    console.log(
      `[dlog ${SESSION_ID}] ${location} | ${message}`,
      data ?? {},
    );
  } catch {
    /* console 不可用不影响主流程 */
  }

  // 2) 远程 ingest（wx.request 异步，绝不抛）
  try {
    const payload = {
      sessionId: SESSION_ID,
      location,
      message,
      data: data ?? {},
      timestamp: Date.now(),
    };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const wxr = (wx as any).request;
    if (typeof wxr !== 'function') return; // 测试环境兜底
    wxr({
      url: DEBUG_INGEST_URL,
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'X-Debug-Session-Id': SESSION_ID,
      },
      data: payload,
      success: () => { /* silently delivered */ },
      fail: () => { /* intentionally swallowed; 127.0.0.1:7556 可能不通 */ },
    });
  } catch {
    // 任何异常吞掉——debug 永远不应阻塞业务
  }
}
