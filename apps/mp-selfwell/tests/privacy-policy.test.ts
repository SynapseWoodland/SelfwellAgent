/**
 * PR-5 · privacy-policy 子页契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-unified-parent.md §2.5 + plans/v2-IA-pr-internal.md §PR-5
 *
 * 锁值 5 用例：
 *  1. 路由注册
 *  2. 四件套完整
 *  3. 不调后端（静态 markdown）
 *  4. 6 段策略锁：信息收集 / 用途 / 存储 / 共享 / 用户权利 / 注销
 *  5. json.usingComponents 不含 tabbar
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readPage(file: string): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'privacy-policy', file),
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

describe('PR-5 · privacy-policy 子页', () => {
  it('用例 1: app.json 注册 pages/privacy-policy/index', () => {
    const app = readAppJson();
    expect(app.pages).toContain('pages/privacy-policy/index');
  });

  it('用例 2: 子页四件套完整（ts/wxml/wxss/json）', () => {
    for (const f of ['index.ts', 'index.wxml', 'index.wxss', 'index.json']) {
      const content = readPage(f);
      expect(content.length, `${f} 文件非空`).toBeGreaterThan(0);
    }
  });

  it('用例 3: TS 不调后端（纯静态 markdown 渲染）', () => {
    const ts = readPage('index.ts');
    expect(ts).not.toContain("get<");
    expect(ts).not.toContain("post<");
    expect(ts).not.toContain("put<");
    expect(ts).not.toContain('wx.request');
  });

  it('用例 4: 6 段策略锁（信息收集 / 用途 / 存储 / 共享 / 用户权利 / 注销）', () => {
    const ts = readPage('index.ts');
    expect(ts).toContain('我们收集的信息');
    expect(ts).toContain('我们如何使用这些信息');
    expect(ts).toContain('存储与加密');
    expect(ts).toContain('共享与披露');
    expect(ts).toContain('你的权利');
    expect(ts).toContain('注销与冷静期');
    // 15 天冷静期
    expect(ts).toContain('15 天');
  });

  it('用例 5: json.usingComponents 不含 tabbar + 顶部版本号', () => {
    const json = readPage('index.json');
    const parsed = JSON.parse(json);
    expect(parsed.usingComponents ?? {}).not.toHaveProperty('tabbar');
    // navigationBarTitleText 锁
    expect(parsed.navigationBarTitleText).toBe('隐私政策');
  });
});