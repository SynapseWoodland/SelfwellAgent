/**
 * PR-3 commit-1 · app.json tabBar 4 项严格 + 文字契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-IA-pr-internal.md §PR-3 commit-1
 * 真源：plans/v2-unified-parent.md §3.3「TabBar 严格约束」
 * 真源：docs/design/ia-and-wireframe.md §2.4
 *
 * 锁值目的（PR-3 commit-1 强契约）：
 *  - tabBar.list.length === 4 严格等于
 *  - 顺序：assistant-home / home(today) / community / profile-new
 *  - 文字：智能管家 / 今天 / 广场 / 我的（V2 设计稿，与旧"首页/智能管家/广场/我的"不同）
 *  - pages 列表含 pages/profile-new/index（V2 tabBar 第 4 项）
 *  - pages/profile/index 仍保留（向后兼容 deep link）
 *
 * 与 PR-5 兑现关系：本测试锁定的 4 项 + 文字，PR-5 子页 (notification-settings/privacy-policy/about/contact/record-album)
 * 不得在 json 中含 tabBar usingComponents，wxml 不渲染任何 tabBar 元素。
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

interface TabBarEntry {
  pagePath: string;
  text: string;
}

interface AppJson {
  pages: string[];
  tabBar?: {
    list: TabBarEntry[];
  };
}

function readAppJson(): AppJson {
  const raw = readFileSync(
    join(__dirname, '..', 'miniprogram', 'app.json'),
    'utf-8',
  );
  // app.json 是合法 JSON（小程序 IDE 读取）；此处直接 JSON.parse
  return JSON.parse(raw) as AppJson;
}

describe('PR-3 commit-1 · app.json tabBar 4 项严格 + 文字契约', () => {
  it('tabBar.list.length === 4（严格等于；V2 设计稿硬约束）', () => {
    const app = readAppJson();
    expect(app.tabBar).toBeDefined();
    expect(app.tabBar!.list).toHaveLength(4);
  });

  it('tabBar 第 1 项 = assistant-home + 智能管家', () => {
    const app = readAppJson();
    const first = app.tabBar!.list[0];
    expect(first.pagePath).toBe('pages/assistant-home/index');
    expect(first.text).toBe('智能管家');
  });

  it('tabBar 第 2 项 = home（今天） + 今天', () => {
    const app = readAppJson();
    const second = app.tabBar!.list[1];
    expect(second.pagePath).toBe('pages/home/index');
    expect(second.text).toBe('今天');
  });

  it('tabBar 第 3 项 = community + 广场', () => {
    const app = readAppJson();
    const third = app.tabBar!.list[2];
    expect(third.pagePath).toBe('pages/community/index');
    expect(third.text).toBe('广场');
  });

  it('tabBar 第 4 项 = profile-new + 我的', () => {
    const app = readAppJson();
    const fourth = app.tabBar!.list[3];
    expect(fourth.pagePath).toBe('pages/profile-new/index');
    expect(fourth.text).toBe('我的');
  });

  it('pages 列表注册 pages/profile-new/index（V2 tabBar 第 4 项落点）', () => {
    const app = readAppJson();
    expect(app.pages).toContain('pages/profile-new/index');
  });

  it('pages 列表保留 pages/profile/index（向后兼容老用户收藏 / deep link）', () => {
    const app = readAppJson();
    expect(app.pages).toContain('pages/profile/index');
  });

  it('tabBar 4 项 pagePath 必须唯一', () => {
    const app = readAppJson();
    const paths = app.tabBar!.list.map((e) => e.pagePath);
    expect(new Set(paths).size).toBe(4);
  });
});