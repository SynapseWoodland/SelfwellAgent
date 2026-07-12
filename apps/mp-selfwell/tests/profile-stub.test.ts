/**
 * PR-3 commit-1 · profile 旧页 redirect stub 契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-IA-pr-internal.md §PR-3 commit-1 §验收清单
 * 真源：plans/v2-unified-parent.md §3.3「profile redirect 跳 profile-new 不死循环」
 *
 * 锁值 1 用例（PR-3 §"profile-stub 1 用例"对齐）：
 *  - profile/index.ts onLoad 调 wx.reLaunch 跳 /pages/profile-new/index
 *  - 用 reLaunch 而非 navigateTo：reLaunch 清空页面栈，避免 profile-new → 返回 profile 的回退循环
 *  - profile/index.wxml 存在（微信小程序要求完整四件套；render-then-redirect 视觉空白期）
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readProfileTs(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'profile', 'index.ts'),
    'utf-8',
  );
}

function readProfileWxml(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'profile', 'index.wxml'),
    'utf-8',
  );
}

describe('PR-3 commit-1 · profile 旧页 redirect stub（不死循环）', () => {
  it('onLoad 调 wx.reLaunch 跳 /pages/profile-new/index（不用 navigateTo 防回退循环）', () => {
    const ts = readProfileTs();
    expect(ts).toContain('onLoad()');
    // 必须用 reLaunch 而非 navigateTo
    expect(ts).toContain("wx.reLaunch({ url: '/pages/profile-new/index' })");
    expect(ts).not.toMatch(/wx\.navigateTo\(\s*\{\s*url:\s*['"]\/pages\/profile-new\/index['"]/);
    // wxml 存在（小程序要求完整四件套）
    const wxml = readProfileWxml();
    expect(wxml).toContain('<view');
  });
});