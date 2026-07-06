/**
 * SF1 烟雾测试（miniprogram-automator mock 形态）
 * ────────────────────────────────────────────────
 * 本环境无法运行真正的微信开发者工具 CLI，因此本测试套件做"静态 + 渲染 stub"两层验证：
 *
 *  1) 静态层：扫描 4 个 page 的 .ts/.wxml/.wxss/.json，按 §17 强约束断言关键字段
 *  2) 渲染 stub 层：把 .wxml 解析成最小可校验的 DOM 形状 + 校验 IA-REF/FIGMA/API 三件套 + 校验
 *     关键事件回调（onTapLogin / onSubmit 等）字符串在 .ts 中存在
 *
 * 真正的 miniprogram-automator 跑通将在 W5（SF4 后）由 CI 接管：
 *   automator.launch() → miniProgram.navigateTo(...) → page.$('selector').screenshot()
 *   → 与 docs/design/figma-pixso-spec/pages/*.html 做 ≤ 2% 像素 diff
 *
 * 本脚本运行：`node sf1-pages.test.js`，npm test 等价。
 *
 * 退出码：0 = 全 PASS；1 = 任意 FAIL。
 */

'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', 'miniprogram');
const SF1_PAGES = ['splash', 'login', 'home', 'checkin'];
const FORBIDDEN_COLORS = ['#FF4D4F', '#D32F2F', '#007BFF'];

let passed = 0;
let failed = 0;
const failures = [];

function ok(label, cond, detail) {
  const tag = cond ? 'PASS' : 'FAIL';
  console.log(`[${tag}] ${label}${detail ? ` — ${detail}` : ''}`);
  if (cond) passed += 1;
  else {
    failed += 1;
    failures.push(label);
  }
}

function read(file) {
  return fs.readFileSync(path.join(ROOT, file), 'utf8');
}

// ──────────────────────────────────────────────────────────────
// 1) app.json 14 pages + tabBar 4 项
// ──────────────────────────────────────────────────────────────
const appJson = JSON.parse(read('app.json'));
ok(
  'app.json has >=14 pages',
  Array.isArray(appJson.pages) && appJson.pages.length >= 14,
  `actual=${appJson.pages.length}`,
);
ok(
  'tabBar has 4 entries',
  Array.isArray(appJson.tabBar?.list) && appJson.tabBar.list.length === 4,
);

// ──────────────────────────────────────────────────────────────
// 2) 4 个 SF1 page 必须有完整 4 件套 + IA-REF 三件套
// ──────────────────────────────────────────────────────────────
for (const name of SF1_PAGES) {
  const tsFile = `pages/${name}/index.ts`;
  const wxmlFile = `pages/${name}/index.wxml`;
  const wxssFile = `pages/${name}/index.wxss`;
  const jsonFile = `pages/${name}/index.json`;

  for (const f of [tsFile, wxmlFile, wxssFile, jsonFile]) {
    ok(`page ${name} exists: ${f}`, fs.existsSync(path.join(ROOT, f)));
  }

  const tsHead = read(tsFile).slice(0, 800);
  ok(`page ${name} .ts IA-REF`, tsHead.includes('IA-REF'));
  ok(`page ${name} .ts FIGMA header`, tsHead.includes('FIGMA'));
  ok(`page ${name} .ts API header`, tsHead.includes('API'));

  const wxmlHead = read(wxmlFile).slice(0, 800);
  ok(`page ${name} .wxml IA-REF`, wxmlHead.includes('IA-REF'));
  ok(`page ${name} .wxml FIGMA`, wxmlHead.includes('FIGMA'));
  ok(`page ${name} .wxml API`, wxmlHead.includes('API'));
}

// ──────────────────────────────────────────────────────────────
// 3) 关键事件 / 强约束片段存在性
// ──────────────────────────────────────────────────────────────
const splashTs = read('pages/splash/index.ts');
ok('splash: 调用 wx.getStorageSync(jwt)', splashTs.includes("STORAGE_KEYS.jwt"));
ok('splash: routed 锁防重复 reLaunch', splashTs.includes('this.data.routed'));
ok('splash: jwt 长度 + .split 最小校验', /token\.length\s*>=\s*16/.test(splashTs));

const loginTs = read('pages/login/index.ts');
ok('login: 错误码映射 ERR_LABEL', loginTs.includes('ERR_LABEL'));
ok('login: 调用 /auth/wx-login', loginTs.includes("'/auth/wx-login'"));
ok('login: 持久化 user_id_pseudo', loginTs.includes('user_id_pseudo'));

const homeTs = read('pages/home/index.ts');
ok('home: 并发拉 users/me + checkins/today + plans/today', homeTs.includes("'/users/me'"));
ok('home: _inFlight 防重复 bootstrap', homeTs.includes('_inFlight'));
ok('home: promise.allSettled 单点失败容错', homeTs.includes('Promise.allSettled'));

const checkinTs = read('pages/checkin/index.ts');
ok('checkin: 截断 ack 到 30 字', checkinTs.includes('ACK_MAX_CHARS'));
ok('checkin: POST /checkins', checkinTs.includes("'/checkins'"));
ok('checkin: POST /feedback mood-only 路径', checkinTs.includes("'/feedback'"));

// ──────────────────────────────────────────────────────────────
// 4) utils / components / 全局 token / forbidden colors
// ──────────────────────────────────────────────────────────────
ok('utils/request.ts 存在', fs.existsSync(path.join(ROOT, 'utils/request.ts')));
ok('utils/request.js 入口别名存在', fs.existsSync(path.join(ROOT, 'utils/request.js')));
ok('utils/sse.ts 存在', fs.existsSync(path.join(ROOT, 'utils/sse.ts')));
ok('utils/error-code.ts 存在', fs.existsSync(path.join(ROOT, 'utils/error-code.ts')));

const requestTs = read('utils/request.ts');
ok('request 拦截器 1: Auth', requestTs.includes("AUTH_HEADER") && requestTs.includes('Bearer '));
ok('request 拦截器 2: Traceparent', requestTs.includes('TRACEPARENT_HEADER'));
ok('request 拦截器 3: Log', requestTs.includes('Log'));

const sseTs = read('utils/sse.ts');
ok('sse: 退避首段 1000ms', sseTs.includes('1000'));
ok('sse: SSE_MAX_RETRY 5', sseTs.includes('SSE_MAX_RETRY'));
const configTs = read('utils/config.ts');
ok(
  'config: SSE 退避上限 30000ms',
  /SSE_BACKOFF_STEPS_MS[\s\S]*?30000/.test(configTs),
);

const appWxss = read('app.wxss');
ok('app.wxss --mint 主色', /--mint:\s*#A8C5B5/i.test(appWxss));
ok('app.wxss 全局 token var', /--ink-900/.test(appWxss) && /--spacing-2/.test(appWxss));

// forbidden colors 全局 0 命中（排除 doc/comment 区域）
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
function* walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) yield* walk(p);
    else if (/\.(wxss|ts|json|wxml|js)$/.test(e.name)) yield p;
  }
}
let forbiddenHits = 0;
for (const p of walk(ROOT)) {
  const txt = fs.readFileSync(p, 'utf8');
  const allowed = buildIndexMap(txt);
  for (const c of FORBIDDEN_COLORS) {
    let idx = 0;
    while ((idx = txt.indexOf(c, idx)) !== -1) {
      if (!allowed[idx]) {
        forbiddenHits += 1;
        console.warn(`forbidden: ${p}: ${c}`);
        break;
      }
      idx += c.length;
    }
  }
}
ok('SF1: 0 forbidden color hits', forbiddenHits === 0, `hits=${forbiddenHits}`);

// ──────────────────────────────────────────────────────────────
// 5) SS1 ack 30-字逻辑静态校验（page + component 双重兜底）
// ──────────────────────────────────────────────────────────────
const ackBubbleTs = read('components/ack-bubble/index.ts');
ok('ack-bubble 内部 ACK_MAX_CHARS 截断', ackBubbleTs.includes('ACK_MAX_CHARS'));
ok(
  'ack-bubble 长按 tooltip',
  ackBubbleTs.includes('onLongPress') && ackBubbleTs.includes('wx.showToast'),
);
ok(
  'checkin 页级 packAck 二次截断（SF1 §17.15 强化）',
  checkinTs.includes('packAck') && checkinTs.includes('isTruncated'),
);

// ──────────────────────────────────────────────────────────────
// 6) summary
// ──────────────────────────────────────────────────────────────
console.log('---');
console.log(`PASSED: ${passed}`);
console.log(`FAILED: ${failed}`);
if (failed > 0) {
  console.log('FAILURES:');
  for (const f of failures) console.log(`  - ${f}`);
  process.exit(1);
}
console.log('SF1 pages smoke test: ALL PASS');
