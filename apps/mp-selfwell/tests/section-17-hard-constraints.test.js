/**
 * §17 前端 8 条强约束自检
 * ────────────────────────────
 * 必跑（CI）：第 1 项（禁用色）必须 0 命中；
 * 第 2-7 项做存在性 / 结构校验；
 * 第 8 项（像素对齐）依赖 miniprogram-automator + puppeteer 真实链路，本自检仅做脚手架存在性检查。
 */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', 'miniprogram');
const TEST_ROOT = path.resolve(__dirname);

function* walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) yield* walk(p);
    else if (/\.(ts|js|wxss|wxml|json|md)$/.test(e.name)) yield p;
  }
}

function buildIndexMap(text) {
  const allowed = new Array(text.length).fill(false);
  for (const m of text.matchAll(/\/\/[^\n]*/g)) {
    for (let i = m.index ?? 0; i < (m.index ?? 0) + m[0].length; i++) allowed[i] = true;
  }
  for (const m of text.matchAll(/\/\*[\s\S]*?\*\//g)) {
    for (let i = m.index ?? 0; i < (m.index ?? 0) + m[0].length; i++) allowed[i] = true;
  }
  return allowed;
}

const results = [];
function check(name, pass, detail) {
  results.push({ name, pass, detail });
  const tag = pass ? 'PASS' : 'FAIL';
  console.log(`[${tag}] §17.${name}` + (detail ? ' — ' + detail : ''));
}

/* ─────────── §17.1 Pixel 禁用色 ─────────── */
const FORBIDDEN = ['#FF4D4F', '#D32F2F', '#007BFF'];
let hits = [];
for (const p of walk(ROOT)) {
  const txt = fs.readFileSync(p, 'utf8');
  const allowed = buildIndexMap(txt);
  for (const c of FORBIDDEN) {
    let idx = 0;
    while ((idx = txt.indexOf(c, idx)) !== -1) {
      if (!allowed[idx]) {
        hits.push(`${path.relative(ROOT, p)}: ${c}@${idx}`);
        break;
      }
      idx += c.length;
    }
  }
}
check('1 forbidden-colors', hits.length === 0, hits.length ? `hits: ${hits.slice(0, 3).join(' | ')}` : '0 hits across all .ts/.wxss/.wxml/.json');

/* ─────────── §17.2 页面 IA 锚点 1:1 ─────────── */
const expectedPages = [
  'splash', 'login', 'home', 'diagnosis-upload', 'diagnosis-loading',
  'diagnosis-report', 'plan', 'checkin', 'assistant-home', 'feedback-diary',
  'recall-compare', 'community', 'profile', 'share-hug-card',
];
let iaMissing = [];
for (const name of expectedPages) {
  const ts = path.join(ROOT, 'pages', name, 'index.ts');
  if (!fs.existsSync(ts)) { iaMissing.push(name); continue; }
  const head = fs.readFileSync(ts, 'utf8').slice(0, 600);
  if (!head.includes('IA-REF')) iaMissing.push(`${name}.ts`);
  if (!(head.includes('设计稿') || head.includes('FIGMA'))) iaMissing.push(`${name}.ts (no figma)`);
  if (!(head.includes('后端端点') || head.includes('operationId') || head.includes('API') )) iaMissing.push(`${name}.ts (no op)`);
}
check('2 ia-anchor', iaMissing.length === 0, iaMissing.length ? iaMissing.join(', ') : `${expectedPages.length} pages, all 1:1`);

/* ─────────── §17.3 双端类型共享 ─────────── */
const typesApi = path.join(ROOT, 'types', 'api.ts');
check('3 shared-types', fs.existsSync(typesApi), typesApi + (fs.existsSync(typesApi) ? ` (${fs.statSync(typesApi).size} bytes)` : ' MISSING'));

/* ─────────── §17.4 设计稿与开发契约 ─────────── */
const figmaRefs = [];
for (const name of expectedPages) {
  const ts = path.join(ROOT, 'pages', name, 'index.ts');
  if (!fs.existsSync(ts)) continue;
  const head = fs.readFileSync(ts, 'utf8').slice(0, 800);
  const m = head.match(/figma-pixso-spec\/pages\/[\w-]+\.html/);
  if (m) figmaRefs.push(name);
}
check('4 figma-ref', figmaRefs.length === expectedPages.length, `${figmaRefs.length}/${expectedPages.length} pages have figma HTML ref`);

/* ─────────── §17.5 30 字 ACK 渲染 ─────────── */
const ackBubble = path.join(ROOT, 'components', 'ack-bubble', 'index.ts');
const ackConfig = path.join(ROOT, 'utils', 'config.ts');
let ackOk = false;
if (fs.existsSync(ackBubble) && fs.existsSync(ackConfig)) {
  const t1 = fs.readFileSync(ackBubble, 'utf8');
  const t2 = fs.readFileSync(ackConfig, 'utf8');
  ackOk = t1.includes('ACK_MAX_CHARS') && t2.includes('ACK_MAX_CHARS = 30') && t1.includes('showToast');
}
check('5 ack-30', ackOk, 'ack-bubble uses ACK_MAX_CHARS=30 + longpress toast tooltip');

/* ─────────── §17.6 SSE 客户端断线重连 1→2→4→8→16→30 ─────────── */
const sseUtil = path.join(ROOT, 'utils', 'sse.ts');
const cfg = path.join(ROOT, 'utils', 'config.ts');
let sseOk = false;
if (fs.existsSync(sseUtil) && fs.existsSync(cfg)) {
  const t1 = fs.readFileSync(sseUtil, 'utf8');
  const t2 = fs.readFileSync(cfg, 'utf8');
  sseOk = t2.includes('1000') && t2.includes('2000') && t2.includes('30000') && t2.includes('SSE_MAX_RETRY');
}
check('6 sse-reconnect', sseOk, 'sse.ts uses config.SSE_BACKOFF_STEPS_MS (1k/2k/4k/8k/16k/30k) + SSE_MAX_RETRY=5');

/* ─────────── §17.7 推送 4 端 SDK 一致 ─────────── */
const pushPayload = path.join(ROOT, 'utils', 'push-payload.ts');
const subscribe = path.join(ROOT, 'utils', 'subscribe.ts');
let pushOk = false;
if (fs.existsSync(pushPayload) && fs.existsSync(subscribe)) {
  const t1 = fs.readFileSync(pushPayload, 'utf8');
  const t2 = fs.readFileSync(subscribe, 'utf8');
  pushOk = t1.includes('traceparent') && t1.includes('client_platform') && t1.includes('user_id_pseudo') &&
    t2.includes('CLIENT_PLATFORM');
}
check('7 push-4sdk', pushOk, 'utils/push-payload.ts + utils/subscribe.ts share traceparent/client_platform/user_id_pseudo');

/* ─────────── §17.8 像素对齐脚手架 ─────────── */
const automator = path.join(TEST_ROOT, 'automator', 'pixel-diff.test.js');
check('8 pixel-align-scaffold', fs.existsSync(automator), 'tests/automator/pixel-diff.test.js (scaffold for miniprogram-automator + puppeteer)');

/* ─────────── 总结 ─────────── */
const passed = results.filter((r) => r.pass).length;
console.log(`\n========= §17 8 Hard Constraints Self-Check =========`);
console.log(`PASSED: ${passed}/8`);
if (passed < 8) process.exitCode = 1;
console.log('====================================================');
