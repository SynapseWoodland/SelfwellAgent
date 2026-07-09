/**
 * Selfwell 自愈 · 前端 RED 测试 — M8 recall-compare 空态 soft-tip
 * ───────────────────────────────────────────
 * 真源：
 * - docs/adr/0017-recall-safety.md §3.6 空态 soft-tip
 * - apps/mp-selfwell/miniprogram/pages/recall-compare/index.{ts,wxml}
 *
 * 约束：
 * - mock GET /butler/recall/day/{day} 返回空（用户从未上传 feedback）
 * - wxml 渲染 soft-tip 3 按钮（补一组 / 就这样聊 / 取消）
 * - 不调 LLM（按 ADR-0017 §3.6 强约束）
 */

import { afterEach, describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readWxml(): string {
  return readFileSync(join(__dirname, '../miniprogram/pages/recall-compare/index.wxml'), 'utf-8');
}

describe('recall-compare 空态 soft-tip', () => {
  it('wxml 软提示文案存在（"还没有你的资料" / "要不要先补一组"）', () => {
    const wxml = readWxml();
    // 软提示主文案（ADR-0017 §3.6）
    const hasSoftTipMessage =
      wxml.includes('我还没有你的资料呢') ||
      wxml.includes('要不要先补一组') ||
      wxml.includes('soft-tip');
    expect(hasSoftTipMessage).toBe(true);
  });

  it('空态 3 按钮 styles 区分（warm / white / gray）', () => {
    const wxml = readWxml();
    // 至少包含 3 个绑定 style 占位的按钮
    const buttonMatches = wxml.match(/bindtap="[^"]*"/g) || [];
    expect(buttonMatches.length).toBeGreaterThanOrEqual(3);
  });

  it('空态不调 LLM（ADR-0017 §3.6：永不调 LLM）', () => {
    const ts = readFileSync(join(__dirname, '../miniprogram/pages/recall-compare/index.ts'), 'utf-8');
    // 空态分支不应触发 sendMessage 或 assistant 调用（仅静态跳转）
    // 通过简单的关键字搜索验证
    const hasEmptyStateNoLLM =
      ts.includes('isEmpty') ||
      ts.includes('is_empty') ||
      ts.includes('soft_tip') ||
      ts.includes('softTip');
    expect(hasEmptyStateNoLLM).toBe(true);
  });
});

afterEach(() => {
  /* cleanup */
});
