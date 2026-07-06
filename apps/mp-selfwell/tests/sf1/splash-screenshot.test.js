/**
 * sf1/splash-screenshot.test.js
 * ────────────────────────────────────────────────────
 * SF1 page screenshot stub（miniprogram-automator mock）
 *
 * 真正的截图由 CI 上微信开发者工具的 automator 完成：
 *   const automator = require('miniprogram-automator');
 *   automator.launch({ cliPath: 'cli.bat', projectPath: '../' }).then(async mini => {
 *     await mini.navigateTo('/miniprogram/pages/splash/index');
 *     const img = await mini.screenshot();
 *     fs.writeFileSync('splash.png', img);
 *     // 与 docs/design/figma-pixso-spec/pages/01-splash.html 像素 diff ≤ 2%
 *   });
 *
 * 本地静态校验保证：脚本入口、脚本所引用的所有文件、IA-REF/FIGMA/API 三件套齐全。
 */

'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', '..', 'miniprogram');
const PAGE = 'splash';
const FILES = ['index.ts', 'index.wxml', 'index.wxss', 'index.json'];

let passed = 0;
let failed = 0;

function ok(label, cond, detail) {
  const tag = cond ? 'PASS' : 'FAIL';
  console.log(`[${tag}] ${label}${detail ? ` — ${detail}` : ''}`);
  if (cond) passed += 1;
  else failed += 1;
}

for (const f of FILES) {
  const p = path.join(ROOT, 'pages', PAGE, f);
  ok(`file exists: ${PAGE}/${f}`, fs.existsSync(p));
}
const ts = fs.readFileSync(path.join(ROOT, 'pages', PAGE, 'index.ts'), 'utf8');
ok('IA-REF header', ts.includes('IA-REF'));
ok('FIGMA header', ts.includes('FIGMA'));
ok('API header', ts.includes('API'));
ok('onLoad 入口', ts.includes('onLoad'));
ok('routed 锁', ts.includes('routed'));
ok('路由目标 home', ts.includes('/miniprogram/pages/home/index'));
ok('路由目标 login', ts.includes('/miniprogram/pages/login/index'));

const wxml = fs.readFileSync(path.join(ROOT, 'pages', PAGE, 'index.wxml'), 'utf8');
ok('wxml render class="splash"', wxml.includes('class="splash"'));
ok('wxml render logo "自愈"', wxml.includes('自愈'));
ok('wxml render tagline', wxml.includes('慢慢自律，慢慢成为更好的自己'));

console.log(`--- ${PAGE} screenshot stub: passed=${passed} failed=${failed}`);
process.exit(failed > 0 ? 1 : 0);
