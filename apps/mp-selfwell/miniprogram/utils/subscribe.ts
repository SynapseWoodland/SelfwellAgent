/**
 * Selfwell · 订阅消息（推送授权）封装
 * ──────────────────────────────────
 * 用法（M4/M8 推送）：
 *   const ok = await subscribeMessages(['M4_checkin', 'M8_recall']);
 *
 * 约束（§17.17）：
 *  - 推送 payload 必须含 traceparent + client_platform=wechat_mp + user_id_pseudo
 *  - 用户拒绝时返回 false，不抛异常；上层负责降级到 in-app 提醒
 *
 * 注：tplId 来自业务方配置（暂未注入）。本 Sprint 仅暴露类型与最小可用封装。
 */

import { CLIENT_PLATFORM } from './config';

export type WxTemplateId =
  | 'checkin_remind' // M4
  | 'recall_card' // M8
  | 'plan_milestone' // M4
  | 'community_reply'; // M6

export interface SubscribeResult {
  /** 模板 ID */
  templateId: WxTemplateId;
  /** 是否同意（accept / reject / ban / filter） */
  status: 'accept' | 'reject' | 'ban' | 'filter' | 'unknown';
}

/**
 * 调起客户端订阅弹窗；返回每条模板的授权结果。
 * 注：wx.requestSubscribeMessage 一次性最多 3 个模板 id。
 */
export async function subscribeMessages(
  templateIds: WxTemplateId[],
): Promise<SubscribeResult[]> {
  if (!templateIds.length) return [];
  const ids = templateIds as unknown as string[];
  return new Promise((resolve) => {
    wx.requestSubscribeMessage({
      tmplIds: ids,
      success: (res) => {
        const out: SubscribeResult[] = templateIds.map((id) => {
          const status = (res[id] ?? 'unknown') as SubscribeResult['status'];
          return { templateId: id, status };
        });
        resolve(out);
      },
      fail: (err) => {
        console.warn('[subscribe] fail', err);
        resolve(templateIds.map((id) => ({ templateId: id, status: 'unknown' })));
      },
    });
  });
}

/**
 * 把授权结果上报到后端 /users/push-token 风格的 endpoint
 * （具体接口在 SF5 接入，先保留函数签名）
 */
export async function reportSubscribeResults(
  results: SubscribeResult[],
): Promise<void> {
  // 简化版：仅 console 打印 + 本地缓存；SF5 接入真实 endpoint
  try {
    wx.setStorageSync('subscribe_results', JSON.stringify(results));
  } catch {
    /* ignore */
  }
  // 业务字段预填，便于 SF5 直接消费
  const payload = {
    client_platform: CLIENT_PLATFORM,
    results,
    reported_at: new Date().toISOString(),
  };
  console.log('[subscribe] report payload', payload);
}