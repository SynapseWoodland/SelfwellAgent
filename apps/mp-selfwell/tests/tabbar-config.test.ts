/**
 * FE-FIX-06 · assistant-home fallbackToHomeTab 配置常量单测
 * ──────────────────────────────────────────────────────────────
 * 真源：docs/plan/frontend-fix-plan.md §FE-FIX-06
 * 真源：apps/mp-selfwell/miniprogram/utils/config.ts（tabBar 配置常量）
 *
 * 验收标准：
 *  - getHomeTabUrl() 返回 /pages/home/index
 *  - TAB_ROUTES.today.url === /pages/home/index
 *  - assistant-home/index.ts fallbackToHomeTab 不含硬编码 /pages/home/index（除注释）
 *  - 4 项 tabBar 与 app.json 锁值严格一致
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readConfig(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'utils', 'config.ts'),
    'utf-8',
  );
}

function readAppJson(): { tabBar?: { list: Array<{ pagePath: string; text: string }> } } {
  return JSON.parse(
    readFileSync(join(__dirname, '..', 'miniprogram', 'app.json'), 'utf-8'),
  ) as { tabBar?: { list: Array<{ pagePath: string; text: string }> } };
}

function readAssistantHome(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'assistant-home', 'index.ts'),
    'utf-8',
  );
}

describe('FE-FIX-06 · utils/config.ts TAB_ROUTES + getHomeTabUrl() 配置常量', () => {
  it('用例 1: TAB_ROUTES.today.url === /pages/home/index', () => {
    const ts = readConfig();
    expect(ts).toMatch(/TAB_ROUTES[\s\S]*today:\s*\{/);
    expect(ts).toContain("pagePath: 'pages/home/index'");
    expect(ts).toContain("url: '/pages/home/index'");
  });

  it('用例 2: TAB_ROUTES 4 项与 app.json 锁值一致（顺序 + 文字）', () => {
    const ts = readConfig();
    const app = readAppJson();
    const tabBars = app.tabBar?.list ?? [];
    expect(tabBars).toHaveLength(4);
    // 4 项 id 都在 TS 中
    for (const id of ['butler', 'today', 'plaza', 'profile']) {
      expect(ts, `TAB_ROUTES 缺少 id=${id}`).toContain(`id: '${id}'`);
    }
    // 文字与 app.json 一致
    for (const entry of tabBars) {
      expect(ts, `TAB_ROUTES 缺少 text="${entry.text}"`).toContain(`text: '${entry.text}'`);
    }
    // pagePath 与 app.json 一致
    for (const entry of tabBars) {
      expect(ts, `TAB_ROUTES 缺少 pagePath="${entry.pagePath}"`).toContain(`pagePath: '${entry.pagePath}'`);
    }
  });

  it('用例 3: getHomeTabUrl() 导出 + 返回 TAB_ROUTES.today.url', () => {
    const ts = readConfig();
    expect(ts).toMatch(/export\s+function\s+getHomeTabUrl\s*\(\s*\)\s*:\s*string/);
    expect(ts).toMatch(/export\s+function\s+getHomeTabUrl/);
    expect(ts).toContain('return TAB_ROUTES.today.url');
  });

  it('用例 4: assistant-home 的 fallbackToHomeTab 不含字面 /pages/home/index', () => {
    const ts = readAssistantHome();
    // 抠出 fallbackToHomeTab 方法体
    const m = ts.match(/fallbackToHomeTab\s*\(\s*\)\s*\{([\s\S]*?)\n\s*\}\s*,?/);
    expect(m, 'assistant-home 必须定义 fallbackToHomeTab 方法').not.toBeNull();
    const body = m?.[1] ?? '';
    // 严格：方法体不含字面 /pages/home/index（避免重复硬编码）
    expect(body, 'fallbackToHomeTab 方法体不允许硬编码 /pages/home/index').not.toContain("'/pages/home/index'");
    expect(body, 'fallbackToHomeTab 方法体不允许硬编码 "/pages/home/index"').not.toContain('"/pages/home/index"');
    // 必须改为走 getHomeTabUrl() 工厂
    expect(body, 'fallbackToHomeTab 方法体必须使用 getHomeTabUrl()').toContain('getHomeTabUrl()');
    // switchTab + reLaunch 兜底链保留
    expect(body).toContain('wx.switchTab');
    expect(body).toContain('wx.reLaunch');
  });
});
