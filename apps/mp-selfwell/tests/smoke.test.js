/**
 * 烟雾测试样例 · 仅作占位
 * ─────────────────────
 * 真接入在 W5（miniprogram-automator）；SF0 仅本地手跑 / CI 用 mocha 跑过即可。
 *
 * 验证点：
 *  - miniprogram/ 目录存在
 *  - app.json 至少 14 项 pages
 *  - app.wxss 内未出现禁用色（#FF4D4F / #D32F2F / #007BFF）
 *  - 14 个 page 都含 IA-REF 注释头
 *  - 7 个 components 都存在
 *  - 4 个 utils 都存在
 *  - utils/config.ts 中 TOKENS.color.mint === '#A8C5B5'
 */

'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', 'miniprogram');
const FORBIDDEN_COLORS = ['#FF4D4F', '#D32F2F', '#007BFF'];

function ok(label, cond) {
  const tag = cond ? 'PASS' : 'FAIL';
  console.log(`[${tag}] ${label}`);
  if (!cond) process.exitCode = 1;
}

// 1. 目录存在
ok('miniprogram/ exists', fs.existsSync(ROOT));

// 2. app.json 至少 14 项 pages
const appJson = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'app.json'), 'utf8'),
);
ok('app.json has >=14 pages', Array.isArray(appJson.pages) && appJson.pages.length >= 14);
ok('tabBar has 4 entries', Array.isArray(appJson.tabBar?.list) && appJson.tabBar.list.length === 4);

// 3. 禁用色扫描（递归 .wxss / .ts / .json）
//    排除"说明禁用色"的注释行（FORBIDDEN/禁用色栅栏/docs 引用）
//    - TS 单行注释 // ...
//    - CSS / TS 多行注释 /* ... */
//    - 任何包含 FORBIDDEN / 禁用色 / 严禁 / 禁止使用 字样的行
function buildIndexMap(text) {
  // 标记每个字符位置是否处于"被允许的文档/注释"区域
  const allowed = new Array(text.length).fill(false);
  // TS 单行注释 // ... 至行尾
  for (const m of text.matchAll(/\/\/[^\n]*/g)) {
    for (let i = m.index ?? 0; i < (m.index ?? 0) + m[0].length; i++) allowed[i] = true;
  }
  // 多行注释 /* ... */
  for (const m of text.matchAll(/\/\*[\s\S]*?\*\//g)) {
    for (let i = m.index ?? 0; i < (m.index ?? 0) + m[0].length; i++) allowed[i] = true;
  }
  return allowed;
}

function* walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) yield* walk(p);
    else if (/\.(wxss|ts|json)$/.test(e.name)) yield p;
  }
}

let forbiddenHits = [];
for (const p of walk(ROOT)) {
  const txt = fs.readFileSync(p, 'utf8');
  const allowed = buildIndexMap(txt);
  for (const c of FORBIDDEN_COLORS) {
    let idx = 0;
    while ((idx = txt.indexOf(c, idx)) !== -1) {
      if (!allowed[idx]) {
        forbiddenHits.push(`${p}: ${c}`);
        break;
      }
      idx += c.length;
    }
  }
}
ok('no forbidden colors found (excluding FORBIDDEN docs)', forbiddenHits.length === 0);
if (forbiddenHits.length) console.warn(forbiddenHits.join('\n'));

// 4. 14 个 page 目录存在 + IA-REF 头
const expectedPages = [
  'splash',
  'login',
  'home',
  'diagnosis-upload',
  'diagnosis-loading',
  'diagnosis-report',
  'plan',
  'checkin',
  'assistant-home',
  'feedback-diary',
  'recall-compare',
  'community',
  'profile',
  'share-hug-card',
];
for (const name of expectedPages) {
  const tsFile = path.join(ROOT, 'pages', name, 'index.ts');
  if (!fs.existsSync(tsFile)) {
    ok(`page ${name} exists`, false);
    continue;
  }
  const head = fs.readFileSync(tsFile, 'utf8').slice(0, 400);
  const hasIA = head.includes('IA-REF');
  const hasDesign = head.includes('设计稿');
  const hasOp = head.includes('后端端点') || head.includes('operationId');
  ok(`page ${name} IA-REF header`, hasIA && hasDesign && hasOp);
}

// 5. 7 个 components
const expectedComponents = [
  'progress-ring',
  'task-card',
  'persona-bubble',
  'ack-bubble',
  'sse-progress',
  'image-uploader',
  'error-toast',
];
for (const name of expectedComponents) {
  const tsFile = path.join(ROOT, 'components', name, 'index.ts');
  ok(`component ${name} exists`, fs.existsSync(tsFile));
}

// 6. 4 个 utils
const expectedUtils = ['config.ts', 'request.ts', 'sse.ts', 'picker.ts', 'subscribe.ts'];
for (const name of expectedUtils) {
  const f = path.join(ROOT, 'utils', name);
  ok(`utils/${name} exists`, fs.existsSync(f));
}

// 7. config.ts token 校验
const configTs = fs.readFileSync(path.join(ROOT, 'utils', 'config.ts'), 'utf8');
ok('TOKENS.color.mint === #A8C5B5', configTs.includes("#A8C5B5"));
ok('SSE_BACKOFF_STEPS_MS 长度 >= 5', /SSE_BACKOFF_STEPS_MS[\s\S]*?1000/.test(configTs));
ok('ACK_MAX_CHARS === 30', /ACK_MAX_CHARS[\s\S]*?30/.test(configTs));

console.log('--- smoke test done ---');