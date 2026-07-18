/**
 * tests/visual-baseline/visual-baseline.spec.ts
 * ─────────────────────────────────────────────────────────
 * Layer 1：Playwright 把所有 30 个 HTML 原型截图，输出 PNG baseline。
 *
 * 用法：
 *   pnpm visual:baseline:install   # 仅首次
 *   pnpm visual:baseline          # 生成 / 验证 baseline
 *   pnpm visual:update            # 强制覆盖现有 baseline
 *
 * 屏幕尺寸：375 × 812（iPhone 14）
 * 像素差异阈值：maxDiffPixelRatio: 0.02
 *
 * PR-V2-A
 */

import { test, expect, type Page } from '@playwright/test';
import { readdirSync } from 'fs';

// 原型 HTML 目录（绝对路径）
const PROTOTYPE_DIR =
  'D:\\agent-project\\SelfwellAgent\\docs\\design\\figma-pixso-spec\\pages-v2';

// 30 个原型文件（按 mapping-pages-v2.md 顺序）
const PROTOTYPES = [
  '01-splash.html',
  '02-login.html',
  '03-home.html',
  '04-diagnosis-upload.html',
  '05-diagnosis-loading.html',
  '06-diagnosis-report.html',
  '08-butler-diary.html',
  '08-checkin.html',
  '08b-recall-past-self.html',
  '09-square.html',
  '11-profile.html',
  '12-hug-card-day7.html',
  '13-hug-card-day14.html',
  '14-hug-card-day21.html',
  '15a-butler-home-tab1.html',
  '15b-today-tab2.html',
  '15c-manage-drawer.html',
  '15d-3step-card-inline-profile.html',
  '15e-recall-cta-buttons.html',
  '15f-plan-tabs-5state.html',
  '15g-p03b-diagnosis-to-plan.html',
  '15h-p03c-plan-delivery.html',
  '15i-butler-analyze-report-revised.html',
  '17-record-album.html',
  '18-profile-archive.html',
  '19-notifications.html',
  '20-privacy.html',
  '21-about.html',
  '22-contact.html',
] as const;

type PrototypeName = (typeof PROTOTYPES)[number];

// 隐藏原型标签（不影响页面主体）
const HIDE_SELECTORS = '.page-label, span.page-label';

/**
 * 截图单个原型文件。
 * file:// 协议需要绝对路径（Windows D:\... 格式）。
 */
async function screenshotPrototype(
  page: Page,
  fileName: string,
  snapshotName: string,
): Promise<void> {
  const filePath = `${PROTOTYPE_DIR}\\${fileName}`;

  if (!readdirSync(PROTOTYPE_DIR).includes(fileName)) {
    throw new Error(
      `原型文件不存在: ${filePath}\n请确认 docs/design/figma-pixso-spec/pages-v2/ 目录存在且包含 ${fileName}`,
    );
  }

  // Windows file:// 需要 file:///D:/... 格式
  const fileUrl = `file:///${filePath.replace(/\\/g, '/')}`;
  await page.goto(fileUrl);

  // 隐藏原型标签（不影响页面主体渲染）
  await page.addStyleTag({
    content: `${HIDE_SELECTORS} { display: none !important; }`,
  });

  // 等待 DOM 就绪
  await page.waitForLoadState('domcontentloaded');
  // 等待字体渲染（最多 1s）
  await page.waitForTimeout(500);

  await expect(page).toHaveScreenshot(`${snapshotName}.png`);
}

// ── 逐个截图（每个文件一个 test，方便单独 re-run）────────────────────

for (const fileName of PROTOTYPES) {
  const snapshotName = fileName.replace(/\.html$/, '');

  test(`原型截图: ${fileName}`, async ({ page }) => {
    await screenshotPrototype(page, fileName, snapshotName);
  });
}

// ── 全量截图（单一 test，一次性生成所有 baseline）────────────────────

test('全量: 截图所有 30 个原型', async ({ page }) => {
  for (const fileName of PROTOTYPES) {
    const snapshotName = fileName.replace(/\.html$/, '');
    await screenshotPrototype(page, fileName, snapshotName);
  }
});
