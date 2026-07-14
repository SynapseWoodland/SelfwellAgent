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
    expect(ts).toContain('tabs');
    expect(ts).toContain('active');
    expect(ts).toContain('size');
  });

  it('AC-3 WXML 用 wx:for 渲染每个 tab', () => {
    const wxml = readFile('index.wxml');
    expect(wxml).toContain('wx:for');
    expect(wxml).toContain('wx:key');
    expect(wxml).toContain('is-active');
  });

  it('AC-4 WXML bindtap 触发 change 事件，TS 暴露事件 payload', () => {
    const wxml = readFile('index.wxml');
    expect(wxml).toContain('onTap');
    const ts = readFile('index.ts');
    expect(ts).toContain('change');
    expect(ts).toContain('index');
    expect(ts).toContain('label');
  });

  it('AC-5 WXSS active 态使用 token 化背景 + 阴影', () => {
    const wxss = readFile('index.wxss');
    expect(wxss).toContain('is-active');
    expect(wxss).toContain('bg-card');
    expect(wxss).toContain('box-shadow');
  });
});