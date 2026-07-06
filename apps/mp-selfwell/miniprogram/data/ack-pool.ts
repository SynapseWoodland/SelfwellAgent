/**
 * Selfwell · 30 条 ACK 温柔回复池（前端常驻副本）
 * ───────────────────────────────────────────
 * 真源：docs/data/ack-pool.yaml（后端 M4/M7/M5 兜底）
 * 同步策略：CI 比对 checksum；如真源变更，先 PR 更新此文件再 sync 后端
 *
 * 强约束（§17.15）：
 *  - 30 字内显示；超出截断 + 长按 tooltip
 *  - 颜色禁用：warm=薄荷/cream 暖色；neutral=白色；celebrate=浅 skyblue
 *  - 全部 30 条 valid=true
 */

export interface AckEntry {
  id: number;
  text: string;
  valid: boolean;
  tags: string[];
}

export const ACK_POOL: ReadonlyArray<AckEntry> = [
  { id: 1, text: '今天又迈出了一步，真的很棒。', valid: true, tags: ['鼓励', '打卡'] },
  { id: 2, text: '你愿意记录，就是改变的开始。', valid: true, tags: ['日记', '温柔'] },
  { id: 3, text: '每一个小动作，都在累积大改变。', valid: true, tags: ['鼓励', '打卡'] },
  { id: 4, text: '今天的你，比昨天更勇敢。', valid: true, tags: ['鼓励', '温柔'] },
  { id: 5, text: '记录本身就是一种力量，继续加油。', valid: true, tags: ['日记', '鼓励'] },
  { id: 6, text: '你的一天，值得被好好记住。', valid: true, tags: ['温柔', '接纳'] },
  { id: 7, text: '自律的路上，你并不孤单。', valid: true, tags: ['陪伴', '鼓励'] },
  { id: 8, text: '完成比完美更重要，你做到了。', valid: true, tags: ['打卡', '鼓励'] },
  { id: 9, text: '每一天的坚持，都在悄悄改变你。', valid: true, tags: ['鼓励', '陪伴'] },
  { id: 10, text: '你真的很努力，给自己一个大大的拥抱吧。', valid: true, tags: ['温柔', '鼓励'] },
  { id: 11, text: '不用和别人比，今天的你已经很好。', valid: true, tags: ['接纳', '温柔'] },
  { id: 12, text: '坚持的路上，偶尔休息也没关系。', valid: true, tags: ['温柔', '接纳'] },
  { id: 13, text: '谢谢你愿意分享，我听到了。', valid: true, tags: ['倾听', '温柔'] },
  { id: 14, text: '你的感受很重要，继续记录吧。', valid: true, tags: ['日记', '鼓励'] },
  { id: 15, text: '小小的坚持，藏着大大的力量。', valid: true, tags: ['鼓励', '打卡'] },
  { id: 16, text: '你已经走在正确的路上了。', valid: true, tags: ['鼓励', '温柔'] },
  { id: 17, text: '能坚持到这里，真的很厉害。', valid: true, tags: ['打卡', '鼓励'] },
  { id: 18, text: '每一天的点滴，都值得被珍惜。', valid: true, tags: ['温柔', '接纳'] },
  { id: 19, text: '你不需要完美，只需要坚持。', valid: true, tags: ['鼓励', '打卡'] },
  { id: 20, text: '我陪着你，一起慢慢来。', valid: true, tags: ['陪伴', '温柔'] },
  { id: 21, text: '自律是给自己的礼物，你值得。', valid: true, tags: ['鼓励', '温柔'] },
  { id: 22, text: '今天的小动作，做得很棒。', valid: true, tags: ['打卡', '鼓励'] },
  { id: 23, text: '不管今天怎样，明天又是新的开始。', valid: true, tags: ['接纳', '温柔'] },
  { id: 24, text: '你比自己想象的更强大。', valid: true, tags: ['鼓励', '温柔'] },
  { id: 25, text: '自律不是惩罚，是对自己的爱。', valid: true, tags: ['温柔', '接纳'] },
  { id: 26, text: '每一步都算数，继续加油。', valid: true, tags: ['鼓励', '打卡'] },
  { id: 27, text: '谢谢你坚持下来，拥抱一下自己。', valid: true, tags: ['温柔', '鼓励'] },
  { id: 28, text: '不管今天经历了什么，你都还在这里。', valid: true, tags: ['陪伴', '温柔'] },
  { id: 29, text: '你已经很努力了，给自己一点掌声吧。', valid: true, tags: ['鼓励', '温柔'] },
  { id: 30, text: '每一天都在成为更好的自己。', valid: true, tags: ['鼓励', '温柔'] },
];

/** 仅取 valid=true 的池（防御性过滤） */
export const ACK_VALID_POOL: ReadonlyArray<AckEntry> = ACK_POOL.filter((a) => a.valid);

/** 随机抽 1 条 */
export function pickRandomAck(): AckEntry {
  const pool = ACK_VALID_POOL;
  return pool[Math.floor(Math.random() * pool.length)];
}

/** 同步 checksum 校验（CI 比对） */
export const ACK_POOL_CHECKSUM = 'ack_pool_v1_30_entries_2026_07_06';
