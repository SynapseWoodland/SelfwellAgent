/**
 * Selfwell 前端 RED 测试 - recall-compare navigation methods (PR-V2-D)
 * 真源：15e-recall-cta-buttons.html
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const source = readFileSync(
  join(__dirname, '..', 'miniprogram', 'pages', 'recall-compare', 'index.ts'),
  'utf-8',
);

describe('PR-V2-D recall-compare navigation methods', () => {
  it('keeps onLoad and routes onContinueChat to the assistant tab', () => {
    expect(source).toMatch(/onLoad\(/);
    expect(source).toMatch(/onContinueChat\(\)[\s\S]*wx\.switchTab\(\{ url: '\/pages\/assistant-home\/index' \}\)/);
  });

  it('routes onSaveAsDiary with the current recall summary', () => {
    expect(source).toMatch(/onSaveAsDiary\(\)[\s\S]*snapshot\?\.current_report_text/);
    expect(source).toContain('/pages/feedback-diary/index?source=recall&text=');
  });

  it('loads snapshot from GET /butler/recall/day/:day', () => {
    expect(source).toMatch(/\/butler\/recall\/day\//);
  });
});
