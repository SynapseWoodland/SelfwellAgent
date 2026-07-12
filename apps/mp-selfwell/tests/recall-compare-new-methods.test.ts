import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const source = readFileSync(
  join(__dirname, '..', 'miniprogram', 'pages', 'recall-compare', 'index.ts'),
  'utf-8',
);

describe('PR-4 recall-compare navigation methods', () => {
  it('keeps onLoad and routes onContinueChat to the assistant tab', () => {
    expect(source).toMatch(/onLoad\(options: \{ day\?: string \}\)/);
    expect(source).toMatch(/onContinueChat\(\)[\s\S]*wx\.switchTab\(\{ url: '\/pages\/assistant-home\/index' \}\)/);
  });

  it('routes onSaveAsDiary with the current recall summary', () => {
    expect(source).toMatch(/onSaveAsDiary\(\)[\s\S]*snapshot\?\.emotionTrend/);
    expect(source).toContain('/pages/feedback-diary/index?source=recall&text=');
  });

  it('routes onAskAnother to a fresh seven-day manual recall', () => {
    expect(source).toMatch(/onAskAnother\(\)[\s\S]*\/pages\/recall-flow\/index\?trigger=user_manual&days_offset=7/);
  });
});
