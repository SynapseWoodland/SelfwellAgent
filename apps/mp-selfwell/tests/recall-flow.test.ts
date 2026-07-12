import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const pageDir = join(__dirname, '..', 'miniprogram', 'pages', 'recall-flow');
const readPage = (name: string) => readFileSync(join(pageDir, name), 'utf-8');

describe('PR-4 recall-flow page contract', () => {
  it('registers the page and renders the custom header', () => {
    const app = JSON.parse(readFileSync(join(__dirname, '..', 'miniprogram', 'app.json'), 'utf-8'));
    const wxml = readPage('index.wxml');
    expect(app.pages).toContain('pages/recall-flow/index');
    expect(wxml).toContain('问问过去的自己');
    expect(wxml).toContain('bindtap="onBack"');
    expect(wxml).toContain('>‹</button>');
  });

  it('provides 3, 7, 14 and custom period chips', () => {
    const ts = readPage('index.ts');
    expect(ts).toContain("{ label: '3 天前', value: 3 }");
    expect(ts).toContain("{ label: '7 天前', value: 7 }");
    expect(ts).toContain("{ label: '14 天前', value: 14 }");
    expect(ts).toContain("{ label: '自定义', value: 'custom' }");
  });

  it('opens a custom date picker and converts the date to days_offset', () => {
    const ts = readPage('index.ts');
    const wxml = readPage('index.wxml');
    expect(wxml).toContain('mode="date"');
    expect(wxml).toContain('onConfirmCustom');
    expect(ts).toContain('daysFromDate(this.data.customDate)');
    expect(ts).toContain("customPickerVisible: true");
  });

  it('defaults to a user_manual seven-day request from onLoad', () => {
    const ts = readPage('index.ts');
    expect(ts).toContain("options?.days_offset ?? '7'");
    expect(ts).toContain("options?.trigger ?? 'user_manual'");
    expect(ts).toContain("selectedPeriod: 7");
  });

  it('posts the selected days_offset to the recall endpoint', () => {
    const ts = readPage('index.ts');
    expect(ts).toContain("'/butler/recall'");
    expect(ts).toContain('{ trigger, days_offset: daysOffset }');
    expect(ts).toMatch(/post<RecallResult,\s*\{ trigger: string; days_offset: number \}>/);
  });

  it('renders AI summary and historical photo thumbnails', () => {
    const wxml = readPage('index.wxml');
    expect(wxml).toContain('recall.context_photos.summary || recall.summary');
    expect(wxml).toContain('wx:for="{{recall.referenced_photos}}"');
    expect(wxml).toContain('src="{{item.url}}"');
  });

  it('locks the AIMessage.context_photos TypeScript schema', () => {
    const ts = readPage('index.ts');
    expect(ts).toMatch(/interface AIMessageContextPhotos[\s\S]*directions: ContextDirection\[\]/);
    expect(ts).toMatch(/interface AIMessageContextPhotos[\s\S]*tags: string\[\]/);
    expect(ts).toMatch(/interface AIMessageContextPhotos[\s\S]*summary: string/);
    expect(ts).toMatch(/interface AIMessageContextPhotos[\s\S]*injected_at: string/);
    expect(ts).toMatch(/interface ContextDirection[\s\S]*num: number[\s\S]*title: string[\s\S]*level: string[\s\S]*description: string/);
  });

  it('offers continue-chat and save-as-diary CTAs', () => {
    const ts = readPage('index.ts');
    const wxml = readPage('index.wxml');
    expect(wxml).toContain('>继续聊</button>');
    expect(wxml).toContain('>保存为日记</button>');
    expect(ts).toContain("wx.switchTab({ url: '/pages/assistant-home/index' })");
    expect(ts).toContain("await post('/feedback'");
  });
});
