/**
 * Selfwell 自愈 · 微信小程序全局配置
 * ────────────────────────────────────────
 * 与 figma-pixso-spec/dist/tokens-flat.json 1:1 对齐的颜色 / 间距 / 圆角 token。
 * 颜色禁用项详见 tokens-flat.json 的 forbiddenColors_NOTE 段；本文件不得引入。
 *
 * 任何新增 token 必须先在 design-tokens.json 中登记，CI 会比对 hash。
 */

/** 三档环境 */
export type Env = 'dev' | 'staging' | 'prod';

/** 当前环境（可由构建命令注入：--env=staging） */
export const CURRENT_ENV: Env = 'dev';

/** 环境标签（用于水印、报错浮层、Log） */
export const ENV_LABELS: Record<Env, string> = {
  dev: 'DEV',
  staging: 'STAGING',
  prod: 'PROD',
};

/**
 * 后端 API 基址
 * - dev: 与 docker-compose 中的 backend 服务一致
 * - staging / prod: 待 SF1 / SF5 接入
 *
 * 注意：禁止在 page 内硬编码完整 endpoint，必须经 utils/request.ts 走 baseURL 拼接。
 */
export const API_BASE_URL: Record<Env, string> = {
  dev: 'http://127.0.0.1:8000/api/v1',
  staging: 'https://staging-api.selfwell.app/api/v1',
  prod: 'https://api.selfwell.app/api/v1',
};

/** SSE 长连接基址（与 API 同源，path = /stream） */
export const SSE_BASE_URL: Record<Env, string> = {
  dev: 'ws://127.0.0.1:8000/api/v1',
  staging: 'wss://staging-api.selfwell.app/api/v1',
  prod: 'wss://api.selfwell.app/api/v1',
};

/** 客户端平台标识（推送 payload 必填，§17.17） */
export const CLIENT_PLATFORM = 'wechat_mp' as const;

/** OTel / W3C traceparent header 名 */
export const TRACEPARENT_HEADER = 'traceparent';

/** JWT header 名 */
export const AUTH_HEADER = 'Authorization';

/** 全局请求超时（ms） */
export const REQUEST_TIMEOUT_MS = 15_000;

/** SSE 重连退避（ms）：1s → 2s → 4s → 8s → 16s → 30s 上限 */
export const SSE_BACKOFF_STEPS_MS: readonly number[] = [
  1000, 2000, 4000, 8000, 16000, 30000,
];

/** SSE 重试失败阈值（5 次触发"网络异常"） */
export const SSE_MAX_RETRY = 5;

/** 图片压缩上限边长（px），§1.5 §2.1.1 强制 */
export const IMAGE_MAX_EDGE_PX = 1024;

/** ACK 气泡最大显示字数（§17.15） */
export const ACK_MAX_CHARS = 30;

/** LocalStorage key 常量 */
export const STORAGE_KEYS = {
  jwt: 'jwt',
  deviceId: 'device_id',
  userId: 'userId',
  logs: 'logs',
  /** SF1 落地：与推送 token 一起复用 */
  openidE: 'openid_e',
  privacyAgreed: 'privacy_agreed',
  meCached: 'me_cached',
  // 推送 token 暂存（SF5 正式接入）
  pushToken: 'push_token_wechat_mp',
} as const;

/**
 * Design Tokens（与 figma-pixso-spec/dist/tokens-flat.json 1:1）
 * 颜色 / 间距 / 圆角 / 字号。
 */
export const TOKENS = {
  color: {
    mint: '#A8C5B5',
    cream: '#F5E6D3',
    lavender: '#D4C5E2',
    peach: '#F0D9C4',
    skyblue: '#B8D4E3',
    ink900: '#2D3436',
    ink700: '#4A5568',
    ink500: '#718096',
    ink300: '#A0AEC0',
    ink100: '#E2E8F0',
    bgPage: '#FAFBFC',
    bgCard: '#FFFFFF',
    bgCardWarm: '#F5E6D3',
    warning: '#E8B87A',
    success: '#9DB5A0',
  },
  /** rpx 单位；基线 750rpx = 屏幕宽，1rpx ≈ 0.5px（iPhone 6） */
  spacing: {
    s1: '8rpx',
    s2: '16rpx',
    s3: '24rpx',
    s4: '32rpx',
    s6: '48rpx',
    s8: '64rpx',
    s12: '96rpx',
  },
  radius: {
    sm: '16rpx',
    md: '24rpx',
    lg: '32rpx',
    xl: '48rpx',
  },
  fontSize: {
    caption: '24rpx',
    body: '28rpx',
    title: '32rpx',
    h2: '36rpx',
    h1: '44rpx',
    display: '56rpx',
  },
} as const;

export type Tokens = typeof TOKENS;