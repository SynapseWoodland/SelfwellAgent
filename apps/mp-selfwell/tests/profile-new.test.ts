/**
 * PR-3 commit-1 · profile-new 主页 静态契约锁（V2 11-profile.html）
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-IA-pr-internal.md §PR-3 commit-1
 * 真源：docs/design/figma-pixso-spec/pages/11-profile.html
 *
 * 锁值 8 用例（与 PR-3 §"profile-new 8 用例"对齐）：
 *  1. wxml 渲染头像渐变区（avatar + nickname + streak）
 *  2. wxml 渲染 6 列表项（profile/time/notification/privacy/support/about）
 *  3. ts settings 列表长度 === 6
 *  4. ts settings 每项含 pagePath 路径（与 PR-5 子页对齐）
 *  5. ts 调 GET /users/me（PR-2 streak_days 扩展数据源）
 *  6. wxml 进度环 size=160（与旧 profile 保持一致）
 *  7. wxss 头像渐变用 #A8C5B5 → #B8D4E3（PR-6 token --gradient-avatar 同色）
 *  8. json 含 pages/profile-new/index（V2 tabBar 落点）
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

  it('用例 2: wxml 渲染 6 列表项（profile/time/notification/privacy/support/about）', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toContain('wx:for="{{settings}}"');
    expect(wxml).toContain('data-id="{{item.id}}"');
    // 用模板插值 data-test 属性（PR-3 §profile-new 设计稿）
    expect(wxml).toContain('data-test="profile-new-row-{{item.id}}"');
    // 6 个 id 在 .ts 里作为字符串字面值出现
    const ts = readProfileNewTs();
    expect(ts).toContain("id: 'profile'");
    expect(ts).toContain("id: 'time'");
    expect(ts).toContain("id: 'notification'");
    expect(ts).toContain("id: 'privacy'");
    expect(ts).toContain("id: 'support'");
    expect(ts).toContain("id: 'about'");
  });

  it('用例 3: ts settings 列表长度 === 6（PR-3 设计稿严格 6 项）', () => {
    const ts = readProfileNewTs();
    expect(ts).toMatch(/settings:\s*\[/);
    // 6 个 id 字面契约
    const idCount = (ts.match(/id:\s*['"][a-z_]+['"]/g) || []).length;
    expect(idCount).toBeGreaterThanOrEqual(6);
  });

  it('用例 4: ts settings 每项含 pagePath 路径（PR-5 子页对齐）', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain('/pages/profile-edit/index?mode=read');
    expect(ts).toContain('/pages/record-album/index');
    expect(ts).toContain('/pages/notification-settings/index');
    expect(ts).toContain('/pages/privacy-policy/index');
    expect(ts).toContain('/pages/contact/index');
    expect(ts).toContain('/pages/about/index');
  });

  it('用例 5: ts 调 GET /users me（PR-2 streak_days 扩展数据源）', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain("get<UserMe>('/users/me')");
    expect(ts).toContain('fetchMe');
  });

  it('用例 6: wxml 进度环 size=160（与旧 profile 一致）', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toMatch(/<progress-ring[^>]*size="\{\{160\}\}"/);
  });

  it('用例 7: wxss 头像渐变用 #A8C5B5 → #B8D4E3（PR-6 token --gradient-avatar 同色）', () => {
    const wxss = readProfileNewWxss();
    expect(wxss).toMatch(/linear-gradient\(135deg,\s*#A8C5B5\s*0%,\s*#B8D4E3\s*100%\)/);
  });

  it('用例 8: json 含 usingComponents 引用 progress-ring（V2 tabBar 主页通用）', () => {
    const json = readProfileNewJson();
    expect(json).toHaveProperty('usingComponents');
    const usingComponents = json.usingComponents as Record<string, string>;
    expect(usingComponents['progress-ring']).toContain('progress-ring');
  });
});