/**
 * Selfwell 自愈 · 前端 Vitest 静态契约 — assistant-home 的 abort 信号改造
 * ────────────────────────────────────────────────────────────
 * 真源：Stream Y / PR-A2 worker Y（决策 2：abort signal 语义）
 *
 * 约束（不可绕过）：
 *  - 暴露 cancelMockAnalyze() 方法
 *  - onUnload 清理 AbortController
 *  - abort 路径不调用 applyAssistantError，不调用 wx.showToast 失败文案
 *  - startMockAnalyze 启用 AbortController（创建后桥接到 consumer.cancel()）
 *  - consumeAssistantStream 对 AbortError 做静默退出（不 toast）
 *
 * 这是一个静态扫描测试（与 assistant_home_entry.spec.test.ts 风格一致）。
 * 真正端到端测试需要 wx runtime + DOM，超出 vitest 单元可达范围。
 */

import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readPageSource(): string {
  return readFileSync(
    join(__dirname, '../miniprogram/pages/assistant-home/index.ts'),
    'utf-8',
  );
}

describe('assistant-home — Stream Y abort signal 改造 静态契约', () => {
  it('startMockAnalyze 内部创建 AbortController 并桥接到 consumer.cancel()', () => {
    const src = readPageSource();
    expect(src).toContain('new AbortController()');
    // 桥接：AbortController.signal 的 abort 事件 → consumer.cancel()
    expect(src).toContain("consumerSignal.addEventListener('abort'");
    expect(src).toMatch(/consumer\.cancel\(\)/);
  });

  it('暴露 cancelMockAnalyze() 方法，且不调 applyAssistantError、不调 wx.showToast 失败', () => {
    const src = readPageSource();
    expect(src).toContain('cancelMockAnalyze()');
    // cancelMockAnalyze 内不应出现 applyAssistantError 调用
    const idx = src.indexOf('cancelMockAnalyze()');
    const blockStart = idx;
    const blockEnd = src.indexOf('},', idx + 30);
    const block = src.slice(blockStart, blockEnd > 0 ? blockEnd : idx + 800);
    expect(block).not.toContain('applyAssistantError');
    expect(block).not.toContain('wx.showToast');
  });

  it('onUnload 清理 AbortController + consumer', () => {
    const src = readPageSource();
    const idx = src.indexOf('onUnload()');
    expect(idx).toBeGreaterThan(0);
    const blockEnd = src.indexOf('},', idx + 30);
    const block = src.slice(idx, blockEnd > 0 ? blockEnd : idx + 1200);
    expect(block).toContain('_sseAbortController');
    expect(block).toContain('.abort()');
    expect(block).toContain('_sseConsumer');
  });

  it('consumeAssistantStream 对 AbortError 做静默退出（不调 applyAssistantError）', () => {
    const src = readPageSource();
    const idx = src.indexOf('async consumeAssistantStream');
    expect(idx).toBeGreaterThan(0);
    const blockEnd = src.indexOf('},\n  applyAssistantProgress', idx);
    const block = src.slice(idx, blockEnd > 0 ? blockEnd : idx + 2000);
    // catch 分支应识别 AbortError 并 return
    expect(block).toMatch(/AbortError/);
    // AbortError 分支不能调 applyAssistantError
    const abortIdx = block.indexOf('AbortError');
    const abortSlice = block.slice(abortIdx, abortIdx + 200);
    expect(abortSlice).not.toContain('applyAssistantError');
  });
});
