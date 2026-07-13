import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const read = (name: string) => readFileSync(
  join(__dirname, '..', 'miniprogram', 'pages', 'plan-delivery', name),
  'utf-8',
);

describe('plan-delivery contract', () => {
  it('renders the 46px deliver icon with the 0.6s pop animation', () => {
    const wxss = read('index.wxss');
    expect(wxss).toContain('.deliver-icon');
    expect(wxss).toContain('font-size: 46px');
    expect(wxss).toContain('animation: pop .6s ease-out');
    expect(wxss).toContain('@keyframes pop');
  });

  it('renders the summary-card-m with a 36px green gradient icon', () => {
    const wxss = read('index.wxss');
    expect(read('index.wxml')).toContain('21 天养护方案已生成');
    expect(wxss).toContain('.summary-card-m');
    expect(wxss).toMatch(/\.summary-icon-m[\s\S]*width: 36px;[\s\S]*linear-gradient/);
  });

  it('builds all 21 day rows and previews the first seven', () => {
    const ts = read('index.ts');
    expect(ts).toContain('Array.from({ length: 21 }');
    expect(ts).toContain('days.slice(0, 7)');
    expect(read('index.wxml')).toContain('查看全部 21 天');
  });

  it('shows all four status legend items', () => {
    const ts = read('index.ts');
    for (const label of ['已完成', '进行中', '待办', '反馈日']) expect(ts).toContain(label);
    expect(read('index.wxml')).toContain('legend-item-m');
  });
});
