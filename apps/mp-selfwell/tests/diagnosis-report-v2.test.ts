import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const read = (name: string) => readFileSync(
  join(__dirname, '..', 'miniprogram', 'pages', 'diagnosis-report-v2', name),
  'utf-8',
);

describe('diagnosis-report-v2 contract', () => {
  it('renders the dynamic 3-photo and 5-profile hero counts', () => {
    const wxml = read('index.wxml');
    expect(wxml).toContain('基于 {{photoCount}} 张照片 + {{profileCount}} 项档案');
    expect(wxml).toContain('hero-title');
    expect(wxml).toContain('不是医学判断');
    expect(read('index.ts')).toContain('profileCount: 5');
  });

  it('contains four detailed directions with Bilibili chips', () => {
    const ts = read('index.ts');
    expect((ts.match(/title: '[^']+', description:/g) ?? []).length).toBeGreaterThanOrEqual(4);
    expect((ts.match(/video: 'B站/g) ?? []).length).toBe(4);
    expect(read('index.wxml')).toContain('video-chip');
  });

  it('renders twelve tags including lavender strong tags', () => {
    const ts = read('index.ts');
    expect((ts.match(/label: '[^']+', strong:/g) ?? []).length).toBe(12);
    const wxss = read('index.wxss');
    expect(wxss).toContain('.tag.strong');
    expect(wxss).toContain('.tag');
  });

  it('locks the three phase left-edge colors', () => {
    const wxss = read('index.wxss');
    expect(wxss).toContain('.phase-card.p1');
    expect(wxss).toContain('border-left: 3px solid var(--color-primary-mint');
    expect(wxss).toContain('.phase-card.p2');
    expect(wxss).toContain('border-left: 3px solid #C7D8B9');
    expect(wxss).toContain('.phase-card.p3');
    expect(wxss).toContain('border-left: 3px solid var(--color-accent-warm');
  });

  it('uses wx:if plus wx:else for the three-action fold', () => {
    const wxml = read('index.wxml');
    expect(wxml).toContain('wx:if="{{!expandedActions}}"');
    expect(wxml).toContain('wx:else');
    expect(read('index.ts')).toContain('expandedActions: !this.data.expandedActions');
  });

  it('generates and redirects to plan delivery with plan id', () => {
    // PR-Contract-Fix C-2: 路径必须是 POST /plans/generate(对齐后端契约)
    const ts = read('index.ts');
    expect(ts).toContain("post<PlanCreateResponse>('/plans/generate'");
    expect(ts).toContain("wx.setStorageSync('plan.delivery.id', planId)");
    expect(ts).toContain('/pages/plan-delivery/index?plan_id=');
  });

  it('keeps the secondary skip CTA returning to today tab', () => {
    // V2 IA: today Tab = home/index(app.json tabBar[1].pagePath)。
    // 旧路径 /pages/today/index 已废弃(PR-V2-B 删除)。
    const ts = read('index.ts');
    expect(ts).toContain("url: '/pages/home/index'");
    expect(read('index.wxml')).toContain('先不生成了');
  });

  it('never calls the nonexistent GET /plans/drafts endpoint', () => {
    // 2026-07-12 bug fix: 前端曾调用不存在的 GET /plans/drafts，
    // 后端 /{plan_id} 路由把它当 plan_id，触发 asyncpg UUID 解析错。
    // 真源：PRD V1.3 没有 /plans/drafts；实施计划 v2-unified-parent 也没有。
    const ts = read('index.ts');
    const js = read('index.js');
    expect(ts).not.toMatch(/\/plans\/drafts/);
    expect(js).not.toMatch(/\/plans\/drafts/);
  });
});
