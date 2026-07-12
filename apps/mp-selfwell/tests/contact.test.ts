/**
 * PR-5 · contact 子页契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-unified-parent.md §2.5 + plans/v2-IA-pr-internal.md §PR-5
 *
 * 锁值 5 用例：
 *  1. 路由注册
 *  2. 四件套完整
 *  3. 邮箱 / 微信字段锁（含默认值）
 *  4. FAQ 4 条锁 + 折叠交互
 *  5. 二维码占位元素 + json.usingComponents 不含 tabbar
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readPage(file: string): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'contact', file),
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

describe('PR-5 · contact 子页', () => {
  it('用例 1: app.json 注册 pages/contact/index', () => {
    const app = readAppJson();
    expect(app.pages).toContain('pages/contact/index');
  });

  it('用例 2: 子页四件套完整', () => {
    for (const f of ['index.ts', 'index.wxml', 'index.wxss', 'index.json']) {
      const content = readPage(f);
      expect(content.length, `${f} 文件非空`).toBeGreaterThan(0);
    }
  });

  it('用例 3: TS 含邮箱 + 微信号常量 + setClipboardData 复制方法', () => {
    const ts = readPage('index.ts');
    // 邮箱 + 微信 ID 必须有默认值
    expect(ts).toContain('selfwell@example.com');
    expect(ts).toContain('selfwell_helper');
    // 复制方法
    expect(ts).toContain('wx.setClipboardData');
    expect(ts).toContain('onCopyEmail');
    expect(ts).toContain('onCopyWechat');
  });

  it('用例 4: FAQ 4 条锁（含标题 4 问） + 折叠交互', () => {
    const ts = readPage('index.ts');
    expect(ts).toContain('如何修改档案');
    expect(ts).toContain('打卡漏了一天怎么办');
    expect(ts).toContain('21 天方案可以重新生成吗');
    expect(ts).toContain('如何注销账号');
    // 折叠交互
    expect(ts).toContain('onTapFaq');
    expect(ts).toContain('expandedIndex');
    // WXML 渲染 faqs
    const wxml = readPage('index.wxml');
    expect(wxml).toContain('wx:for="{{faqs}}"');
  });

  it('用例 5: 二维码占位元素存在 + json.usingComponents 不含 tabbar', () => {
    const wxml = readPage('index.wxml');
    expect(wxml).toContain('ct-qrcode-placeholder');
    expect(wxml).toContain('二维码占位');
    const json = readPage('index.json');
    const parsed = JSON.parse(json);
    expect(parsed.usingComponents ?? {}).not.toHaveProperty('tabbar');
    expect(parsed.navigationBarTitleText).toBe('联系客服');
  });
});