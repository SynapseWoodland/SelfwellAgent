'use strict';
const fs = require('node:fs');
const path = require('node:path');
const root = 'd:/agent-project/SelfwellAgent/apps/mp-selfwell/miniprogram';
const FORBIDDEN = ['#FF4D4F', '#D32F2F', '#007BFF'];
const ALLOW_SUBSTRINGS = ['FORBIDDEN', '禁用色', '严禁', '禁止', 'forbiddenColors_NOTE'];

function walk(d) {
  const out = [];
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) out.push(...walk(p));
    else if (/\.(wxss|ts|json|wxml|js|wxs)$/.test(e.name)) out.push(p);
  }
  return out;
}

function buildIndexMap(text) {
  const allowed = new Array(text.length).fill(false);
  // 单行注释
  for (const m of text.matchAll(/\/\/[^\n]*/g)) {
    for (let i = m.index; i < m.index + m[0].length; i++) allowed[i] = true;
  }
  // 多行注释
  for (const m of text.matchAll(/\/\*[\s\S]*?\*\//g)) {
    for (let i = m.index; i < m.index + m[0].length; i++) allowed[i] = true;
  }
  // 整行包含"FORBIDDEN / 禁用色 / 严禁 / 禁止"关键字：把整行标为 allowed
  const lines = text.split('\n');
  let off = 0;
  for (const ln of lines) {
    if (ALLOW_SUBSTRINGS.some((kw) => ln.includes(kw))) {
      for (let i = off; i < off + ln.length; i++) allowed[i] = true;
    }
    off += ln.length + 1;
  }
  return allowed;
}

let hits = [];
for (const p of walk(root)) {
  const t = fs.readFileSync(p, 'utf8');
  const allowed = buildIndexMap(t);
  for (const c of FORBIDDEN) {
    let idx = 0;
    while ((idx = t.indexOf(c, idx)) !== -1) {
      if (!allowed[idx]) {
        hits.push(p.replace(/\\/g, '/') + ' :: ' + c + ' @col ' + idx);
        break;
      }
      idx += c.length;
    }
  }
}
console.log('forbidden-color hits:', hits.length);
for (const h of hits) console.log('  ' + h);
process.exit(hits.length > 0 ? 1 : 0);
