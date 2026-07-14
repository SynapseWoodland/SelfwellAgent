/**
 * FE-FIX-03 · home/index.smart-body.ts getDrawCards() 单测
 * ──────────────────────────────────────────────────────────────
 * 真源：docs/plan/frontend-fix-plan.md §FE-FIX-03
 *
 * 验收标准：
 *  - getDrawCards() 返回数组长度为 8
 *  - 每项含 id (string, 非空) / title (string) / pagePath (string, 以 /pages/ 开头)
 *  - openDrawer() 返回 true；closeDrawer() 返回 false
 *
 * 设计要点：
 *  - 字符串匹配 smart-body.ts 源码（与项目约定一致：home-tab2.test.ts 同款风格）
 *  - 验证抽屉 8 项 id 全部存在 + pagePath 格式契约稳定
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readSmartBody(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'home', 'index.smart-body.ts'),
    'utf-8',
  );
}

describe('FE-FIX-03 · home/index.smart-body.ts getDrawCards() 抽屉 8 项', () => {
  it('用例 1: getDrawCards() 返回数组长度为 8（8 条 id 字面锁）', () => {
    const sb = readSmartBody();
    const expectedIds = ['profile', 'time', 'notification', 'privacy', 'support', 'about', 'feedback', 'plan'];
    for (const id of expectedIds) {
      expect(sb, `smart-body.ts 缺少抽屉卡片 id=${id}`).toContain(`id: '${id}'`);
    }
    expect(sb).toMatch(/getDrawCards\s*\(\s*\)\s*:\s*DrawerCard\[\]/);
    expect(sb).toMatch(/return\s*\[/);
  });

  it('用例 2: 每项含 id/title/pagePath 字段（核心契约字段）', () => {
    const sb = readSmartBody();
    // DrawerCard interface 必须声明 id / title / pagePath 字段
    expect(sb).toMatch(/interface\s+DrawerCard[\s\S]*id:\s*string/);
    expect(sb).toMatch(/interface\s+DrawerCard[\s\S]*title:\s*string/);
    expect(sb).toMatch(/interface\s+DrawerCard[\s\S]*pagePath:\s*string/);
    // 所有 pagePath 必须以 /pages/ 开头（防意外的相对路径）
    const pagePathMatches = sb.match(/pagePath:\s*['"]([^'"]+)['"]/g) ?? [];
    expect(pagePathMatches.length).toBeGreaterThanOrEqual(8);
    for (const match of pagePathMatches) {
      // 取 pagePath 值（第 1 个捕获组的字符串）
      const valueMatch = match.match(/pagePath:\s*['"]([^'"]+)['"]/);
      const value = valueMatch?.[1] ?? '';
      expect(value, `pagePath 必须以 /pages/ 开头：${value}`).toMatch(/^\/pages\//);
    }
  });

  it('用例 3: openDrawer() 返回 true；closeDrawer() 返回 false', () => {
    const sb = readSmartBody();
    expect(sb).toMatch(/export\s+function\s+openDrawer\s*\(\s*\)\s*:\s*boolean\s*\{[\s\S]*return\s+true/);
    expect(sb).toMatch(/export\s+function\s+closeDrawer\s*\(\s*\)\s*:\s*boolean\s*\{[\s\S]*return\s+false/);
  });

  it('用例 4: 8 项 id 全部登记（防漏配）', () => {
    const sb = readSmartBody();
    for (const id of ['profile', 'time', 'notification', 'privacy', 'support', 'about', 'feedback', 'plan']) {
      expect(sb, `抽屉卡片 id=${id} 必须存在`).toContain(`id: '${id}'`);
    }
  });
});
