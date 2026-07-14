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

  it('FE-FIX-09 渲染顶层 recall.summary + referenced_photos 缩略图', () => {
    const wxml = readPage('index.wxml');
    // V1.1.1：context_photos 已变为 array<{url, caption}>；summary 走顶层 recall.summary
    expect(wxml).toContain('recall.summary');
    expect(wxml).not.toContain('recall.context_photos.summary');
    expect(wxml).toContain('wx:for="{{recall.referenced_photos}}"');
    expect(wxml).toContain('src="{{item.url}}"');
  });

  it('FE-FIX-09 锁 RecallResponse.referenced_feedbacks / referenced_photos / context_photos 内联对象结构', () => {
    const ts = readPage('index.ts');
    // ReferencedFeedback
    expect(ts).toMatch(/interface\s+ReferencedFeedback[\s\S]*id:\s*string/);
    expect(ts).toMatch(/interface\s+ReferencedFeedback[\s\S]*body_part\?:/);
    expect(ts).toMatch(/interface\s+ReferencedFeedback[\s\S]*snippet\?:/);
    expect(ts).toMatch(/interface\s+ReferencedFeedback[\s\S]*feedback_type\?:/);
    expect(ts).toMatch(/interface\s+ReferencedFeedback[\s\S]*photo_url\?:/);
    // ReferencedPhoto
    expect(ts).toMatch(/interface\s+ReferencedPhoto[\s\S]*url:\s*string/);
    expect(ts).toMatch(/interface\s+ReferencedPhoto[\s\S]*body_part\?:/);
    expect(ts).toMatch(/interface\s+ReferencedPhoto[\s\S]*uploaded_at\?:/);
    // ContextPhoto（V1.1.1 起改为 array）
    expect(ts).toMatch(/interface\s+ContextPhoto[\s\S]*url:\s*string/);
    expect(ts).toMatch(/interface\s+ContextPhoto[\s\S]*caption\?:/);
    // RecallResult 顶层字段
    expect(ts).toMatch(/interface\s+RecallResult[\s\S]*recall_id:\s*string/);
    expect(ts).toMatch(/interface\s+RecallResult[\s\S]*safety_passed\?:/);
    expect(ts).toMatch(/interface\s+RecallResult[\s\S]*referenced_feedbacks\?:\s*ReferencedFeedback\[\]/);
    expect(ts).toMatch(/interface\s+RecallResult[\s\S]*referenced_photos\?:\s*ReferencedPhoto\[\]/);
    expect(ts).toMatch(/interface\s+RecallResult[\s\S]*context_photos\?:\s*ContextPhoto\[\]/);
    // 旧 AIMessageContextPhotos / ContextDirection 必须删除（不再用于 RecallResponse）
    expect(ts).not.toMatch(/interface\s+AIMessageContextPhotos/);
    expect(ts).not.toMatch(/interface\s+ContextDirection/);
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
