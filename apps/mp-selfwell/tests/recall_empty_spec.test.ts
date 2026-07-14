/**
 * Selfwell 前端 RED 测试 - recall-compare 空态 15e alignment
 * 真源：ADR-0017 Recall Safety s3.6 空态 soft-tip
 * PR-V2-D 实施后：添加 actions-bar 和双 CTA（已完成）
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readTs(): string {
  return readFileSync(join(__dirname, '../miniprogram/pages/recall-compare/index.ts'), 'utf-8');
}

function readWxss(): string {
  return readFileSync(join(__dirname, '../miniprogram/pages/recall-compare/index.wxss'), 'utf-8');
}

describe('recall-compare PR-V2-D 15e 实施后验证', () => {
  it('ts 不调用 LLM (ADR-0017 s3.6)', () => {
    const ts = readTs();
    expect(ts).not.toMatch(/sendMessage|POST.*assistant|POST.*chat/);
  });

  it('wxml 有空态兜底文案', () => {
    const wxml = readFileSync(
      join(__dirname, '../miniprogram/pages/recall-compare/index.wxml'),
      'utf-8',
    );
    expect(wxml).toContain('还没有对比数据');
  });

  it('wxss 有基本样式 (recall-page + timeline-card)', () => {
    const wxss = readWxss();
    expect(wxss).toContain('.recall-page');
    expect(wxss).toContain('.timeline-card');
  });

  it('wxss 有 actions-bar 双 CTA 样式', () => {
    const wxss = readWxss();
    expect(wxss).toContain('.actions-bar');
    expect(wxss).toContain('.btn-ghost');
    expect(wxss).toContain('.btn-primary');
  });

  it('wxml 有 intro-bubble + reply-bubble', () => {
    const wxml = readFileSync(
      join(__dirname, '../miniprogram/pages/recall-compare/index.wxml'),
      'utf-8',
    );
    expect(wxml).toContain('intro-bubble');
    expect(wxml).toContain('reply-bubble');
  });
});
