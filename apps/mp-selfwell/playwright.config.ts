/**
 * playwright.config.ts — Playwright 视觉回归配置
 * Layer 1：HTML 原型 → PNG baseline
 *
 * 用法：
 *   pnpm visual:baseline:install   # 安装 Chromium（仅首次）
 *   pnpm visual:baseline          # 生成 / 验证 baseline
 *   pnpm visual:update            # 强制接受当前渲染为新 baseline
 *
 * PR-V2-A
 */

import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

// apps/mp-selfwell/ 的绝对路径（__dirname 在 ESM 用 import.meta.url 代替）
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');

export default defineConfig({
  testDir: './tests/visual-baseline',
  timeout: 30_000,

  // iPhone 14 尺寸（与原型一致）
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 375, height: 812 },
      },
    },
  ],

  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.02, // 容忍字体/emoji 渲染差异
    },
  },

  updateMode: 'none',
  updateSources: [],
  reporter: [['list']],
});

// 导出供 spec 文件使用
export const PROTOTYPE_DIR = resolve(ROOT, 'docs/design/figma-pixso-spec/pages-v2');
