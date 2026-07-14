/**
 * PR-V2-C · home 今天 Tab 静态契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：docs/design/figma-pixso-spec/pages-v2/15b-today-tab2.html
 *
 * 8 验收用例（V2 15b）：
 *  1. progress-ring size=90px + variant=gradient
 *  2. day-strip-5state 组件渲染，days="{{dayStrip}}"
 *  3. dayStrip 5 态状态（completed/today/missed/future/feedback）
 *  4. hug-section 含抱抱卡入口（绑定 onGotoShare）
 *  5. time-section 含我的时光入口（绑定 onGotoTimeAlbum）
 *  6. drawer-overlay 组件替代 inline drawer（WXML）
 *  7. drawer 抽屉内容含管理卡片 grid
 *  8. bootstrap 三接口契约保留
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

describe('PR-V2-C · home 今天 Tab (15b-today-tab2.html)', () => {
  it('用例 1: progress-ring size=90px + variant=gradient', () => {
    const wxml = readWxml();
    expect(wxml).toMatch(/size="\{\{90\}\}"/);
    expect(wxml).toMatch(/variant="gradient"/);
  });

  it('用例 2: day-strip-5state 组件渲染，days="{{dayStrip}}"', () => {
    const wxml = readWxml();
    expect(wxml).toContain('day-strip-5state');
    expect(wxml).toContain('days="{{dayStrip}}"');
  });

  it('用例 3: dayStrip 5 态（completed/today/missed/future/feedback）', () => {
    const ts = readTs();
    expect(ts).toContain("'completed'");
    expect(ts).toContain("'today'");
    expect(ts).toContain("'missed'");
    expect(ts).toContain("'future'");
    expect(ts).toContain("'feedback'");
  });

  it('用例 4: hug-section 含抱抱卡入口（绑定 onGotoShare）', () => {
    const wxml = readWxml();
    expect(wxml).toContain('hug-section');
    expect(wxml).toContain('onGotoShare');
    const ts = readTs();
    expect(ts).toContain('onGotoShare');
    expect(ts).toContain('/pages/share-hug-card/index');
  });

  it('用例 5: time-section 含我的时光入口（绑定 onGotoTimeAlbum）', () => {
    const wxml = readWxml();
    expect(wxml).toContain('time-section');
    expect(wxml).toContain('onGotoTimeAlbum');
    const ts = readTs();
    expect(ts).toContain('onGotoTimeAlbum');
    expect(ts).toContain('/pages/record-album/index');
  });

  it('用例 6: drawer-overlay 组件替代 inline drawer（WXML）', () => {
    const wxml = readWxml();
    expect(wxml).toContain('drawer-overlay');
    expect(wxml).toContain('bind:close="onCloseDrawer"');
    expect(wxml).toContain('visible="{{drawerOpen}}"');
  });

  it('用例 7: drawer 抽屉内容含管理卡片 grid + 底部进度块', () => {
    const wxml = readWxml();
    expect(wxml).toContain('home-drawer-grid');
    expect(wxml).toContain('home-drawer-progress');
    expect(wxml).toContain('onTapDrawerCard');
  });

  it('用例 8: bootstrap 三接口契约保留', () => {
    const ts = readTs();
    expect(ts).toContain("get<UserMe>('/users/me')");
    expect(ts).toContain("get<CheckinToday>('/checkins/today')");
    expect(ts).toContain("get<TodayPlan>('/plans/today')");
    expect(ts).toContain('async bootstrap(): Promise<void>');
    expect(ts).toContain('onLoad()');
    expect(ts).toContain('onShow()');
    expect(ts).toContain('onPullDownRefresh()');
  });
});
