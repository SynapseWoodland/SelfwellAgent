#!/usr/bin/env node
/**
 * scripts/visual-baseline-setup.js
 * ─────────────────────────────────────────────────────────
 * 首次运行前必须执行此脚本，将所有 30 个原型截图写入 __snapshots__/ 目录。
 *
 * 之后每次变更代码后，只需运行：
 *   pnpm visual:baseline    （验证与 baseline 差异 ≤ 2%）
 *   pnpm visual:update     （强制接受当前渲染为新 baseline）
 *
 * PR-V2-A
 */

import { chromium } from '@playwright/test';
import { readdirSync, mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const PROTOTYPE_DIR =
  'D:\\agent-project\\SelfwellAgent\\docs\\design\\figma-pixso-spec\\pages-v2';

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
];

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 375, height: 812 });

  // 隐藏 .page-label 标签（原型调试用）
  const hideStyle =
    '.page-label, span.page-label { display: none !important; }';

  let count = 0;
  for (const fileName of PROTOTYPES) {
    const filePath = `${PROTOTYPE_DIR}\\${fileName}`;
    if (!readdirSync(PROTOTYPE_DIR).includes(fileName)) {
      console.warn(`⚠️  跳过不存在: ${fileName}`);
      continue;
    }

    const url = `file:///${filePath.replace(/\\/g, '/')}`;
    process.stdout.write(`📸 ${fileName} ... `);
    await page.goto(url);
    await page.addStyleTag({ content: hideStyle });
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(300); // 等待字体渲染
    const screenshot = await page.screenshot({ type: 'png' });
    const snapshotName = fileName.replace(/\.html$/, '');
    const outDir = path.join(
      process.cwd(),
      'tests/visual-baseline/__snapshots__',
    );
    mkdirSync(outDir, { recursive: true });
    const outPath = path.join(
      outDir,
      `${snapshotName}-chromium-win32.png`,
    );
    writeFileSync(outPath, screenshot);
    console.log(`✅ → ${path.basename(outPath)}`);
    count++;
  }

  await browser.close();
  console.log(`\n✅ 完成：生成了 ${count} 个 Layer 1 baseline 截图`);
  console.log(
    '📌 提示：将 tests/visual-baseline/__snapshots__/ 提交到 git，作为 Layer 1 真值。',
  );
}

main().catch((e) => {
  console.error('❌ 失败:', e.message);
  process.exit(1);
});
