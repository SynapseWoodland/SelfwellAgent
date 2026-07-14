/**
 * Selfwell 前端 RED 测试 - recall-compare page PR-V2-D 实施后
 * 真源：15e-recall-cta-buttons.html
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readWxml(): string {
  return readFileSync(join(__dirname, '../miniprogram/pages/recall-compare/index.wxml'), 'utf-8');
}

function readTs(): string {
  return readFileSync(join(__dirname, '../miniprogram/pages/recall-compare/index.ts'), 'utf-8');
}

function readWxss(): string {
  return readFileSync(join(__dirname, '../miniprogram/pages/recall-compare/index.wxss'), 'utf-8');
}

describe('recall-compare 15e audit P0 (PR-V2-D 已实施)', () => {
  it('wxml: nav-bar 返回按钮 + 问问过去的你', () => {
    const wxml = readWxml();
    expect(wxml).toContain('recall-nav');
    expect(wxml).toContain('问问过去的你');
  });

  it('wxml: timeline-card 照片网格', () => {
    const wxml = readWxml();
    expect(wxml).toContain('timeline-card');
    expect(wxml).toContain('tl-grid');
  });

  it('wxml: intro-bubble + reply-bubble', () => {
    const wxml = readWxml();
    expect(wxml).toContain('intro-bubble');
    expect(wxml).toContain('reply-bubble');
  });

  it('wxss: actions-bar btn-primary btn-ghost', () => {
    const wxss = readWxss();
    expect(wxss).toContain('actions-bar');
    expect(wxss).toContain('btn-primary');
    expect(wxss).toContain('btn-ghost');
  });

  it('ts: GET /butler/recall/day/:day', () => {
    const ts = readTs();
    expect(ts).toMatch(/\/butler\/recall\/day\//);
  });
});
