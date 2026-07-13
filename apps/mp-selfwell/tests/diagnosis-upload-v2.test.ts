import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const read = (name: string) => readFileSync(
  join(__dirname, '..', 'miniprogram', 'pages', 'diagnosis-upload-v2', name),
  'utf-8',
);

describe('diagnosis-upload-v2 contract', () => {
  it('renders exactly three upload slots', () => {
    const ts = read('index.ts');
    expect(ts).toContain("label: '额头'");
    expect(ts).toContain("label: '面颊'");
    expect(ts).toContain("label: '颈部'");
  });

  it('binds filledUrl images and filled state', () => {
    expect(read('index.wxml')).toContain('src="{{item.filledUrl}}"');
    expect(read('index.wxml')).toContain("item.filled ? 'filled' : ''");
  });

  it('supports replacing a selected photo', () => {
    expect(read('index.ts')).toMatch(/slotIndex === index[\s\S]*filledUrl: picked\.path/);
    expect(read('index.wxml')).toContain('点击换图');
  });

  it('offers five multi-select body parts', () => {
    const ts = read('index.ts');
    expect(ts).toContain("['额头', '面颊', '颈部', 'T 区', 'U 区']");
    expect(ts).toContain('selected: !option.selected');
  });

  it('offers six mutually exclusive age ranges', () => {
    const ts = read('index.ts');
    expect(ts).toContain("['<18', '18-24', '25-34', '35-44', '45-54', '55+']");
    expect(ts).toContain('selected: option.value === value');
  });

  it('updates the hero profile and photo counters dynamically', () => {
    const wxml = read('index.wxml');
    expect(wxml).toContain('{{profileFilledCount}}/6 项档案 + {{photoFilledCount}} 张照片');
    expect(read('index.ts')).toContain('countFilledFields(readUserProfile())');
  });

  it('uploads three images serially through assistant presign helper', () => {
    const ts = read('index.ts');
    expect(ts).toMatch(/for \(let index = 0; index < filledSlots\.length; index \+= 1\)/);
    expect(ts).toContain('await presignAndUploadOneForAssistant');
    expect(ts).not.toMatch(/Promise\.all\([\s\S]{0,100}presignAndUploadOneForAssistant/);
  });

  it('reports upload progress after every uploaded slot', () => {
    const ts = read('index.ts');
    expect(ts).toContain('uploadProgress: Math.round');
    expect(read('index.wxml')).toContain('{{uploadProgress}}%');
  });

  it('creates assistant session and redirects to loading v2', () => {
    const ts = read('index.ts');
    expect(ts).toContain("post<AssistantSessionResponse>('/assistant/sessions'");
    expect(ts).toContain('/pages/diagnosis-loading-v2/index?id=');
    expect(ts).toContain('&stream_url=');
  });
});
