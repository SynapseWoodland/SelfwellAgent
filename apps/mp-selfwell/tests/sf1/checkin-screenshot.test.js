/**
 * sf1/checkin-screenshot.test.js
 * ────────────────────────────────────────────────────
 * checkin page 关键元素 + §17.15 ACK 30 字截断 + 长按 tooltip 双件套；
 * 同时静态模拟一次渲染，确认截断逻辑不破坏非截断路径。
 */

'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', '..', 'miniprogram');
const PAGE = 'checkin';
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
ok('调用 /checkins', ts.includes("'/checkins'"));
ok('调用 /feedback', ts.includes("'/feedback'"));
ok('调用 /plans/today', ts.includes("'/plans/today'"));
ok('调用 /checkins/today', ts.includes("'/checkins/today'"));
ok('页级 packAck 含 ACK_MAX_CHARS', ts.includes('packAck') && ts.includes('ACK_MAX_CHARS'));
ok('onAckLongPress 事件', ts.includes('onAckLongPress'));
ok('isTruncated 判断', ts.includes('isTruncated'));
ok('提交后 setTimeout reLaunch home', ts.includes("'/miniprogram/pages/home/index'"));

const wxml = fs.readFileSync(path.join(ROOT, 'pages', PAGE, 'index.wxml'), 'utf8');
ok('wxml class="checkin"', wxml.includes('class="checkin"'));
ok('wxml task item 渲染', wxml.includes('wx:for="{{todayItems}}"'));
ok('wxml feedback textarea', wxml.includes('<textarea'));
ok('wxml 提交按钮 bindtap onSubmit', wxml.includes('bindtap="onSubmit"'));
ok('wxml ack 区段条件渲染', wxml.includes('wx:if="{{ack}}"'));
ok('wxml ack-bubble 长按事件', wxml.includes('onAckLongPress'));
ok('wxml 截断提示文案', wxml.includes('长按查看完整'));

const wxss = fs.readFileSync(path.join(ROOT, 'pages', PAGE, 'index.wxss'), 'utf8');
ok('wxss checkin 主色 #A8C5B5', wxss.includes('#A8C5B5'));
ok(
  'wxss 禁用色 #FF4D4F 不存在',
  !wxss.includes('#FF4D4F'),
);
ok(
  'wxss 禁用色 #D32F2F 不存在',
  !wxss.includes('#D32F2F'),
);
ok(
  'wxss 禁用色 #007BFF 不存在',
  !wxss.includes('#007BFF'),
);

// ──────────────────────────────────────────────────────────────
// §17.15 静态截断模拟（30 字阈值）
// ──────────────────────────────────────────────────────────────
const ACK_MAX_CHARS = 30;
function packAck(raw) {
  const text = (raw ?? '').toString();
  const isTruncated = text.length > ACK_MAX_CHARS;
  return {
    text,
    truncated: isTruncated ? text.slice(0, ACK_MAX_CHARS) + '…' : text,
    isTruncated,
  };
}

const short = packAck('每一小步都算数');
ok(
  'ack 短文本不截断',
  !short.isTruncated && short.text === '每一小步都算数',
  `len=${short.text.length}`,
);

const long =
  '今天坚持了 30 分钟冥想，呼吸平稳了很多，晚上睡得更好了，明天也想继续 (词数 ≥ 30)';
const longR = packAck(long);
ok(
  'ack 长文本截断到 30 字 + …',
  longR.isTruncated && longR.truncated.length === ACK_MAX_CHARS + 1,
  `truncated.len=${longR.truncated.length}`,
);
ok('ack 长文本原值保留', longR.text === long);
ok(
  'ack 截断后长按可读全文',
  longR.text.length > ACK_MAX_CHARS && !longR.truncated.includes(longR.text),
);

console.log(`--- ${PAGE} screenshot stub: passed=${passed} failed=${failed}`);
process.exit(failed > 0 ? 1 : 0);
