/**
 * PR-3 commit-1 · profile-new 主页 静态契约锁（V2 11-profile.html）
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-IA-pr-internal.md §PR-3 commit-1
 * 真源：docs/design/figma-pixso-spec/pages/11-profile.html
 * §4.2.4 IA plan：6 列表项在抽屉里，不直接显示在主页
 *
 * 锁值 8 用例（与 PR-3 §"profile-new 8 用例"对齐）：
 *  1. wxml 渲染头像渐变区（avatar + nickname + streak）
 *  2. wxml 含 nav bar + 抽屉按钮（⋯）
 *  3. wxml 含抱抱卡区域 + 领取 CTA
 *  4. wxml 含 drawer-overlay，6 项菜单在抽屉内
 *  5. ts settings 列表长度 === 6（含 drawerVisible 状态）
 *  6. ts settings 每项含 pagePath 路径（与 PR-5 子页对齐）
 *  7. ts 含 drawer 控制方法（onOpenDrawer / onCloseDrawer / onDrawerNav）
 *  8. json 含 usingComponents 引用 drawer-overlay + progress-ring
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readProfileNewJson(): Record<string, unknown> {
  const raw = readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'profile-new', 'index.json'),
    'utf-8',
  );
  return JSON.parse(raw) as Record<string, unknown>;
}

function readProfileNewWxml(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'profile-new', 'index.wxml'),
    'utf-8',
  );
}

function readProfileNewWxss(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'profile-new', 'index.wxss'),
    'utf-8',
  );
}

function readProfileNewTs(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'profile-new', 'index.ts'),
    'utf-8',
  );
}

describe('PR-3 commit-1 · profile-new 主页（V2 11-profile.html）', () => {
  it('用例 1: wxml 渲染头像渐变区（avatar + nickname + streak）', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toContain('class="profile-new-avatar"');
    expect(wxml).toContain('class="profile-new-nickname"');
    expect(wxml).toContain('class="profile-new-streak"');
    expect(wxml).toContain('已坚持 {{streak}} 天');
  });

  it('用例 2: wxml 含 nav bar + 抽屉按钮（⋯）', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toContain('class="profile-new-nav"');
    expect(wxml).toContain('class="profile-new-nav-more"');
    expect(wxml).toContain('bindtap="onOpenDrawer"');
  });

  it('用例 3: wxml 含抱抱卡区域 + 领取 CTA', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toContain('class="profile-new-hugs"');
    expect(wxml).toContain('class="profile-new-cta-btn"');
    expect(wxml).toContain('领取抱抱卡');
  });

  it('用例 4: wxml 含 drawer-overlay，6 项菜单在抽屉内', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toContain('<drawer-overlay');
    expect(wxml).toContain('visible="{{drawerVisible}}"');
    expect(wxml).toContain('bind:close="onCloseDrawer"');
    expect(wxml).toContain('wx:for="{{settings}}"');
    expect(wxml).toContain('bindtap="onDrawerNav"');
    // 6 个 id 字面在 TS 中（动态绑定 data-id="{{item.id}}"）
    const ts = readProfileNewTs();
    expect(ts).toContain("id: 'profile'");
    expect(ts).toContain("id: 'time'");
    expect(ts).toContain("id: 'notification'");
    expect(ts).toContain("id: 'privacy'");
    expect(ts).toContain("id: 'support'");
    expect(ts).toContain("id: 'about'");
  });

  it('用例 5: ts settings 列表含 6 项 + drawerVisible 状态', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain('drawerVisible');
    expect(ts).toMatch(/settings:\s*\[/);
    const idCount = (ts.match(/id:\s*['"][a-z_]+['"]/g) || []).length;
    expect(idCount).toBeGreaterThanOrEqual(6);
  });

  it('用例 6: ts settings 每项含 pagePath 路径（与 PR-5 子页对齐）', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain('/pages/profile-edit/index?mode=read');
    expect(ts).toContain('/pages/album/index');
    expect(ts).toContain('/pages/notification-settings/index');
    expect(ts).toContain('/pages/privacy-policy/index');
    expect(ts).toContain('/pages/contact/index');
    expect(ts).toContain('/pages/about/index');
  });

  it('用例 7: ts 含 drawer 控制方法（onOpenDrawer / onCloseDrawer / onDrawerNav）', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain('onOpenDrawer');
    expect(ts).toContain('onCloseDrawer');
    expect(ts).toContain('onDrawerNav');
  });

  it('用例 8: json 含 usingComponents 引用 drawer-overlay + progress-ring', () => {
    const json = readProfileNewJson();
    expect(json).toHaveProperty('usingComponents');
    const usingComponents = json.usingComponents as Record<string, string>;
    expect(usingComponents['progress-ring']).toContain('progress-ring');
    expect(usingComponents['drawer-overlay']).toContain('drawer-overlay');
  });
});
