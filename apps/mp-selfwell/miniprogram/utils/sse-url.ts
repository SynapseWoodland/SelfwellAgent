/**
 * FE-FIX-08 · SSE stream_url 路径拼接辅助函数
 * ──────────────────────────────────────────────────────────────
 * 真源：docs/plan/frontend-fix-plan.md §FE-FIX-08
 * 真源：backend/app/services/assistant_service.py:442
 *   `stream_url: f"/diagnosis/jobs/{job_id}/stream"`  ← 不带 /api/v1 前缀
 *
 * 设计要点：
 *  - 后端 stream_url 可能返回两种形式：
 *    A) `/diagnosis/jobs/{id}/stream`（assistant_service 当前实现 — 无 /api/v1 前缀）
 *    B) `/api/v1/diagnosis/jobs/{id}/stream`（理论契约 — 含 /api/v1 前缀）
 *  - 前端 utils/request.ts 已经把"API path"（不带 /api/v1）拼成完整 URL；SSE
 *    不走 utils/request.ts（直连），需独立拼接。
 *
 *  规则：
 *   1. 绝对 URL（http/https）— 原样返回
 *   2. 含 /api/v1 前缀 — 拼 host 部分（无 path 段）+ path
 *   3. 无 /api/v1 前缀 — API_BASE_URL[CURRENT_ENV] + path
 *
 *  注意：
 *  - API_BASE_URL[CURRENT_ENV] 已包含 /api/v1 后缀（如 `https://.../api/v1`）
 *  - 不能简单 `${base}${path}` —— 当 path 已是 `${base}` 子串时会双前缀
 */
import { API_BASE_URL, CURRENT_ENV, type Env } from './config';

/** 判断 URL 是否绝对（含 scheme）。 */
export function isAbsoluteUrl(url: string): boolean {
  return /^https?:\/\//i.test(url);
}

/** 抽出 host（含 scheme + host:port + 已存在的 /api/v1 后缀）。
 *  - 例如 `https://api.selfwell.app/api/v1` → 返回 `https://api.selfwell.app/api/v1`
 *  - 通常 API_BASE_URL[CURRENT_ENV] 直接就是这个值 */
export function getApiBaseUrl(env: Env = CURRENT_ENV): string {
  return API_BASE_URL[env];
}

/**
 * 拼 SSE stream_url 绝对 URL。
 *
 * @param streamPath  后端返回的 stream_url（可能 /api/v1 前缀 / 可能不带 / 可能是 http(s):// 绝对）
 * @param env         运行环境；默认 CURRENT_ENV
 * @returns           完整 URL（含 scheme + host + path）
 */
export function buildSseStreamUrl(streamPath: string, env: Env = CURRENT_ENV): string {
  // 1. 已是绝对 URL → 原样返回（后端给完整 URL / 测试 mock）
  if (isAbsoluteUrl(streamPath)) return streamPath;

  const base = API_BASE_URL[env];
  // 2. 含 /api/v1 前缀 → 去掉 base 的 /api/v1 部分，再 join（避免双前缀）
  //    例如 base = 'https://api.selfwell.app/api/v1', path = '/api/v1/diagnosis/jobs/.../stream'
  //    期望 'https://api.selfwell.app/api/v1/diagnosis/jobs/.../stream'
  //    算法：base.host + path（base 去掉尾 /api/v1）
  const baseWithoutApiV1 = base.replace(/\/api\/v\d+\/?$/, '');
  // 防御：若 base 不含 /api/v1（极端环境），退化为直接拼接
  if (baseWithoutApiV1 === base) {
    const joiner = streamPath.startsWith('/') ? '' : '/';
    return `${base}${joiner}${streamPath}`;
  }

  // 3. 无 /api/v1 前缀 → 直接 `${base}${path}`
  if (streamPath.startsWith('/api/v')) {
    return `${baseWithoutApiV1}${streamPath}`;
  }
  // 普通 path：拼接 base（base 已含 /api/v1）+ path
  const joiner = streamPath.startsWith('/') ? '' : '/';
  return `${base}${joiner}${streamPath}`;
}