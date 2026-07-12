/**
 * V2 STYLE TOKENS · Snapshot 锁值测试（PR-6 契约测试）
 * ─────────────────────────────────────────────────────────────────
 * 真源：docs/spec/SPEC-A6-V2-STYLE-TOKENS.md
 * 真源：docs/design/ia-and-wireframe.md §2A.1
 * 真源：plans/v2-unified-parent.md §2.6 + §3.3 契约「V2 颜色 token 值」
 *
 * 锁值目的：
 *  - PR-6 锁定 8 颜色 / 7 字号 / 7 圆角 / 进度环 / 阴影 / 间距 / 字体回退 token
 *  - PR-3 / PR-5 / PR-7 引用 app.wxss 时不会无意中修改 hex 值
 *  - vitest snapshot 锁策略：精确比对每个 token 的定义行（行内正则）
 *
 * 与 vitest 内置 toMatchSnapshot 关系：
 *  - 此处用显式断言 + 自定义 snapshot 字符串，避免 vitest 自动生成 __snapshots__ 目录
 *    （PR-6 测试门槛要求「token 值不变，搜 app.wxss」，显式断言更利于 CI grep 失败 diff）
 *
 * 与既有 app.wxss 旧 token 关系：
 *  - 旧 token（--mint / --ink-900 等 rpx 体系）保留不动，本测试**不**覆盖它们
 *  - V2 token 与旧 token 同名冲突时（--radius-sm / --radius-md / --radius-lg / --radius-xl），
 *    V2 用 px、旧用 rpx，本测试只校验 V2 行的字面值
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

// ESM-safe __dirname（vitest.config.ts 标了 "type": "module"）
const __dirname = dirname(fileURLToPath(import.meta.url));

/**
 * app.wxss 的绝对路径。
 * 测试文件位于 apps/mp-selfwell/tests/，目标文件位于 apps/mp-selfwell/miniprogram/。
 */
const APP_WXSS_PATH = resolve(__dirname, '..', 'miniprogram', 'app.wxss');

let appWxssContent = '';

beforeAll(() => {
  appWxssContent = readFileSync(APP_WXSS_PATH, 'utf-8');
});

/**
 * 提取 CSS 自定义属性的字面值。
 *
 * 匹配规则：`--token-name: <value>;`（值可为颜色 / 数字 / 字符串 / 函数）。
 * 不跨行匹配（CSS 自定义属性单行定义）。
 *
 * 重要：返回 **最后一个** 匹配值。
 * 原因：app.wxss 内 V2 token 块（px 体系）位于 page { } 块（rpx 体系）之后，
 * CSS 级联按"后定义覆盖先定义"生效，本测试须反映 PR-6 落地的最终值（即 V2 块）。
 * 例如 `--radius-sm` 在旧 page 块内是 `16rpx`，V2 块内是 `8px`，
 * 取最后一个匹配才能锁住 V2 值（PR-6 契约）。
 */
function extractTokenValue(tokenName: string): string | null {
  // 使用 /g 匹配所有，遍历取最后一个非空值
  const re = new RegExp(
    `^\\s*--${tokenName}\\s*:\\s*([^;]+);`,
    'gm',
  );
  let last: string | null = null;
  let match: RegExpExecArray | null;
  while ((match = re.exec(appWxssContent)) !== null) {
    last = match[1].trim();
  }
  return last;
}

/**
 * 断言 token 存在且值精确匹配。
 */
function assertToken(tokenName: string, expectedValue: string): void {
  const actual = extractTokenValue(tokenName);
  expect(
    actual,
    `V2 token --${tokenName} 必须存在于 app.wxss`,
  ).not.toBeNull();
  expect(
    actual,
    `V2 token --${tokenName} 值不被意外修改（PR-6 契约）`,
  ).toBe(expectedValue);
}

/**
 * 断言 token 存在但不强校验值（用于尺寸类 token，因 PR-3 可微调 rpx 换算）。
 */
function assertTokenExists(tokenName: string): void {
  const actual = extractTokenValue(tokenName);
  expect(
    actual,
    `V2 token --${tokenName} 必须存在于 app.wxss`,
  ).not.toBeNull();
}

/**
 * 整段 V2 颜色 token 锁值（8 个）。
 * 锁值来源：plans/v2-unified-parent.md §2.6 + docs/design/ia-and-wireframe.md §2A.1
 */
const V2_COLOR_TOKENS = [
  { name: 'color-primary-mint', value: '#A8C5B5' },        // 主色：薄荷绿
  { name: 'color-primary-mint-dark', value: '#5A8270' },   // 主色深
  { name: 'color-secondary-cream', value: '#F5E6D3' },     // 奶油杏
  { name: 'color-secondary-lavender', value: '#D4C5E2' },  // 薰衣草紫
  { name: 'color-secondary-peach', value: '#F0D9C4' },     // 蜜桃粉
  { name: 'color-secondary-sky', value: '#B8D4E3' },       // 天空蓝
  { name: 'color-accent-warm', value: '#9C7AB8' },         // 强调色：薰衣草紫深
  { name: 'color-accent-earth', value: '#A0724F' },        // 强调色：赭石
] as const;

/**
 * 整段 V2 字号 token（7 个；用户原指令文里写"6 字号"但列出 7 个，按列出的锁）。
 */
const V2_FONT_SIZE_TOKENS = [
  { name: 'font-size-caption', value: '10px' },
  { name: 'font-size-body-sm', value: '12px' },
  { name: 'font-size-body', value: '14px' },
  { name: 'font-size-body-lg', value: '16px' },
  { name: 'font-size-heading', value: '18px' },
  { name: 'font-size-title', value: '22px' },
  { name: 'font-size-display', value: '28px' },
] as const;

/**
 * 整段 V2 圆角 token（7 个）。
 */
const V2_RADIUS_TOKENS = [
  { name: 'radius-xs', value: '4px' },
  { name: 'radius-sm', value: '8px' },
  { name: 'radius-md', value: '12px' },
  { name: 'radius-lg', value: '16px' },
  { name: 'radius-xl', value: '24px' },
  { name: 'radius-pill', value: '999px' },
  { name: 'radius-circle', value: '50%' },
] as const;

/**
 * 进度环 token（来自 plans/v2-unified-parent.md §2.6）。
 */
const V2_PROGRESS_RING_TOKENS = [
  { name: 'progress-ring-size', value: '37' },
  { name: 'progress-ring-stroke', value: '6' },
  { name: 'progress-ring-fg', value: '#A8C5B5' },
  { name: 'progress-ring-bg', value: '#E2E8F0' },
] as const;

/**
 * 阴影 token。
 */
const V2_SHADOW_TOKENS = [
  { name: 'shadow-card', value: '0 2px 8px rgba(0, 0, 0, 0.06)' },
  { name: 'shadow-pop', value: '0 4px 16px rgba(0, 0, 0, 0.08)' },
] as const;

/**
 * 间距 token（存在性 + 关键值锁）。
 */
const V2_SPACE_TOKENS = [
  { name: 'space-1', value: '4px' },
  { name: 'space-2', value: '8px' },
  { name: 'space-3', value: '12px' },
  { name: 'space-4', value: '16px' },
  { name: 'space-6', value: '24px' },
  { name: 'space-8', value: '32px' },
  { name: 'space-12', value: '48px' },
] as const;

/**
 * 字体回退 token（仅断言存在；值含字体名引号 + 多 fallback，字符串比对容错差）。
 */
const V2_FONT_FAMILY_TOKENS = [
  { name: 'font-family-cn', expectedSubstring: 'PingFang SC' },
  { name: 'font-family-num', expectedSubstring: 'SF Pro Display' },
] as const;

describe('PR-6 V2 style tokens · app.wxss snapshot', () => {
  describe('文件存在性', () => {
    it('app.wxss 路径正确解析', () => {
      expect(appWxssContent.length, 'app.wxss 内容非空').toBeGreaterThan(0);
      // 文件头应包含「app.wxss」标识（自我描述）
      expect(appWxssContent).toContain('app.wxss');
    });

    it('app.wxss 含 V2 token 块标记', () => {
      // 锚点注释（PR-6 注入的 V2 STYLE TOKENS 块头）
      expect(
        appWxssContent,
        'V2 STYLE TOKENS 锚点注释必须存在（PR-6 契约）',
      ).toContain('V2 STYLE TOKENS');
    });
  });

  describe('8 颜色 token 锁值', () => {
    for (const { name, value } of V2_COLOR_TOKENS) {
      it(`--${name} === ${value}`, () => {
        assertToken(name, value);
      });
    }

    it('8 颜色 token 总数校验', () => {
      // 用 grep 数定义行（行首 --color-*）
      const colorMatches = appWxssContent.match(/^\s*--color-[a-z-]+:/gm) ?? [];
      // 至少 8 个 V2 颜色（不排除未来新增）
      expect(
        colorMatches.length,
        'app.wxss 应至少含 8 个 --color-* token 定义行',
      ).toBeGreaterThanOrEqual(8);
    });
  });

  describe('7 字号 token 锁值', () => {
    for (const { name, value } of V2_FONT_SIZE_TOKENS) {
      it(`--${name} === ${value}`, () => {
        assertToken(name, value);
      });
    }
  });

  describe('7 圆角 token 锁值', () => {
    for (const { name, value } of V2_RADIUS_TOKENS) {
      it(`--${name} === ${value}`, () => {
        assertToken(name, value);
      });
    }

    it('7 圆角 token 总数校验', () => {
      const radiusMatches = appWxssContent.match(/^\s*--radius-[a-z-]+:/gm) ?? [];
      expect(
        radiusMatches.length,
        'app.wxss 应至少含 7 个 --radius-* token 定义行',
      ).toBeGreaterThanOrEqual(7);
    });
  });

  describe('间距 / 阴影 / 进度环 token', () => {
    for (const { name, value } of V2_SPACE_TOKENS) {
      it(`间距 --${name} === ${value}`, () => {
        assertToken(name, value);
      });
    }

    for (const { name, value } of V2_SHADOW_TOKENS) {
      it(`阴影 --${name} === ${value}`, () => {
        assertToken(name, value);
      });
    }

    for (const { name, value } of V2_PROGRESS_RING_TOKENS) {
      it(`进度环 --${name} === ${value}`, () => {
        assertToken(name, value);
      });
    }
  });

  describe('字体回退 token', () => {
    for (const { name, expectedSubstring } of V2_FONT_FAMILY_TOKENS) {
      it(`--${name} 含 "${expectedSubstring}"`, () => {
        const actual = extractTokenValue(name);
        expect(actual, `--${name} 必须存在`).not.toBeNull();
        expect(actual, `--${name} 必须含 "${expectedSubstring}"`).toContain(
          expectedSubstring,
        );
      });
    }

    it('中文字体栈包含 PingFang SC + Microsoft YaHei', () => {
      const value = extractTokenValue('font-family-cn');
      expect(value).toContain('PingFang SC');
      expect(value).toContain('Microsoft YaHei');
      expect(value).toContain('sans-serif');
    });

    it('数字字体栈包含 SF Pro Display + Inter', () => {
      const value = extractTokenValue('font-family-num');
      expect(value).toContain('SF Pro Display');
      expect(value).toContain('Inter');
      expect(value).toContain('sans-serif');
    });
  });

  describe('跨 PR 不变量（防御性回归）', () => {
    it('禁用色 #FF4D4F 不在 app.wxss 内（PR-6 不引入）', () => {
      // 排除注释行：检查非注释区段
      // 简化策略：直接 grep，但要求注释内允许（注释是说明禁用，不算违反）
      // 这里仅做"全文件不出现"的硬约束（PR-6 阶段确保 V2 token 不引入禁用色）
      const lines = appWxssContent.split('\n');
      const codeLines = lines.filter(
        (line) => !line.trim().startsWith('//') && !line.trim().startsWith('*') && !line.trim().startsWith('/*'),
      );
      const codeText = codeLines.join('\n');
      expect(
        codeText.includes('#FF4D4F'),
        'app.wxss 非注释区不应出现 #FF4D4F',
      ).toBe(false);
    });

    it('V2 主色 --color-primary-mint 与旧 --mint 值一致（向下兼容）', () => {
      // V2 主色必须是 #A8C5B5，与旧 --mint（page 块内）值一致
      // 这是 PR-6 的隐藏约束：V2 不引入与旧 token 冲突的主色值
      const v2Mint = extractTokenValue('color-primary-mint');
      expect(v2Mint).toBe('#A8C5B5');

      // 旧 --mint 也应存在且为 #A8C5B5
      expect(appWxssContent).toMatch(/^\s*--mint\s*:\s*#A8C5B5\s*;/m);
    });
  });
});