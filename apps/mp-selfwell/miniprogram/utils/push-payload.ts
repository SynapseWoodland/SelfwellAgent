/**
 * Selfwell · 推送 Payload 契约（§17.17 强约束）
 * ───────────────────────────────────────────────
 * 每次推送 / 上报订阅状态时，payload 必含：
 *   1) traceparent       W3C 格式：00-<32 hex>-<16 hex>-<2 hex>
 *   2) client_platform   必 'wechat_mp'
 *   3) user_id_pseudo    脱敏后的 user id
 *
 * 4 端 SDK（apns/fcm/hms/email）共用本文件，CI 跑 utils/__tests__/push-payload.test.js
 * 比对真源 packages/i18n/zh-CN.json::push_template_* 文案。
 */

import { CLIENT_PLATFORM, STORAGE_KEYS } from './config';

const HEX = '0123456789abcdef';
const seg = (n: number) => {
  let s = '';
  for (let i = 0; i < n; i++) s += HEX[(Math.random() * 16) | 0];
  return s;
};

/** 生成 W3C traceparent（与 utils/request.ts 保持一致） */
export function buildTraceparent(): string {
  return `00-${seg(32)}-${seg(16)}-01`;
}

/** 推送 Payload 必填字段 */
export interface PushPayload {
  traceparent: string;
  client_platform: typeof CLIENT_PLATFORM;
  user_id_pseudo: string;
  /** 业务字段：模板 id（来自 packages/i18n） */
  template_id: string;
  /** 业务字段：openid 或 device token */
  recipient_token: string;
  /** 业务字段：模板参数（key-value，key 必在 zh-CN.json 登记） */
  template_params: Record<string, string>;
  /** 业务字段：触发场景（M4/M7/M8/...） */
  scene: 'checkin_remind' | 'recall_card' | 'plan_milestone' | 'community_reply' | 'other';
  /** 业务字段：触发时间（ISO 8601） */
  triggered_at: string;
}

/** 取脱敏 user id（user_id.slice(-6)，与 §17.10 一致） */
export function getPseudoUserId(): string {
  try {
    const raw = wx.getStorageSync(STORAGE_KEYS.userId) || '';
    return raw ? `pseudo_${raw.slice(-6)}` : 'pseudo_anon';
  } catch {
    return 'pseudo_anon';
  }
}

/** 校验 traceparent 格式 */
export function isValidTraceparent(tp: string): boolean {
  return /^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$/.test(tp);
}

/** 构造推送 payload（强制 3 个必填字段） */
export function buildPushPayload(
  partial: Omit<PushPayload, 'traceparent' | 'client_platform' | 'user_id_pseudo' | 'triggered_at'>,
): PushPayload {
  return {
    traceparent: buildTraceparent(),
    client_platform: CLIENT_PLATFORM,
    user_id_pseudo: getPseudoUserId(),
    triggered_at: new Date().toISOString(),
    ...partial,
  };
}

/** 校验既有 payload（任何渠道上报前调用；不通过则抛错拒绝） */
export function assertValidPushPayload(p: Partial<PushPayload>): asserts p is PushPayload {
  if (!p.traceparent || !isValidTraceparent(p.traceparent)) {
    throw new Error('push payload: traceparent missing or invalid');
  }
  if (p.client_platform !== 'wechat_mp' && p.client_platform !== 'flutter_app') {
    throw new Error(`push payload: client_platform invalid (${p.client_platform})`);
  }
  if (!p.user_id_pseudo || !p.user_id_pseudo.startsWith('pseudo_')) {
    throw new Error('push payload: user_id_pseudo missing or not desensitized');
  }
  if (!p.template_id) {
    throw new Error('push payload: template_id missing');
  }
}
