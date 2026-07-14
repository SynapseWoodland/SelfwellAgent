/**
 * FE-FIX-08 · SSE stream_url 路径前缀拼接单测
 * ──────────────────────────────────────────────────────────────
 * 真源：docs/plan/frontend-fix-plan.md §FE-FIX-08
 * 真源：backend/app/services/assistant_service.py:442（`stream_url: f"/diagnosis/jobs/{job_id}/stream"`）
 *
 * 验收标准：
 *  - 后端返回不带 /api/v1 前缀（assistant_service.py:442 当前实现）
 *    → buildSseStreamUrl 拼出正确 URL，无 404
 *  - 后端返回带 /api/v1 前缀（理论契约）
 *    → buildSseStreamUrl 不双前缀
 *  - 后端返回 http(s):// 绝对 URL
 *    → 原样使用，不重复拼 base
 *  - diagnosis-loading-v2/index.ts 必须使用 buildSseStreamUrl 工厂
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import {
  buildSseStreamUrl,
  getApiBaseUrl,
  isAbsoluteUrl,
} from '../miniprogram/utils/sse-url';
import { API_BASE_URL, CURRENT_ENV } from '../miniprogram/utils/config';

describe('FE-FIX-08 · utils/sse-url.ts buildSseStreamUrl()', () => {
  it('用例 1: isAbsoluteUrl 判定 https / http', () => {
    expect(isAbsoluteUrl('https://api.selfwell.app/api/v1/x')).toBe(true);
    expect(isAbsoluteUrl('http://localhost:8000/x')).toBe(true);
    expect(isAbsoluteUrl('/diagnosis/jobs/abc/stream')).toBe(false);
    expect(isAbsoluteUrl('diagnosis/jobs/abc/stream')).toBe(false);
  });

  it('用例 2: getApiBaseUrl 默认返回当前环境 base', () => {
    expect(getApiBaseUrl()).toBe(API_BASE_URL[CURRENT_ENV]);
    expect(getApiBaseUrl('dev')).toBe(API_BASE_URL.dev);
    expect(getApiBaseUrl('staging')).toBe(API_BASE_URL.staging);
    expect(getApiBaseUrl('prod')).toBe(API_BASE_URL.prod);
  });

  it('用例 3: 后端不带 /api/v1 前缀（assistant_service.py:442 当前实现）→ 拼出正确 URL', () => {
    // 真源：assistant_service.py:442 → `stream_url: f"/diagnosis/jobs/{job_id}/stream"`
    const jobId = 'job_abc123';
    const path = `/diagnosis/jobs/${jobId}/stream`;
    const out = buildSseStreamUrl(path);
    const base = API_BASE_URL[CURRENT_ENV];
    expect(out).toBe(`${base}${path}`);
    expect(out).toContain('/api/v1/diagnosis/jobs/job_abc123/stream');
    // 不应出现双 /api/v1
    expect(out.match(/\/api\/v1/g)?.length).toBe(1);
  });

  it('用例 4: 后端带 /api/v1 前缀（理论契约）→ 不双前缀', () => {
    const path = `/api/v1/diagnosis/jobs/job_xyz/stream`;
    const out = buildSseStreamUrl(path);
    expect(out.match(/\/api\/v1/g)?.length).toBe(1);
    // 期望结尾包含 /diagnosis/jobs/job_xyz/stream
    expect(out.endsWith('/diagnosis/jobs/job_xyz/stream')).toBe(true);
  });

  it('用例 5: 后端返回绝对 URL → 原样返回，不重复拼 base', () => {
    const abs = 'https://api.selfwell.app/diagnosis/jobs/job_abs/stream';
    const out = buildSseStreamUrl(abs);
    expect(out).toBe(abs);
  });

  it('用例 6: path 不带前导 / → 自动补 /', () => {
    const path = `diagnosis/jobs/job_no_slash/stream`;
    const out = buildSseStreamUrl(path);
    const base = API_BASE_URL[CURRENT_ENV];
    expect(out).toBe(`${base}/${path}`);
  });

  it('用例 7: 不同 env 拼接正确（staging / prod）', () => {
    const path = '/diagnosis/jobs/j1/stream';
    expect(buildSseStreamUrl(path, 'staging')).toBe(`${API_BASE_URL.staging}${path}`);
    expect(buildSseStreamUrl(path, 'prod')).toBe(`${API_BASE_URL.prod}${path}`);
  });
});

describe('FE-FIX-08 · diagnosis-loading-v2 集成契约锁', () => {
  it('diagnosis-loading-v2/index.ts 必须 import buildSseStreamUrl', () => {
    const ts = readFileSync(
      join(__dirname, '..', 'miniprogram', 'pages', 'diagnosis-loading-v2', 'index.ts'),
      'utf-8',
    );
    expect(ts).toMatch(/import\s*\{[^}]*buildSseStreamUrl[^}]*\}\s*from\s*['"]\.\.\/\.\.\/utils\/sse-url['"]/);
  });
  it('diagnosis-loading-v2 startSse 走 buildSseStreamUrl 工厂（不再内联拼接）', () => {
    const ts = readFileSync(
      join(__dirname, '..', 'miniprogram', 'pages', 'diagnosis-loading-v2', 'index.ts'),
      'utf-8',
    );
    expect(ts).toContain('buildSseStreamUrl(streamPath)');
    // 不再使用 inline `API_BASE_URL[CURRENT_ENV]` 拼接
    const startSse = ts.match(/startSse\s*\([^)]*\)\s*\{([\s\S]*?)\n\s*\}\s*,?/);
    const body = startSse?.[1] ?? '';
    expect(body, 'startSse 不允许内联 API_BASE_URL 拼接').not.toMatch(/API_BASE_URL\[CURRENT_ENV\]/);
  });
});