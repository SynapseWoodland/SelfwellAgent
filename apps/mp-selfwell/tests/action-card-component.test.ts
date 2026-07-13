/**
 * PR-V2-A · action-card 组件契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：docs/spec/SPEC-M3-pages-v2-1to1-clone.md §3.1
 * 真源：docs/design/figma-pixso-spec/pages-v2/15i-butler-analyze-report-revised.html · .action-item
 *
 * 组件用途：
 *  - 操作卡：图标 + 名称 + meta + 箭头（点击触发 tap）
 *  - 与已有 task-card 的区别：task-card 是任务卡（带勾选），action-card 是操作卡（无勾选）
 *  - 复用页面：diagnosis-report-v2 (15i)、home (15b)、assistant-home、抽屉内列表
 *
 * 验收标准：
 *  AC-1 4 文件齐全
 *  AC-2 props: icon (emoji) / name / meta / bgClass / onTap
 *  AC-3 tap 事件触发 bind:tap {name}
 *  AC-4 WXSS 提供 6 种背景 class（mint/cream/peach/lavender/skin/gray）
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
  'action-card',
);

function readFile(name: string): string {
  return readFileSync(join(COMPONENT_DIR, name), 'utf-8');
}

describe('PR-V2-A · action-card 组件契约', () => {
  it('AC-1 4 文件齐全', () => {
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

  it('AC-2 props: icon / name / meta / bgClass 全部声明', () => {
    const ts = readFile('index.ts');
    expect(ts).toMatch(/icon\s*:\s*String/);
    expect(ts).toMatch(/name\s*:\s*String/);
    expect(ts).toMatch(/meta\s*:\s*String/);
    expect(ts).toMatch(/bgClass\s*:\s*String/);
  });

  it('AC-3 WXML bindtap 触发 tap 事件', () => {
    const wxml = readFile('index.wxml');
    expect(wxml).toMatch(/bindtap=/);
    expect(wxml).toMatch(/\{\{icon\}\}/);
    expect(wxml).toMatch(/\{\{name\}\}/);
  });

  it('AC-3 TS 暴露 tap 事件 payload {name}', () => {
    const ts = readFile('index.ts');
    expect(ts).toMatch(/triggerEvent\(['"]tap['"]/);
    expect(ts).toMatch(/name:\s*string/);
  });

  it('AC-4 WXSS 至少 3 种 bgClass（mint/cream/peach）', () => {
    const wxss = readFile('index.wxss');
    expect(wxss).toMatch(/\.bg-mint/);
    expect(wxss).toMatch(/\.bg-cream/);
    expect(wxss).toMatch(/\.bg-peach/);
  });

  it('AC-5 颜色全部用 design token，无硬编码 hex', () => {
    const wxss = readFile('index.wxss');
    expect(wxss).toMatch(/var\(--color-/);
    expect(wxss).not.toMatch(/background:\s*#[A-Fa-f0-9]{3,6}/);
  });
});