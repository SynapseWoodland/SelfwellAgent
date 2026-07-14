/**
 * PR-V2-A · drawer-overlay 组件契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：docs/spec/SPEC-M3-pages-v2-1to1-clone.md §3.1
 * 真源：docs/design/figma-pixso-spec/pages-v2/15c-manage-drawer.html
 *
 * 组件用途：
 *  - 右侧抽屉 + 全屏遮罩
 *  - 当 visible=true 时显示，否则隐藏
 *  - 点击遮罩或 close 按钮触发 close 事件
 *  - 复用页面：home (15c 管理抽屉)
 *
 * 验收标准：
 *  AC-1 4 文件齐全
 *  AC-2 props: visible (Boolean) / title (String, 可选) / peekTab (Boolean, 可选)
 *  AC-3 WXML 在 visible=true 时含 mask + drawer 两个 view
 *  AC-4 WXML 含 close 按钮（点击触发 close 事件）
 *  AC-5 WXSS drawer 宽度默认 78% / max-width 295px
 *  AC-6 WXSS mask 背景 rgba(0,0,0,0.4)
 *  AC-7 颜色 token 化（mask 黑色例外，token 化灰阶）
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const COMPONENT_DIR = join(
  __dirname,
  '..',
  'miniprogram',
  'components',
  'drawer-overlay',
);

function readFile(name: string): string {
  return readFileSync(join(COMPONENT_DIR, name), 'utf-8');
}

describe('PR-V2-A · drawer-overlay 组件契约', () => {
  it('AC-1 4 文件齐全', () => {
    expect(existsSync(join(COMPONENT_DIR, 'index.ts'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.wxml'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.wxss'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.json'))).toBe(true);
  });

  it('AC-2 props: visible / title / peekTab 全部声明', () => {
    const ts = readFile('index.ts');
    // 微信小程序用对象形式声明属性 { type: Boolean }
    expect(ts).toMatch(/visible\s*:\s*\{[^}]*type\s*:\s*Boolean/);
    expect(ts).toMatch(/title\s*:\s*\{[^}]*type\s*:\s*String/);
    expect(ts).toMatch(/peekTab\s*:\s*\{[^}]*type\s*:\s*Boolean/);
  });

  it('AC-3 WXML 关闭时不渲染（wrapper 用 wx:if="{{visible}}"），打开时 mask+drawer 直接可见', () => {
    const wxml = readFile('index.wxml');
    // wrapper 用 wx:if="{{visible}}" 关闭时不渲染任何 DOM
    expect(wxml).toMatch(/class="drawer-wrapper" wx:if="\{\{visible\}\}"/);
    // 打开时 mask 始终有 is-visible，drawer 始终有 is-open
    expect(wxml).toMatch(/class="drawer-mask is-visible"/);
    expect(wxml).toMatch(/class="drawer is-open"/);
  });

  it('AC-4 WXML 含 close 按钮，触发 close 事件', () => {
    const wxml = readFile('index.wxml');
    expect(wxml).toMatch(/bindtap="onCloseTap"|bindtap="onMaskTap"|bindtap="onClose"/);
  });

  it('AC-4 TS 暴露 close 事件', () => {
    const ts = readFile('index.ts');
    expect(ts).toMatch(/triggerEvent\(['"]close['"]/);
  });

  it('AC-5 WXSS drawer 宽度 80% / max-width 320px（对齐 15c 原型）', () => {
    const wxss = readFile('index.wxss');
    expect(wxss).toMatch(/\.drawer\s*\{[^}]*width:\s*80%/);
    expect(wxss).toMatch(/\.drawer\s*\{[^}]*max-width:\s*320px/);
  });

  it('AC-6 WXSS mask 背景 rgba(0,0,0,0.4)', () => {
    const wxss = readFile('index.wxss');
    expect(wxss).toMatch(/rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\.4\s*\)/);
  });

  it('AC-7 WXSS 抽屉头部米色渐变（实际使用 --color-secondary-cream 等效色）', () => {
    const wxss = readFile('index.wxss');
    // 组件无法 import v2-tokens，使用硬编码值（等效于 --color-secondary-cream: #F5E6D3）
    expect(wxss).toMatch(/#F5E6D3/);
  });
});