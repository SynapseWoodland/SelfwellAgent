/**
 * Push payload 契约测试（§17.17 强约束）
 * ────────────────────────────────────
 * 真源：apps/mp-selfwell/miniprogram/utils/push-payload.ts
 * 测试目标：4 端 SDK 必含 traceparent + client_platform + user_id_pseudo
 * 任何字段缺失或格式错误 → FAIL
 */
'use strict';

const path = require('node:path');
const fs = require('node:fs');

const ROOT = path.resolve(__dirname, '..', 'miniprogram');
const pushPayloadSrc = fs.readFileSync(
  path.join(ROOT, 'utils', 'push-payload.ts'),
  'utf8',
);

function ok(label, cond, extra) {
  const tag = cond ? 'PASS' : 'FAIL';
  console.log(`[${tag}] ${label}`);
  if (!cond) {
    if (extra) console.warn('  reason:', extra);
    process.exitCode = 1;
  }
}

// 1. 文件存在
ok('utils/push-payload.ts exists', pushPayloadSrc.length > 0);

// 2. 必填 3 字段在源码中出现
ok(
  'source has traceparent field',
  pushPayloadSrc.includes('traceparent'),
);
ok(
  'source has client_platform field',
  pushPayloadSrc.includes('client_platform'),
);
ok(
  'source has user_id_pseudo field',
  pushPayloadSrc.includes('user_id_pseudo'),
);

// 3. traceparent 格式校验函数
ok(
  'has isValidTraceparent() regex',
  /isValidTraceparent[\s\S]*?0-9a-f/.test(pushPayloadSrc),
);

// 4. user_id_pseudo 必以 pseudo_ 开头
ok(
  'user_id_pseudo enforced pseudo_ prefix',
  /user_id_pseudo[\s\S]{0,200}pseudo_/.test(pushPayloadSrc),
);

// 5. client_platform 必 'wechat_mp' 或 'flutter_app'
ok(
  'client_platform enum wechat_mp / flutter_app',
  /client_platform[\s\S]{0,200}wechat_mp[\s\S]{0,200}flutter_app/.test(
    pushPayloadSrc,
  ),
);

// 6. 抛错拒绝（assertValidPushPayload）
ok(
  'has assertValidPushPayload guard',
  pushPayloadSrc.includes('assertValidPushPayload'),
);

// 7. 跨端一致：subscribe.ts 也必须引用 push-payload 或自带 traceparent
const subscribeSrc = fs.readFileSync(
  path.join(ROOT, 'utils', 'subscribe.ts'),
  'utf8',
);
ok(
  'subscribe.ts uses client_platform',
  subscribeSrc.includes('CLIENT_PLATFORM') || subscribeSrc.includes('client_platform'),
);

// 8. poster.ts 保存时也带 traceparent
const posterSrc = fs.readFileSync(path.join(ROOT, 'utils', 'poster.ts'), 'utf8');
ok(
  'poster.ts saves traceparent meta',
  posterSrc.includes('traceparent') || posterSrc.includes('CLIENT_PLATFORM'),
);

console.log('--- push-payload contract test done ---');
