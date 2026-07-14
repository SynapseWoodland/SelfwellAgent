/**
 * PR-V2-A · day-strip-5state 组件契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：docs/spec/SPEC-M3-pages-v2-1to1-clone.md §3.1
 * 真源：docs/design/figma-pixso-spec/pages-v2/15b-today-tab2.html · .day-strip-item
 * 真源：docs/design/figma-pixso-spec/pages-v2/15f-plan-tabs-5state.html · .day-cell
 *
 * 组件用途：
 *  - 5 态日条 / 日格：completed / today / missed / future / feedback
 *  - 复用页面：home (15b)、plan-tabs (15f)、profile-new
 *
 * 验收标准（与 SPEC-M3 FR-V2-A-02 对齐）：
 *  AC-1 组件 4 文件齐全（index.ts / index.wxml / index.wxss / index.json）
 *  AC-2 WXML 含 data-state 属性绑定
 *  AC-3 5 状态对应 5 个 CSS class（completed / today / missed / future / feedback）
 *  AC-4 props: days 数组、activeIndex（高亮选中态）、compact（紧凑模式）
 *  AC-5 事件：bind:select 触发 {index, day}
 *  AC-6 颜色全部用 design token（无硬编码 #A8C5B5 等）
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const COMPONENT_DIR = join(
  __dirname,
  '..',
  'miniprogram',
  'components',
  'day-strip-5state',
);

function readFile(name: string): string {
  return readFileSync(join(COMPONENT_DIR, name), 'utf-8');
}

describe('PR-V2-A · day-strip-5state 组件契约', () => {
  it('AC-1 4 文件齐全（ts/wxml/wxss/json）', () => {
    expect(existsSync(join(COMPONENT_DIR, 'index.ts'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.wxml'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.wxss'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.json'))).toBe(true);
  });

  it('AC-1 index.json 声明 component=true', () => {
    const json = JSON.parse(readFile('index.json')) as {
      component?: boolean;
    };
    expect(json.component).toBe(true);
  });

  it('AC-2 WXML 使用 data-state 属性绑定状态', () => {
    const wxml = readFile('index.wxml');
    expect(wxml).toMatch(/data-state=/);
    expect(wxml).toMatch(/state-{{/);
  });

  it('AC-3 WXML 渲染 5 状态 css class', () => {
    const wxml = readFile('index.wxml');
    expect(wxml).toMatch(/state-{{item\.state}}/);
    expect(wxml).toContain('{{item.dayNumber}}');
  });

  it('AC-3 WXSS 定义 5 个状态样式（属性选择器禁中文）', () => {
    const wxss = readFile('index.wxss');
    expect(wxss).toMatch(/\.day-strip-item\[data-state=['"]completed['"]\]/);
    expect(wxss).toMatch(/\.day-strip-item\[data-state=['"]today['"]\]/);
    expect(wxss).toMatch(/\.day-strip-item\[data-state=['"]missed['"]\]/);
    expect(wxss).toMatch(/\.day-strip-item\[data-state=['"]future['"]\]/);
    expect(wxss).toMatch(/\.day-strip-item\[data-state=['"]feedback['"]\]/);
  });

  it('AC-4 props: days / activeIndex / compact 全部声明', () => {
    const ts = readFile('index.ts');
    expect(ts).toMatch(/days\s*:\s*Array/);
    expect(ts).toMatch(/activeIndex\s*:\s*Number/);
    expect(ts).toMatch(/compact\s*:\s*Boolean/);
  });

  it('AC-5 TS 暴露 select 事件 payload {index, day}', () => {
    const ts = readFile('index.ts');
    expect(ts).toContain('select');
    expect(ts).toContain('index');
    expect(ts).toContain('DayItem');
  });

  it('AC-6 颜色全部用 design token，无硬编码 hex', () => {
    const wxss = readFile('index.wxss');
    expect(wxss).toMatch(/var\(--color-/);
    expect(wxss).not.toMatch(/#A8C5B5/);
    expect(wxss).not.toMatch(/#D4C5E2/);
    expect(wxss).not.toMatch(/#F0F2F5/);
  });
});
