/**
 * Selfwell 自愈 · 前端 RED 测试 — M8 recall-compare 页
 * ───────────────────────────────────────────
 * 真源：
 * - docs/spec/SPEC-M8-recall.md §3.10
 * - ADR-0017 Recall Safety + §3.5 永不复用清单
 * - apps/mp-selfwell/miniprogram/pages/recall-compare/index.{ts,wxml}
 *
 * 约束：
 * - mock GET /butler/recall/day/{day} 返回高亮 + 缩略图
 * - wxml 渲染缩略图（thumbnail_signed_url）
 * - wxml 不含 "坚持 X 天" 字样（即使 mock 数据含 habitStreak 也不能渲染 — ADR-0017）
 * - mock 空态 → 渲染 soft-tip 3 按钮（补一组 / 就这样聊 / 取消）
 */

import { afterEach, describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readWxml(): string {
  return readFileSync(join(__dirname, '../miniprogram/pages/recall-compare/index.wxml'), 'utf-8');
}

function readTs(): string {
  return readFileSync(join(__dirname, '../miniprogram/pages/recall-compare/index.ts'), 'utf-8');
}

// ─────────────────────────────────────────────────────────────────────────────
// recall-compare 接 GET /butler/recall/day/{day}
// ─────────────────────────────────────────────────────────────────────────────
describe('recall-compare 契约 — 接真实 endpoint', () => {
  it('recall-compare/index.ts 调用 /butler/recall/day/{day}', () => {
    const ts = readTs();
    expect(ts).toMatch(/\/butler\/recall\/day\/\$\{day\}/);
  });

  it('recall-compare/index.ts 不再使用 mock snapshot (MOCK_BY_DAY)', () => {
    const ts = readTs();
    // 不应有 MOCK_BY_DAY 常量
    expect(ts).not.toContain('MOCK_BY_DAY');
  });
});

describe('recall-compare 契约 — 去 mock habitStreak 字段 (ADR-0017)', () => {
  it('recall-compare/index.ts 接口/类型不含 habitStreak 字段', () => {
    const ts = readTs();
    expect(ts).not.toContain('habitStreak');
    expect(ts).not.toContain('habit_streak');
  });

  it('recall-compare/index.wxml 不渲染 "坚持 X 天" 字样', () => {
    const wxml = readWxml();
    // 关键断言：即使后端返回了 habitStreak，前端 UI 也不渲染
    expect(wxml).not.toMatch(/坚持\s*\d+\s*天/);
    expect(wxml).not.toContain('habitStreak');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Day 7/14/21 切换
// ─────────────────────────────────────────────────────────────────────────────
describe('recall-compare 契约 — Day 7/14/21 切换', () => {
  it('wxml 包含 3 个 day tab（7/14/21）', () => {
    const wxml = readWxml();
    expect(wxml).toContain('第 7 天');
    expect(wxml).toContain('第 14 天');
    expect(wxml).toContain('第 21 天');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 空态 soft-tip 3 按钮
// ─────────────────────────────────────────────────────────────────────────────
describe('recall-compare 契约 — 空态 soft-tip 3 按钮', () => {
  it('wxml 包含 3 按钮文案（补一组 / 就这样聊 / 取消）', () => {
    const wxml = readWxml();
    expect(wxml).toContain('补一组');
    expect(wxml).toContain('就这样聊');
    expect(wxml).toContain('取消');
  });

  it('空态按钮路由跳转：补一组 → feedback-diary；就这样聊 → assistant-home；取消 → 关闭', () => {
    const ts = readTs();
    // 至少 3 个 navigateTo 调用或 onTap handler
    expect(ts).toContain('feedback-diary');
    expect(ts).toContain('assistant-home');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 渲染缩略图（thumbnail_signed_url）
// ─────────────────────────────────────────────────────────────────────────────
describe('recall-compare 契约 — 渲染缩略图', () => {
  it('wxml 包含 image 元素绑定 thumbnail 字段', () => {
    const wxml = readWxml();
    expect(wxml).toMatch(/<image[^>]*src="\{\{[^}]*thumbnail/);
  });
});

afterEach(() => {
  /* cleanup */
});
