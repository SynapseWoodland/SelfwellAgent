/**
 * PR-V2-A · tab-switcher 组件契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：docs/spec/SPEC-M3-pages-v2-1to1-clone.md §3.1
 * 真源：docs/design/figma-pixso-spec/pages-v2/15f-plan-tabs-5state.html · .tab-switcher
 *
 * 组件用途：
 *  - Tab 切换器（2/3 段）：底部胶囊容器 + 等分布局
 *  - 复用页面：plan-tabs (15f 5 态日历)、assistant-home 入口
 *
 * 验收标准：
 *  AC-1 4 文件齐全
 *  AC-2 props: tabs (Array<string>) / active (Number) / size ('sm' | 'md')
 *  AC-3 WXML 渲染 N 个 tab，active tab 加 is-active class
 *  AC-4 WXML tap 触发 change 事件 {index, label}
 *  AC-5 WXSS active 态背景 var(--bg-card) + box-shadow
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const COMPONENT_DIR = join(
  __dirname,
  '..',
  'miniprogram',
  'components',
  'tab-switcher',
);

function readFile(name: string): string {
  return readFileSync(join(COMPONENT_DIR, name), 'utf-8');
}

describe('PR-V2-A · tab-switcher 组件契约', () => {
  it('AC-1 4 文件齐全', () => {
    expect(existsSync(join(COMPONENT_DIR, 'index.ts'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.wxml'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.wxss'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.json'))).toBe(true);
  });

  it('AC-2 props: tabs / active / size 全部声明', () => {
    const ts = readFile('index.ts');
    expect(ts).toMatch(/tabs\s*:\s*Array/);
    expect(ts).toMatch(/active\s*:\s*Number/);
    expect(ts).toMatch(/size\s*:\s*String/);
  });

  it('AC-3 WXML 用 wx:for 渲染每个 tab', () => {
    const wxml = readFile('index.wxml');
    expect(wxml).toMatch(/wx:for="\{\{tabs\}\}"/);
    expect(wxml).toMatch(/wx:key/);
    expect(wxml).toMatch(/class="tab-switch \{\{index === active \? 'is-active' : ''\}\}"/);
  });

  it('AC-4 WXML bindtap 触发 change 事件，TS 暴露事件 payload', () => {
    const wxml = readFile('index.wxml');
    expect(wxml).toMatch(/bindtap="onTap"/);
    const ts = readFile('index.ts');
    expect(ts).toMatch(/triggerEvent\(['"]change['"]/);
    expect(ts).toMatch(/index:\s*number/);
    expect(ts).toMatch(/label:\s*string/);
  });

  it('AC-5 WXSS active 态使用 token 化背景 + 阴影', () => {
    const wxss = readFile('index.wxss');
    expect(wxss).toMatch(/\.is-active\s*\{/);
    expect(wxss).toMatch(/background:\s*var\(--bg-card\)/);
    expect(wxss).toMatch(/box-shadow/);
  });
});