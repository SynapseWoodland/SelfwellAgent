/**
 * Selfwell 自愈 · 前端 Vitest 单测 — assistant-home entry card 跳转（PR-A4）
 * ────────────────────────────────────────────────────────────
 * 真源：apps/mp-selfwell/miniprogram/pages/assistant-home/index.ts
 *      plan §5.2 — 「assistant-home 的「智能分析」卡片 wx.navigateTo 到 pages/smart-analyze-upload/index」
 *
 * 覆盖：
 *  - entryCards 列表含 id === 'smart_analyze'
 *  - onTapEntry 处理 smart_analyze 分支调用 wx.navigateTo 目标 /pages/smart-analyze-upload/index
 *  - 当前 id === 'upload' 的旧版分支仍然存在（向后兼容 SF2）
 */

import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readSource(relPath: string): string {
  return readFileSync(join(__dirname, '../miniprogram', relPath), 'utf-8');
}

describe('assistant-home — PR-A4 新 entry card "smart_analyze"', () => {
  it('entryCards 数据含 id="smart_analyze"', () => {
    const ts = readSource('pages/assistant-home/index.ts');
    expect(ts).toContain("id: 'smart_analyze'");
  });

  it('onTapEntry 处理 smart_analyze → wx.navigateTo 到 /pages/smart-analyze-upload/index', () => {
    const ts = readSource('pages/assistant-home/index.ts');
    // 取出 onTapEntry 函数体
    const match = ts.match(/onTapEntry\([^)]*\)\s*{([\s\S]*?)\n\s*},?[\n\s]*\}/);
    expect(match).toBeTruthy();
    const body = match?.[1] ?? '';
    expect(body).toContain("id === 'smart_analyze'");
    expect(body).toContain('/pages/smart-analyze-upload/index');
  });

  it('保留旧版 id="upload" → /pages/diagnosis-upload/index（向后兼容）', () => {
    const ts = readSource('pages/assistant-home/index.ts');
    expect(ts).toContain("id === 'upload'");
    expect(ts).toContain('/pages/diagnosis-upload/index');
  });

  it('app.json 注册了 4 个新页面', () => {
    const json = readSource('app.json');
    expect(json).toContain('pages/smart-analyze-upload/index');
    expect(json).toContain('pages/smart-analyze-loading/index');
    expect(json).toContain('pages/smart-analyze-report/index');
    expect(json).toContain('pages/plan-tabs/index');
  });
});
