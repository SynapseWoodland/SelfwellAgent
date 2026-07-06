/**
 * sf1/login-screenshot.test.js
 * ────────────────────────────────────────────────────
 * 验证 login page 所有关键元素、IA-REF/FIGMA/API 三件套。
 * 真截图由 miniprogram-automator 在 CI 跑（绑定 cliPath + projectPath + pagePath）。
 */

'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', '..', 'miniprogram');
const PAGE = 'login';
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
ok('IA-REF', ts.includes('IA-REF'));
ok('FIGMA', ts.includes('FIGMA'));
ok('API', ts.includes('API'));
ok('调用 /auth/wx-login', ts.includes("'/auth/wx-login'"));
ok('持久化 user_id_pseudo', ts.includes('user_id_pseudo'));
ok('错误码映射 ERR_LABEL', ts.includes('ERR_LABEL'));

const wxml = fs.readFileSync(path.join(ROOT, 'pages', PAGE, 'index.wxml'), 'utf8');
ok('wxml 微信登录按钮 bindtap', wxml.includes('bindtap="onTapLogin"'));
ok('wxml 隐私 switch 绑定 onToggleAgree', wxml.includes('bindchange="onToggleAgree"'));
ok('wxml 主色 #A8C5B5', wxml.includes('#A8C5B5'));

console.log(`--- ${PAGE} screenshot stub: passed=${passed} failed=${failed}`);
process.exit(failed > 0 ? 1 : 0);
