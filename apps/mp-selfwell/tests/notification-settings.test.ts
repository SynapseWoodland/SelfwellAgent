/**
 * PR-5 · notification-settings 子页契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-unified-parent.md §2.5 + plans/v2-IA-pr-internal.md §PR-5
 *
 * 锁值 5 用例：
 *  1. 路由注册：app.json 含 pages/notification-settings/index
 *  2. 子页四件套存在（ts/wxml/wxss/json）
 *  3. json.usingComponents 不含 tabbar
 *  4. GET /me/notification-settings 契约消费
 *  5. PUT /me/notification-settings 契约消费（rowsToPayload 字段映射锁）
 *  6. 6 行 pref 锁（与后端 notification_service.DEFAULT_PREF_VALUES 对齐）
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readPage(file: string): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'notification-settings', file),
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

describe('PR-5 · notification-settings 子页', () => {
  it('用例 1: app.json 注册 pages/notification-settings/index', () => {
    const app = readAppJson();
    expect(app.pages).toContain('pages/notification-settings/index');
  });

  it('用例 2: 子页四件套完整（ts/wxml/wxss/json）', () => {
    for (const f of ['index.ts', 'index.wxml', 'index.wxss', 'index.json']) {
      const content = readPage(f);
      expect(content.length, `${f} 文件非空`).toBeGreaterThan(0);
    }
  });

  it('用例 3: json.usingComponents 不含 tabbar（PR-3 锁定约束）', () => {
    const json = readPage('index.json');
    const parsed = JSON.parse(json);
    expect(parsed.usingComponents ?? {}, 'usingComponents 应为空或不存在').not.toHaveProperty('tabbar');
  });

  it('用例 4: TS 调 GET /me/notification-settings（PR-2 后端契约兑现）', () => {
    const ts = readPage('index.ts');
    expect(ts).toContain("'/me/notification-settings'");
    // fetchSettings 走 get<T>
    expect(ts).toContain('get<');
    expect(ts).toMatch(/get<\{ prefs: [^}]*; total: number \}/);
  });

  it('用例 5: TS 调 PUT /me/notification-settings + pref_key 白名单 (6 个) 锁', () => {
    const ts = readPage('index.ts');
    // 路径字面必须存在（split across lines 但字面连续）
    expect(ts).toMatch(/put<[^>]*>/);
    expect(ts).toContain("'/me/notification-settings'");
    // 6 个 pref_key 必须存在（与后端 DEFAULT_PREF_VALUES 对齐）
    for (const key of [
      'daily_checkin',
      'weekly_recall',
      'feedback_ack',
      'plan_milestone',
      'album_unlock',
      'hug_card_ready',
    ]) {
      expect(ts, `pref_key ${key} 应在 PREF_ORDER / PREF_LABELS 内`).toContain(key);
    }
  });
});