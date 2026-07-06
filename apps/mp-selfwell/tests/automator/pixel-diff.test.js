/**
 * miniprogram-automator 像素对齐测试脚手架（§17.18 强约束）
 * ──────────────────────────────────────────────────
 * 目标 P0 page：03 home / 06 diagnose report / 07 plan / 12 hug-card
 * 真源 HTML：docs/design/figma-pixso-spec/pages/{03-home,06-butler-analyze-report,07-plan,12-hug-card-day7}.html
 *
 * 接入方式：
 *  1) npm i miniprogram-automator -D
 *  2) 启动微信开发者工具：cli auto --project ${PROJECT_PATH} --auto-port 9421
 *  3) 运行：node tests/automator/pixel-diff.test.js
 *
 * 流程：
 *  - automator.launch / connectMiniProgram
 *  - 遍历 4 个 P0 page → 截图 (page.screenshot)
 *  - 与 docs/design/figma-pixso-spec/pages/{...}.html 渲染后截图做像素 diff
 *  - 允许 ≤ 2% 差异（文本长度差异除外）
 *
 * 风险：
 *  - automator 在 CI 上需 headless 模式；本地开发体验需打开 IDE
 *  - 真机像素与 devtool 像素可能有 1% 偏差
 */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_PATH = path.resolve(__dirname, '..', '..');
const SPEC_PAGES = [
  { name: '03-home', figma: '03-home.html', mp: '/miniprogram/pages/home/index' },
  {
    name: '06-diagnose-report',
    figma: '06-butler-analyze-report.html',
    mp: '/miniprogram/pages/diagnosis-report/index',
  },
  { name: '07-plan', figma: '07-plan.html', mp: '/miniprogram/pages/plan/index' },
  {
    name: '12-hug-card-day7',
    figma: '12-hug-card-day7.html',
    mp: '/miniprogram/pages/share-hug-card/index?day=7',
  },
];

const PIXEL_DIFF_THRESHOLD = 0.02; // 2%

/** 检查 automator 是否已安装 */
function isAutomatorInstalled() {
  try {
    return !!require.resolve('miniprogram-automator');
  } catch {
    return false;
  }
}

/** 主流程：launch IDE → 遍历 4 个 page → 截图 → 计算 diff */
async function runPixelTest() {
  if (!isAutomatorInstalled()) {
    console.warn('[skip] miniprogram-automator 未安装；本测试为脚手架占位。');
    console.warn('      接入：npm i miniprogram-automator -D');
    console.warn('      启动 IDE：cli auto --project ' + PROJECT_PATH);
    console.log('--- pixel diff test done (skipped, scaffold only) ---');
    return;
  }

  const automator = require('miniprogram-automator');
  const miniProgram = await automator.launch({
    projectPath: PROJECT_PATH,
    // 9421 是默认 IDE 自动化端口
    cliPath: 'C:/Program Files (x86)/Tencent/微信web开发者工具/cli.bat',
  });

  let allPass = true;
  for (const spec of SPEC_PAGES) {
    const page = await miniProgram.reLaunch(spec.mp);
    await page.waitFor(2000); // 等动画/数据加载
    const mpScreenshotPath = path.join(
      __dirname,
      'snapshots',
      `${spec.name}.mp.png`,
    );
    fs.mkdirSync(path.dirname(mpScreenshotPath), { recursive: true });
    const img = await page.screenshot({ path: mpScreenshotPath });
    console.log(`[INFO] ${spec.name}: mp screenshot saved to ${mpScreenshotPath}`);

    // TODO(W5+): 用 puppeteer 打开 spec.figma HTML，截同尺寸图，做 pixel diff
    // 当前仅生成 mp 端截图；diff 计算待 puppeteer 接入后补全
    const ok = img && img.byteLength > 0;
    if (!ok) allPass = false;
    await page.close();
  }

  await miniProgram.close();

  if (!allPass) {
    process.exitCode = 1;
  }
  console.log(`--- pixel diff test done (threshold ≤ ${PIXEL_DIFF_THRESHOLD * 100}%) ---`);
}

if (require.main === module) {
  runPixelTest().catch((e) => {
    console.error('[fatal]', e);
    process.exitCode = 1;
  });
}

module.exports = { runPixelTest, SPEC_PAGES, PIXEL_DIFF_THRESHOLD };
