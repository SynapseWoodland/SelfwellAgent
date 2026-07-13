import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const read = (name: string) => readFileSync(
  join(__dirname, '..', 'miniprogram', 'pages', 'diagnosis-loading-v2', name),
  'utf-8',
);

describe('diagnosis-loading-v2 contract', () => {
  it('uses a rotating SVG progress ring instead of conic-gradient', () => {
    const ts = read('index.ts');
    expect(ts).toContain('<svg xmlns=');
    expect(ts).toContain('transform="rotate(-90 32 32)"');
    expect(read('index.wxss')).not.toContain('conic-gradient');
  });

  it('renders the six steps in the locked order', () => {
    const ts = read('index.ts');
    const labels = ['连接分析资料', '照片安全预处理', '识别状态细节', '生成养护方向', '21 天方案编排', '诊断报告就绪'];
    let cursor = -1;
    for (const label of labels) {
      const next = ts.indexOf(label);
      expect(next).toBeGreaterThan(cursor);
      cursor = next;
    }
  });

  it('maps the five SSE stages onto six UI steps', () => {
    const ts = read('index.ts');
    expect(ts).toMatch(/start:\s*0/);
    expect(ts).toMatch(/preprocess:\s*1/);
    expect(ts).toMatch(/analyzing:\s*2/);
    expect(ts).toMatch(/suggestion:\s*4/);
    expect(ts).toMatch(/ready:\s*5/);
    expect(ts).not.toMatch(/STAGE_TO_STEP[\s\S]*plan:\s*\d/);
  });

  it('starts mock advancement after three silent seconds at 1.5 seconds per step', () => {
    const ts = read('index.ts');
    expect(ts).toContain('}, 3000)');
    expect(ts).toContain('}, 1500)');
    expect(ts).toContain('if (!this.privateReceivedEvent) this.startMockProgress()');
  });

  it('shows a stable network exception message and redirects on done', () => {
    const ts = read('index.ts');
    expect(ts).toContain('网络异常，正在为你继续分析');
    expect(ts).toContain("eventName === 'done'");
    expect(ts).toContain('/pages/diagnosis-report-v2/index?session_id=');
  });
});
