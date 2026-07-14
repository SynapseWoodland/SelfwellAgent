/**
 * plan-delivery 静态契约锁
 * PR-V2-C · 对齐 15h-p03c-plan-delivery.html 原型
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const read = (name: string) =>
  readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'plan-delivery', name),
    'utf-8',
  );

describe('plan-delivery · 15h 原型对齐', () => {
  it('hero bounce 动画', () => {
    const wxss = read('index.wxss');
    expect(wxss).toContain('.plan-hero-icon');
    expect(wxss).toContain('animation: bounce');
    expect(wxss).toContain('@keyframes bounce');
  });

  it('bottom CTA 有两个按钮', () => {
    const wxss = read('index.wxss');
    expect(wxss).toContain('.btn-primary');
    expect(wxss).toContain('.btn-secondary');
    expect(wxss).toContain('.plan-cta');
    expect(wxss).toContain('position: fixed');
  });

  it('前 5 天预览 + phase 样式', () => {
    const ts = read('index.ts');
    expect(ts).toMatch(/days\.slice\(\s*0\s*,\s*5\s*\)/);
    const wxss = read('index.wxss');
    expect(wxss).toContain('.day-row.p1');
    expect(wxss).toContain('.day-row.p2');
    expect(wxss).toContain('.day-row.p3');
  });

  it('阶段图例（phase-legend）+ 3 个阶段 dot', () => {
    const wxss = read('index.wxss');
    expect(wxss).toContain('.phase-legend');
    expect(wxss).toContain('.p1-dot');
    expect(wxss).toContain('.p2-dot');
    expect(wxss).toContain('.p3-dot');
  });

  it('mapPlanDays 走 services/plan.ts', () => {
    const ts = read('index.ts');
    expect(ts).toContain('mapPlanDays');
    expect(ts).toContain('services/plan');
  });
});
