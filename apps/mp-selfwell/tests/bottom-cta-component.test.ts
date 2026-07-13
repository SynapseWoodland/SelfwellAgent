/**
 * PR-V2-A · bottom-cta 组件契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：docs/spec/SPEC-M3-pages-v2-1to1-clone.md §3.1
 * 真源：docs/design/figma-pixso-spec/pages-v2/15g/15h/15i · .bottom-cta
 *
 * 组件用途：
 *  - 底部 CTA：单按钮 / 双按钮（primary + secondary outline）/ 三按钮
 *  - 复用页面：diagnosis-transition (15g)、plan-delivery (15h)、diagnosis-report-v2 (15i)、
 *             recall-compare (15e)、plan-tabs (15f)
 *
 * 验收标准：
 *  AC-1 4 文件齐全
 *  AC-2 props: primary (text) / secondary (text) / sticky (Boolean)
 *  AC-3 WXML 在 sticky=true 时输出 position:fixed 样式
 *  AC-4 WXSS 定义 primary / outline / ghost 三种按钮样式
 *  AC-5 颜色 token 化
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const COMPONENT_DIR = join(
  __dirname,
  '..',
  'miniprogram',
  'components',
  'bottom-cta',
);

function readFile(name: string): string {
  return readFileSync(join(COMPONENT_DIR, name), 'utf-8');
}

describe('PR-V2-A · bottom-cta 组件契约', () => {
  it('AC-1 4 文件齐全', () => {
    expect(existsSync(join(COMPONENT_DIR, 'index.ts'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.wxml'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.wxss'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.json'))).toBe(true);
  });

  it('AC-2 props: primary / secondary / sticky 全部声明', () => {
    const ts = readFile('index.ts');
    expect(ts).toMatch(/primary\s*:\s*String/);
    expect(ts).toMatch(/secondary\s*:\s*String/);
    expect(ts).toMatch(/sticky\s*:\s*Boolean/);
  });

  it('AC-3 WXML 在 sticky=true 时渲染 fixed 样式', () => {
    const wxml = readFile('index.wxml');
    expect(wxml).toMatch(/class="bottom-cta \{\{sticky \? 'is-sticky' : ''\}\}"/);
    // 或显式 style
    expect(wxml).toMatch(/position:\s*\{\{sticky \? 'fixed' : 'absolute'\}\}/);
  });

  it('AC-3 WXML 渲染 primary 与 secondary 两个按钮（有则显示）', () => {
    const wxml = readFile('index.wxml');
    expect(wxml).toMatch(/wx:if="\{\{primary\}\}"/);
    expect(wxml).toMatch(/wx:if="\{\{secondary\}\}"/);
  });

  it('AC-4 WXSS 定义 primary / outline 三种按钮样式', () => {
    const wxss = readFile('index.wxss');
    expect(wxss).toMatch(/\.cta-primary/);
    expect(wxss).toMatch(/\.cta-outline/);
  });

  it('AC-4 WXSS 含 is-sticky 状态（position: fixed）', () => {
    const wxss = readFile('index.wxss');
    expect(wxss).toMatch(/\.is-sticky\s*\{[^}]*position:\s*fixed/);
  });

  it('AC-5 颜色 token 化', () => {
    const wxss = readFile('index.wxss');
    expect(wxss).toMatch(/var\(--color-/);
    expect(wxss).not.toMatch(/background:\s*#A8C5B5/);
  });
});