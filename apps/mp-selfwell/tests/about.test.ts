/**
 * PR-5 · about 子页契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-unified-parent.md §2.5 + plans/v2-IA-pr-internal.md §PR-5
 *
 * 锁值 5 用例：
 *  1. 路由注册
 *  2. 四件套完整
 *  3. TS 用 wx.getAccountInfoSync 取版本号
 *  4. TS 用 wx.getAppBaseInfo / getSystemInfoSync 取系统信息
 *  5. json.usingComponents 不含 tabbar + 文案锁
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readPage(file: string): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'about', file),
    'utf-8',
  );
}

function readAppJson(): { pages: string[] } {
  const raw = readFileSync(
    join(__dirname, '..', 'miniprogram', 'app.json'),
    'utf-8',
  );
  return JSON.parse(raw);
}

describe('PR-5 · about 子页', () => {
  it('用例 1: app.json 注册 pages/about/index', () => {
    const app = readAppJson();
    expect(app.pages).toContain('pages/about/index');
  });

  it('用例 2: 子页四件套完整', () => {
    for (const f of ['index.ts', 'index.wxml', 'index.wxss', 'index.json']) {
      const content = readPage(f);
      expect(content.length, `${f} 文件非空`).toBeGreaterThan(0);
    }
  });

  it('用例 3: TS 用 wx.getAccountInfoSync 取 miniProgram.version', () => {
    const ts = readPage('index.ts');
    expect(ts).toContain('wx.getAccountInfoSync');
    // 字段路径：miniProgram → version（可选链）
    expect(ts).toMatch(/miniProgram\??\.version/);
  });

  it('用例 4: TS 用 wx.getAppBaseInfo / getSystemInfoSync 取系统信息', () => {
    const ts = readPage('index.ts');
    const usesAppBaseInfo = ts.includes('wx.getAppBaseInfo');
    const usesGetSystemInfo = ts.includes('wx.getSystemInfoSync');
    expect(
      usesAppBaseInfo || usesGetSystemInfo,
      'TS 必须用 wx.getAppBaseInfo 或 wx.getSystemInfoSync 取系统信息',
    ).toBe(true);
    // 系统信息字段必须写入 data
    expect(ts).toContain('system');
    expect(ts).toContain('systemVersion');
    expect(ts).toContain('wechatVersion');
  });

  it('用例 5: json.usingComponents 不含 tabbar + 锁值导航栏 + WXML 锁值', () => {
    const json = readPage('index.json');
    const parsed = JSON.parse(json);
    expect(parsed.usingComponents ?? {}).not.toHaveProperty('tabbar');
    expect(parsed.navigationBarTitleText).toBe('关于自愈');
    // WXML 必须含 Selfwell 自愈 标题
    const wxml = readPage('index.wxml');
    expect(wxml).toContain('Selfwell 自愈');
    expect(wxml).toContain('应用版本');
    expect(wxml).toContain('检查更新');
  });
});