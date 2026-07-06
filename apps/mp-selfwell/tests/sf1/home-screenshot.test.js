/**
 * sf1/home-screenshot.test.js
 * ────────────────────────────────────────────────────
 * 验证 home page + 引入的 progress-ring / task-card 组件；
 * 三接口并发（/users/me + /checkins/today + /plans/today）；
 * _inFlight 防重叠 + 30 字截断兜底由 checkin 验证（见 sf1/checkin）。
 */

'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', '..', 'miniprogram');
const PAGE = 'home';
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
ok('GET /users/me', ts.includes("'/users/me'"));
ok('GET /checkins/today', ts.includes("'/checkins/today'"));
ok('GET /plans/today', ts.includes("'/plans/today'"));
ok('Promise.allSettled 容错', ts.includes('Promise.allSettled'));
ok('_inFlight 重入锁', ts.includes('_inFlight'));
ok('streak clamp [0, 9999]', /Math\.max\(0,\s*Math\.min\(9999/.test(ts));

const wxml = fs.readFileSync(path.join(ROOT, 'pages', PAGE, 'index.wxml'), 'utf8');
ok('wxml home class', wxml.includes('class="home"'));
ok('wxml greeting 渲染', wxml.includes('{{greeting}}'));
ok('wxml streak 渲染', wxml.includes('{{streak}}'));
ok('wxml progress-ring 组件', wxml.includes('progress-ring'));
ok('wxml task-card 组件', wxml.includes('task-card'));
ok('wxml 主按钮 onGotoCheckin', wxml.includes('bindtap="onGotoCheckin"'));
ok('wxml 副按钮 onGotoAssistant', wxml.includes('bindtap="onGotoAssistant"'));

const json = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'pages', PAGE, 'index.json'), 'utf8'),
);
ok(
  'json usingComponents progress-ring',
  typeof json.usingComponents['progress-ring'] === 'string',
);
ok(
  'json usingComponents task-card',
  typeof json.usingComponents['task-card'] === 'string',
);

console.log(`--- ${PAGE} screenshot stub: passed=${passed} failed=${failed}`);
process.exit(failed > 0 ? 1 : 0);
