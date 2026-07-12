/**
 * PR-5 · album 子页契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-unified-parent.md §2.5 + plans/v2-IA-pr-internal.md §PR-5
 *
 * 锁值 5 用例：
 *  1. 路由注册
 *  2. 四件套完整
 *  3. GET /me/album/photos + GET /me/album/stats 契约消费
 *  4. 时间段切换（周 chip 数组生成）
 *  5. 照片网格 + 预览 + json.usingComponents 不含 tabbar
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readPage(file: string): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'album', file),
    'utf-8',
  );
}

function readAppJson(): { pages: string[] } {
  const raw = readFileSync(
    join(__dirname, '..', 'miniprogram', 'app.json'),
    'utf-8',
  );
  return JSON.parse(raw);
}

describe('PR-5 · album 子页（V2 17-record-album 单页）', () => {
  it('用例 1: app.json 注册 pages/album/index', () => {
    const app = readAppJson();
    expect(app.pages).toContain('pages/album/index');
  });

  it('用例 2: 子页四件套完整', () => {
    for (const f of ['index.ts', 'index.wxml', 'index.wxss', 'index.json']) {
      const content = readPage(f);
      expect(content.length, `${f} 文件非空`).toBeGreaterThan(0);
    }
  });

  it('用例 3: GET /me/album/photos + GET /me/album/stats 契约兑现（PR-2 后端）', () => {
    const ts = readPage('index.ts');
    // 路径必须存在（模板字符串拼接）
    expect(ts).toMatch(/\/me\/album\/photos\?week=/);
    expect(ts).toContain("'/me/album/stats'");
    // 返回结构字段锁（与 backend album_service 对齐）
    expect(ts).toContain('week');
    expect(ts).toContain('count');
    expect(ts).toContain('photos');
    expect(ts).toContain('photo_url');
    expect(ts).toContain('feedback_id');
    // 统计字段
    expect(ts).toContain('total_photos');
    expect(ts).toContain('total_checkin_days');
    expect(ts).toContain('total_diary_entries');
    expect(ts).toContain('days_in_app');
  });

  it('用例 4: 时间段切换（最近 8 周 + ISO 周号 + 周 chip）', () => {
    const ts = readPage('index.ts');
    // ISO 周号工具
    expect(ts).toContain('isoWeek');
    // 实际拼接形如 `YYYY-W${...}` 而非常量字面
    expect(ts).toMatch(/W\$\{String\(weekNum\)\.padStart/);
    expect(ts).toContain('buildRecentWeeks');
    expect(ts).toContain('onSelectWeek');
    // WXML 含周 chip 列表
    const wxml = readPage('index.wxml');
    expect(wxml).toContain('al-week-chip');
    expect(wxml).toContain('wx:for="{{weeks}}"');
  });

  it('用例 5: 照片网格 + wx.previewImage + json.usingComponents 不含 tabbar', () => {
    const ts = readPage('index.ts');
    expect(ts).toContain('wx.previewImage');
    expect(ts).toContain('onTapPhoto');
    const wxml = readPage('index.wxml');
    expect(wxml).toContain('al-grid-cell');
    expect(wxml).toContain('wx:for="{{weekData.photos}}"');
    // 空态
    expect(wxml).toContain('al-empty');
    // 统计卡 4 项
    expect(wxml).toContain('al-stats');
    const json = readPage('index.json');
    const parsed = JSON.parse(json);
    expect(parsed.usingComponents ?? {}).not.toHaveProperty('tabbar');
    expect(parsed.navigationBarTitleText).toBe('我的时光');
  });
});