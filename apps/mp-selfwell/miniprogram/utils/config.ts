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
  dev: 'https://husenlin.tail61999e.ts.net/api/v1',
  staging: 'https://staging-api.selfwell.app/api/v1',
  prod: 'https://api.selfwell.app/api/v1',
};

/** SSE 长连接基址（与 API 同源，path = /stream） */
export const SSE_BASE_URL: Record<Env, string> = {
  dev: 'wss://husenlin.tail61999e.ts.net/api/v1',
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
 * TabBar 配置常量（FE-FIX-06）
 * ────────────────────────────────────────
 * 真源：app.json tabBar.list（PR-3 commit-1 锁定 4 项）
 * 设计：页面内禁止硬编码 `/pages/...` 路径；统一通过 TAB_ROUTES 配置常量 + getTabUrl() 工厂读取。
 *
 * 用途：
 *  - assistant-home 的 fallbackToHomeTab() 等需要「跳 tabBar 兜底链」的场景
 *  - 未来 tabBar 重排（"今天" tab 路径变更）时，只改本常量即可
 *
 * 与 app.json tabBar 的关系：
 *  - app.json 真源不变（小程序 IDE 读取）；此处 TS 层镜像，便于：
 *    1. vitest 单测 + 静态分析校验
 *    2. 跨 page 文件常量引用
 *    3. 后续如增删 tabBar 项，自动 TS 编译报警
 */
export type TabId = 'butler' | 'today' | 'plaza' | 'profile';

export interface TabRoute {
  /** Tab 标识符（与小程序后台约定的语义键） */
  id: TabId;
  /** 微信小程序 pagePath（不含前导 `/`；与 wx.switchTab / app.json 兼容） */
  pagePath: string;
  /** 与 switchTab / navigateTo 拼接时使用的前导 `/` 路径 */
  url: string;
  /** Tab 标题（用于 _devLog / 调试） */
  text: string;
}

export const TAB_ROUTES: Readonly<Record<TabId, TabRoute>> = {
  butler: {
    id: 'butler',
    pagePath: 'pages/assistant-home/index',
    url: '/pages/assistant-home/index',
    text: '智能管家',
  },
  today: {
    id: 'today',
    pagePath: 'pages/home/index',
    url: '/pages/home/index',
    text: '今天',
  },
  plaza: {
    id: 'plaza',
    pagePath: 'pages/community/index',
    url: '/pages/community/index',
    text: '广场',
  },
  profile: {
    id: 'profile',
    pagePath: 'pages/profile-new/index',
    url: '/pages/profile-new/index',
    text: '我的',
  },
} as const;

/** getHomeTabUrl() = 「今天」tab 的稳定路径（FE-FIX-06 抽出）。
 *  - 若未来 tabBar 重排（如把"今天"tab 改名为"日记"），改 TAB_ROUTES.today.pagePath 即可，无需全局搜索替换。 */
export function getHomeTabUrl(): string {
  return TAB_ROUTES.today.url;
}

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