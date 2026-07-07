import { defineConfig } from 'vitest/config';
import { resolve } from 'node:path';

/**
 * Selfwell 自愈 · Vitest 配置
 * ─────────────────────────────────────
 * 覆盖范围：
 * - miniprogram/utils/*   —— 契约核心（request / error-code / config）
 * - tests/**              —— 所有 vitest 用例（contract / unit / 等）
 *
 * 排除：
 * - miniprogram/pages/** （页面级不写 vitest 单测，由
 *   miniprogram-automator 在 tests/sf1/ 端到端覆盖）
 */
export default defineConfig({
  resolve: {
    alias: {
      '~utils': resolve(__dirname, 'miniprogram/utils'),
    },
  },
  test: {
    globals: true,
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      include: ['miniprogram/utils/**/*.ts'],
      exclude: ['**/__tests__/**', '**/*.d.ts'],
    },
  },
});