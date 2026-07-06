/**
 * utils/error-code.ts — Selfwell · 错误码 → 中文 toast 映射
 * ─────────────────────────────────────────────────────────
 * 与 docs/api/error-codes.md 1:1 对齐；SF1 仅登录链路使用。
 * 类型版本联调：金标 (E_AUTH_*) / 输入校验 (E_USER_INVALID_INPUT) / 限流 (E_RATE_LIMIT)。
 *
 * 用途：在 page 的 catch 中根据 e.code 找到对应的中文提示，避免裸英文错误回传用户。
 */

export const ERR_LABEL: Record<string, string> = {
  E_AUTH_WX_CODE_INVALID: '登录凭证已过期，请重试',
  E_AUTH_TOKEN_EXPIRED: '登录已过期，请重新登录',
  E_USER_INVALID_INPUT: '输入有误，请检查后重试',
  E_RATE_LIMIT: '操作太频繁，请稍后再试',
  E_INTERNAL: '服务异常，请稍后再试',
  NETWORK_ERROR: '网络异常，请检查后重试',
};

export function friendlyMessage(err: unknown, fallback = '操作失败，请稍后再试'): string {
  if (err && typeof err === 'object' && 'code' in err) {
    const code = String((err as { code: unknown }).code);
    if (ERR_LABEL[code]) return ERR_LABEL[code];
  }
  if (err instanceof Error) return err.message || fallback;
  return fallback;
}
