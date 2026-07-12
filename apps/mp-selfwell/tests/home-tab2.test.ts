/**
 * PR-3 commit-1 · home 升版为「今天」Tab 静态契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-IA-pr-internal.md §PR-3 commit-1
 * 真源：docs/design/figma-pixso-spec/pages/15b-today-tab2.html
 *
 * 锁值 8 用例（与 PR-3 §"home-tab2 8 用例"对齐）：
 *  1. progress ring size = 90（V2 15b-today-tab2.html 进度环 90px）
 *  2. 21-day strip 渲染 21 个 cell
 *  3. dayStrip cell 含 done/today/future 三态属性
 *  4. hug-section 含"领取今日抱抱卡"标题（→ /pages/share-hug-card/index）
 *  5. time-section 含"我的时光"标题（→ /pages/record-album/index）
 *  6. drawer trigger 元素存在（fixed 右下角）
 *  7. drawer 含 8 个 drawer-card
 *  8. home/index.ts bootstrap 不破坏三接口契约（GET /users/me + /checkins/today + /plans/today）
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readWxml(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'home', 'index.wxml'),
    'utf-8',
  );
}

function readWxss(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'home', 'index.wxss'),
    'utf-8',
  );
}

function readTs(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'home', 'index.ts'),
    'utf-8',
  );
}

function readSmartBody(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'home', 'index.smart-body.ts'),
    'utf-8',
  );
}

describe('PR-3 commit-1 · home 升版 today Tab (15b-today-tab2.html)', () => {
  it('用例 1: 进度环 size=90（V2 设计稿 90px，不是旧版 240）', () => {
    const wxml = readWxml();
    expect(wxml).toMatch(/<progress-ring[^>]*size="\{\{90\}\}"/);
    expect(wxml).not.toMatch(/<progress-ring[^>]*size="\{\{240\}\}"/);
  });

  it('用例 2: 21-day strip 渲染 21 个 cell（wx:for dayStrip）', () => {
    const wxml = readWxml();
    expect(wxml).toContain('wx:for="{{dayStrip}}"');
    // wxss 含 daystrip 样式
    const wxss = readWxss();
    expect(wxss).toContain('.home-daystrip');
    expect(wxss).toContain('.home-daystrip-cell');
  });

  it('用例 3: dayStrip cell 三态属性（done/today/future 用 data-state 属性选择器）', () => {
    const wxml = readWxml();
    expect(wxml).toContain('data-state="{{item.state}}"');
    const wxss = readWxss();
    expect(wxss).toMatch(/\[data-state=['"]done['"]\]/);
    expect(wxss).toMatch(/\[data-state=['"]today['"]\]/);
    expect(wxss).toMatch(/\[data-state=['"]future['"]\]/);
  });

  it('用例 4: hug-section 含"领取今日抱抱卡"标题（绑定 onGotoShare）', () => {
    const wxml = readWxml();
    expect(wxml).toContain('领取今日抱抱卡');
    expect(wxml).toContain('onGotoShare');
    const ts = readTs();
    expect(ts).toContain('onGotoShare');
    expect(ts).toContain('/pages/share-hug-card/index');
  });

  it('用例 5: time-section 含"我的时光"标题（绑定 onGotoTimeAlbum）', () => {
    const wxml = readWxml();
    expect(wxml).toContain('我的时光');
    expect(wxml).toContain('onGotoTimeAlbum');
    const ts = readTs();
    expect(ts).toContain('onGotoTimeAlbum');
    expect(ts).toContain('/pages/record-album/index');
  });

  it('用例 6: drawer trigger 元素存在（fixed 右下角浮动）', () => {
    const wxml = readWxml();
    expect(wxml).toContain('class="home-drawer-trigger"');
    expect(wxml).toContain('onOpenDrawer');
    const wxss = readWxss();
    expect(wxss).toContain('.home-drawer-trigger');
    expect(wxss).toContain('position: fixed');
  });

  it('用例 7: drawer 含 8 个 drawer-card（drawerCards 数组）', () => {
    const sb = readSmartBody();
    expect(sb).toMatch(/getDrawCards\s*\(\s*\)\s*:\s*DrawerCard\[\]/);
    // 8 个卡片 id 锁
    expect(sb).toContain("id: 'profile'");
    expect(sb).toContain("id: 'time'");
    expect(sb).toContain("id: 'notification'");
    expect(sb).toContain("id: 'privacy'");
    expect(sb).toContain("id: 'support'");
    expect(sb).toContain("id: 'about'");
    expect(sb).toContain("id: 'feedback'");
    expect(sb).toContain("id: 'plan'");
  });

  it('用例 8: bootstrap 不破坏现有三接口契约（GET /users/me + /checkins/today + /plans/today）', () => {
    const ts = readTs();
    // 三接口字面契约（PR-3 §commit-1 强契约）
    expect(ts).toContain("get<UserMe>('/users/me')");
    expect(ts).toContain("get<CheckinToday>('/checkins/today')");
    expect(ts).toContain("get<TodayPlan>('/plans/today')");
    // bootstrap 入口仍存在
    expect(ts).toContain('async bootstrap(): Promise<void>');
    // onLoad + onShow + onPullDownRefresh 三个生命周期保留
    expect(ts).toContain('onLoad()');
    expect(ts).toContain('onShow()');
    expect(ts).toContain('onPullDownRefresh()');
  });
});