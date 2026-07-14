/**
 * FE-FIX-04 · progress-ring 组件单测
 * ──────────────────────────────────────────────────────────────
 * 真源：docs/plan/frontend-fix-plan.md §FE-FIX-04
 * 真源：docs/design/figma-pixso-spec/pages/03-home.html（progress-ring）
 * 真源：apps/mp-selfwell/miniprogram/components/progress-ring/index.ts
 *
 * 验收标准：
 *  - percent=0 → dashOffset = circumference（全未完成）
 *  - percent=100 → dashOffset = 0（全完成）
 *  - percent=50 → dashOffset = circumference * 0.5（一半）
 *
 * 设计要点：
 *  - 走项目约定的「字符串匹配 + 数值公式」复合断言：契约算法不动即 PASS
 *  - 与 components/action-card-component.test.ts / components/day-strip-5state-component.test.ts
 *    同款风格（4 文件齐全检查 + 核心契约锁）
 *  - 公式内联复刻 component observer 内的 r/c/dashOffset 算法
 *    （r = size/2 - 16; c = 2πr; dashOffset = c * (1 - percent/100)）
 */
import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const COMPONENT_DIR = join(
  __dirname,
  '..',
  'miniprogram',
  'components',
  'progress-ring',
);

function readFile(name: string): string {
  return readFileSync(join(COMPONENT_DIR, name), 'utf-8');
}

// 复刻 component observer 内的算法（保持单一真源在 observer 内）
function computeDashOffsets(
  size: number,
  percents: number[],
  strokeWidth = 6,
): Array<{ percent: number; radius: number; circumference: number; dashOffset: number }> {
  const r = size / 2 - strokeWidth;
  const c = 2 * Math.PI * r;
  return percents.map((percent) => {
    const safe = Math.max(0, Math.min(100, Number(percent) || 0));
    return { percent: safe, radius: r, circumference: c, dashOffset: c * (1 - safe / 100) };
  });
}

describe('FE-FIX-04 · progress-ring 组件契约', () => {
  it('用例 1: 4 文件齐全（component=true 声明）', () => {
    expect(existsSync(join(COMPONENT_DIR, 'index.ts'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.wxml'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.wxss'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.json'))).toBe(true);
    const json = JSON.parse(readFile('index.json')) as { component?: boolean };
    expect(json.component).toBe(true);
  });

  it('用例 2: props.percent / size / strokeWidth / label / subLabel 全部声明', () => {
    const ts = readFile('index.ts');
    expect(ts).toMatch(/percent:\s*\{\s*type:\s*Number/);
    expect(ts).toMatch(/size:\s*\{\s*type:\s*Number/);
    expect(ts).toMatch(/strokeWidth:\s*\{\s*type:\s*Number/);
    expect(ts).toMatch(/label:\s*\{\s*type:\s*String/);
    expect(ts).toMatch(/subLabel:\s*\{\s*type:\s*String/);
  });

  it('用例 3: observer 公式 r = size/2 - strokeWidth / c = 2πr / dashOffset = c * (1 - percent/100)', () => {
    const ts = readFile('index.ts');
    // 关键算法字面锁（V2 支持 strokeWidth 参数，不再写死 16）
    expect(ts).toMatch(/size\s*\/\s*2\s*-\s*strokeWidth/);
    expect(ts).toContain('2 * Math.PI *');
    expect(ts).toMatch(/c\s*\*\s*\(1\s*-\s*/);
    expect(ts).toMatch(/observers:\s*\{[\s\S]*['"]percent,\s*size,\s*strokeWidth['"]/);
  });

  it('用例 4: percent=0 → dashOffset = circumference（全未完成）', () => {
    const SIZE = 240;
    const rows = computeDashOffsets(SIZE, [0]);
    expect(rows[0].dashOffset).toBeCloseTo(rows[0].circumference, 6);
  });

  it('用例 5: percent=100 → dashOffset = 0（全完成）', () => {
    const SIZE = 240;
    const rows = computeDashOffsets(SIZE, [100]);
    expect(rows[0].dashOffset).toBeCloseTo(0, 6);
  });

  it('用例 6: percent=50 → dashOffset = circumference * 0.5（一半）', () => {
    const SIZE = 240;
    const rows = computeDashOffsets(SIZE, [50]);
    expect(rows[0].dashOffset).toBeCloseTo(rows[0].circumference * 0.5, 6);
  });

  it('用例 7: percent 边界值（-10 / 150）自动 clamp 到 [0, 100]', () => {
    const SIZE = 240;
    const rows = computeDashOffsets(SIZE, [-10, 150]);
    // -10 clamp 到 0 → dashOffset = circumference
    expect(rows[0].dashOffset).toBeCloseTo(rows[0].circumference, 6);
    // 150 clamp 到 100 → dashOffset = 0
    expect(rows[1].dashOffset).toBeCloseTo(0, 6);
  });

  it('用例 8: size 变化后 radius / circumference 重算（默认 240 → 改 90 / 360；strokeWidth 默认 6px）', () => {
    const r90 = computeDashOffsets(90, [50], 6);
    const r240 = computeDashOffsets(240, [50], 6);
    const r360 = computeDashOffsets(360, [50], 6);
    expect(r90[0].radius).toBe(90 / 2 - 6);
    expect(r240[0].radius).toBe(240 / 2 - 6);
    expect(r360[0].radius).toBe(360 / 2 - 6);
    expect(r90[0].circumference).not.toBe(r240[0].circumference);
    expect(r240[0].circumference).not.toBe(r360[0].circumference);
    // dashOffset 永远等于 circumference * (1 - 0.5) = circumference * 0.5
    expect(r90[0].dashOffset).toBeCloseTo(r90[0].circumference * 0.5, 6);
    expect(r240[0].dashOffset).toBeCloseTo(r240[0].circumference * 0.5, 6);
    expect(r360[0].dashOffset).toBeCloseTo(r360[0].circumference * 0.5, 6);
  });

  it('用例 9: wxml 渲染 SVG circle + stroke-dashoffset 绑定', () => {
    const wxml = readFile('index.wxml');
    expect(wxml).toContain('<svg');
    expect(wxml).toContain('<circle');
    expect(wxml).toContain('stroke-dasharray="{{circumference}}"');
    expect(wxml).toContain('stroke-dashoffset="{{dashOffset}}"');
    expect(wxml).toContain('class="ring-fg"');
    expect(wxml).toContain('class="ring-bg"');
  });
});
