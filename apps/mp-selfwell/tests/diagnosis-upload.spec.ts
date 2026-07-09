/**
 * Selfwell 自愈 · 前端 Vitest 单测 — diagnosis-upload M2 100% 落地
 * ────────────────────────────────────────────────────────────
 * 真源：M2 智能分析(上传 + AI 诊断)端到端 100% 落地修复计划 §10/§12/§16
 *
 * 覆盖：
 *  - 1/2/3 张图的 photos 数量校验逻辑
 *  - SSE 帧解析（event: stage / data: {stage}） → 正确填写 currentStage
 *  - 重连退避表 SSE_BACKOFF_STEPS_MS 形状
 *  - 后端 5 阶段 → 前端 8 阶段别名映射 (resolveUiStage)
 *  - 类型契约：DiagnosisDirection / PhotoInput 字段对齐后端
 */

import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import {
  SSE_BACKOFF_STEPS_MS,
  SSE_MAX_RETRY,
} from '../miniprogram/utils/config';
import {
  resolveUiStage,
  UI_SSE_STAGES,
} from '../miniprogram/utils/sse-stage';

// ─────────────────────────────────────────────────────────────────────────────
// 1. 照片数量校验 — 1/2/3 张图场景
// ─────────────────────────────────────────────────────────────────────────────
import { validatePhotoCount } from '../miniprogram/utils/upload-helper';

describe('validatePhotoCount — diagnosis photos 1-3 张校验', () => {
  it('0 张 → 拒绝', () => {
    const r = validatePhotoCount([]);
    expect(r.ok).toBe(false);
    expect(r.message).toContain('至少');
  });

  it('1 张 → 通过', () => {
    expect(validatePhotoCount([{ objectKey: 'a' }]).ok).toBe(true);
  });

  it('2 张 → 通过', () => {
    expect(validatePhotoCount([{ objectKey: 'a' }, { objectKey: 'b' }]).ok).toBe(true);
  });

  it('3 张 → 通过', () => {
    expect(
      validatePhotoCount([{ objectKey: 'a' }, { objectKey: 'b' }, { objectKey: 'c' }]).ok,
    ).toBe(true);
  });

  it('4 张 → 拒绝', () => {
    const r = validatePhotoCount([
      { objectKey: 'a' },
      { objectKey: 'b' },
      { objectKey: 'c' },
      { objectKey: 'd' },
    ]);
    expect(r.ok).toBe(false);
    expect(r.message).toContain('最多');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. SSE 帧解析 — 模拟后端推送 'stage' 事件 + 'done' 事件
// ─────────────────────────────────────────────────────────────────────────────
import {
  SseClient,
  _setHttpSseFactoryForTest,
  type SseHandlers,
} from '../miniprogram/utils/sse';

describe('SSE 帧解析 — 模拟后端 5 阶段 + done 事件', () => {
  it('UI_SSE_STAGES 至少有 5 个（前端 UI 8 阶段，含首尾映射）', () => {
    expect(UI_SSE_STAGES.length).toBeGreaterThanOrEqual(5);
  });

  it('后端 5 阶段 connected/queued/analyzing/ready/done 都能映射到 UI 阶段', () => {
    expect(resolveUiStage('connected')).toBe('upload_verify');
    expect(resolveUiStage('queued')).toBe('queued');
    expect(resolveUiStage('analyzing')).toBe('style_analyzing');
    expect(resolveUiStage('ready')).toBe('rendering');
    expect(resolveUiStage('done')).toBe('done');
  });

  it('未识别 stage → 原样返回（fallback 容错）', () => {
    expect(resolveUiStage('upload_verify')).toBe('upload_verify');
    expect(resolveUiStage('mystery_stage' as never)).toBe('mystery_stage');
    expect(resolveUiStage(undefined)).toBe('upload_verify');
  });

  it('诊断 loading 页使用 UI_SSE_STAGES[0] 作为 currentStage 初始值', () => {
    // 通过静态读取 wxml/tsx 验证 currentStage 初始化来自 utils/sse-stage
    const ts = readFileSync(
      join(__dirname, '../miniprogram/pages/diagnosis-loading/index.ts'),
      'utf-8',
    );
    expect(ts).toContain('UI_SSE_STAGES');
    expect(ts).toContain('resolveUiStage');
  });

  // ── HTTP SSE（chunked transfer）后端帧解析（M2 重构：wx.request enableChunked）──
  it('完整 SSE 帧解析 — 与后端 _format_sse_event 输出一致', () => {
    let pending: Array<{
      onChunk: (c: string) => void;
      onStatus: (s: number) => void;
      onError: (e: { errMsg: string }) => void;
    }> = [];
    const factory: NonNullable<Parameters<typeof SseClient>[2]> = (_url, _hdr, h) => {
      pending.push(h);
      return { abort: () => undefined };
    };
    (globalThis as unknown as { wx: { getStorageSync: (k: string) => string } }).wx = {
      getStorageSync: () => '',
    } as never;
    _setHttpSseFactoryForTest(factory);
    const events: Array<{ event: string; data: unknown }> = [];
    let completed = false;
    const handlers: SseHandlers = {
      onEvent: (e) => events.push({ event: e.event, data: e.data }),
      onComplete: () => (completed = true),
    };
    const c = new SseClient({ path: '/diagnosis/r-99/stream' }, handlers);
    c.open();
    // 触发帧 → 5 阶段 + done
    pending[0]!.onChunk(
      [
        'event: stage\ndata: {"stage":"connected"}\n\n',
        'event: stage\ndata: {"stage":"queued"}\n\n',
        'event: stage\ndata: {"stage":"analyzing"}\n\n',
        'event: stage\ndata: {"stage":"ready","report_id":"r-99"}\n\n',
        'event: done\ndata: {"ok":true,"report_id":"r-99"}\n\n',
      ].join(''),
    );
    expect(events.map((e) => e.event)).toEqual(['stage', 'stage', 'stage', 'stage']);
    expect((events[3]?.data as { stage: string; report_id: string }).report_id).toBe('r-99');
    expect(completed).toBe(true);
    _setHttpSseFactoryForTest(null);
    pending = [];
  });

  it('注释行 : heartbeat\\n\\n 不进入 onEvent', () => {
    let pending: Array<{
      onChunk: (c: string) => void;
      onStatus: (s: number) => void;
      onError: (e: { errMsg: string }) => void;
    }> = [];
    const factory: NonNullable<Parameters<typeof SseClient>[2]> = (_url, _hdr, h) => {
      pending.push(h);
      return { abort: () => undefined };
    };
    (globalThis as unknown as { wx: { getStorageSync: (k: string) => string } }).wx = {
      getStorageSync: () => '',
    } as never;
    _setHttpSseFactoryForTest(factory);
    const events: unknown[] = [];
    const handlers: SseHandlers = { onEvent: (e) => events.push(e) };
    const c = new SseClient({ path: '/x' }, handlers);
    c.open();
    pending[0]!.onChunk(': heartbeat\n\nevent: stage\ndata: {"stage":"connected"}\n\n');
    expect(events).toHaveLength(1);
    expect((events[0] as { event: string }).event).toBe('stage');
    _setHttpSseFactoryForTest(null);
    pending = [];
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. SSE 退避表
// ─────────────────────────────────────────────────────────────────────────────
describe('SSE_BACKOFF_STEPS_MS — 指数退避', () => {
  it('退避表长度 ≥ 5（1→2→4→8→16→30s）', () => {
    expect(SSE_BACKOFF_STEPS_MS.length).toBeGreaterThanOrEqual(5);
  });

  it('每一步严格递增', () => {
    for (let i = 1; i < SSE_BACKOFF_STEPS_MS.length; i++) {
      expect(SSE_BACKOFF_STEPS_MS[i]).toBeGreaterThan(SSE_BACKOFF_STEPS_MS[i - 1]);
    }
  });

  it('SSE_MAX_RETRY = 5（触发 onFailure 的阈值）', () => {
    expect(SSE_MAX_RETRY).toBe(5);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. 类型契约 — DiagnosisDirection / PhotoInput 字段对齐
// ─────────────────────────────────────────────────────────────────────────────
describe('types/api.ts 契约对齐', () => {
  it('PhotoInput 字段含 object_key / body_part / format? / size_bytes?', () => {
    const ts = readFileSync(join(__dirname, '../miniprogram/types/api.ts'), 'utf-8');
    expect(ts).toMatch(/PhotoInput[\s\S]+object_key:/);
    expect(ts).toMatch(/body_part:\s*'face'\s*\|\s*'head'\s*\|\s*'shoulder_neck'/);
    expect(ts).toMatch(/format\?/);
    expect(ts).toMatch(/size_bytes\?/);
  });

  it('DiagnosisDirection 字段含 title / description / video_url?', () => {
    const ts = readFileSync(join(__dirname, '../miniprogram/types/api.ts'), 'utf-8');
    expect(ts).toMatch(/DiagnosisDirection[\s\S]+title: string/);
    expect(ts).toMatch(/description: string/);
    expect(ts).toMatch(/video_url\?/);
  });

  it('DiagnosisStreamStage 5 阶段（不含旧的 8 阶段枚举名）', () => {
    const ts = readFileSync(join(__dirname, '../miniprogram/types/api.ts'), 'utf-8');
    expect(ts).toMatch(/DiagnosisStreamStage/);
    expect(ts).toMatch(/'connected'\s*\|\s*'queued'\s*\|\s*'analyzing'\s*\|\s*'ready'\s*\|\s*'done'/);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. diagnosis-upload wxml — 3 张照片 UI + body_part chips
// ─────────────────────────────────────────────────────────────────────────────
describe('diagnosis-upload wxml — 3 张照片 UI', () => {
  it('wxml 含 3 个 slot 循环 [0,1,2]', () => {
    const wxml = readFileSync(
      join(__dirname, '../miniprogram/pages/diagnosis-upload/index.wxml'),
      'utf-8',
    );
    expect(wxml).toMatch(/wx:for="\{\{\[0,1,2\]\}\}"/);
  });

  it('wxml 含 body_part chip 三选一（face / head / shoulder_neck）', () => {
    const wxml = readFileSync(
      join(__dirname, '../miniprogram/pages/diagnosis-upload/index.wxml'),
      'utf-8',
    );
    expect(wxml).toContain('face');
    expect(wxml).toContain('head');
    expect(wxml).toContain('shoulder_neck');
  });

  it('wxml 含 textarea 备注输入', () => {
    const wxml = readFileSync(
      join(__dirname, '../miniprogram/pages/diagnosis-upload/index.wxml'),
      'utf-8',
    );
    expect(wxml).toMatch(/<textarea[^>]+bindinput/);
  });

  it('wxml 不含 image-uploader 组件引用（已替换为内置 slot）', () => {
    const wxml = readFileSync(
      join(__dirname, '../miniprogram/pages/diagnosis-upload/index.wxml'),
      'utf-8',
    );
    expect(wxml).not.toContain('<image-uploader');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. diagnosis-report — improvements → directions 字段迁移
// ─────────────────────────────────────────────────────────────────────────────
describe('diagnosis-report wxml — directions 字段渲染', () => {
  it('wxml 渲染 report.directions 而非 improvements', () => {
    const wxml = readFileSync(
      join(__dirname, '../miniprogram/pages/diagnosis-report/index.wxml'),
      'utf-8',
    );
    expect(wxml).toContain('report.directions');
    expect(wxml).not.toContain('report.improvements');
  });

  it('wxml 展开 direction.title / direction.description / direction.video_url', () => {
    const wxml = readFileSync(
      join(__dirname, '../miniprogram/pages/diagnosis-report/index.wxml'),
      'utf-8',
    );
    expect(wxml).toContain('item.title');
    expect(wxml).toContain('item.description');
    expect(wxml).toContain('item.video_url');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 7. 路由前导斜杠 — assistant-home ROUTE_KEYWORDS
// ─────────────────────────────────────────────────────────────────────────────
describe('assistant-home 路由前缀 — 所有 page 字段带 /', () => {
  it('所有 ROUTE_KEYWORDS.page 都以 / 开头', () => {
    const ts = readFileSync(
      join(__dirname, '../miniprogram/pages/assistant-home/index.ts'),
      'utf-8',
    );
    // 抽取所有 'page: '...' 字符串
    const matches = [...ts.matchAll(/page:\s*'([^']+)'/g)].map((m) => m[1]);
    expect(matches.length).toBeGreaterThanOrEqual(7);
    for (const p of matches) {
      expect(p).toMatch(/^\/pages\//);
    }
  });
});