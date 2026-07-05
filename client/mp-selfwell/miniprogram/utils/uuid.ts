/**
 * 轻量 uuid v4（不依赖 crypto.randomUUID，兼容微信基础库 2.x）
 * 仅供 SF0 客户端自生成 device_id 临时使用；后续 SF1 接入 unionid 后弃用。
 */
export function uuidv4(): string {
  const hex = '0123456789abcdef';
  let s = '';
  for (let i = 0; i < 36; i++) {
    if (i === 8 || i === 13 || i === 18 || i === 23) {
      s += '-';
    } else if (i === 14) {
      s += '4';
    } else if (i === 19) {
      // variant 10xx
      s += hex[(Math.random() * 4) | (8 + 0)];
    } else {
      s += hex[(Math.random() * 16) | 0];
    }
  }
  return s;
}