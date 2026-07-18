/**
 * 视频 URL 分类工具（v1.1）
 * ────────────────────────────────────────────────────────────────
 * 任务：判断 videoUrl 是「可直接播放」还是「外链引导」。
 *
 * 设计依据：docs/plan/视频外链跳转浏览器方案-v1.1.md
 *
 * 分类策略：
 *   - empty      : 空字符串 / 非字符串 / 纯空白 → 渲染占位
 *   - playable   : HTTPS mp4 / m3u8 / webm / mov + 白名单 CDN 域名
 *                  → 直接走 <video> 组件
 *   - external   : 其它（HTTPS 但域名非白名单 / xhslink 等短链 / 外部平台）
 *                  → 渲染「复制到浏览器」引导卡片
 *
 * 边界情况：
 *   - HTTP（非 HTTPS）→ external（小程序强制 HTTPS）
 *   - URL 解析异常 → external（保守兜底，不崩溃）
 *   - 域名大小写归一
 */

export type VideoUrlType = 'empty' | 'playable' | 'external';

/** 直链文件扩展名（走 <video> 组件）。 */
const DIRECT_EXTENSIONS = ['.mp4', '.m3u8', '.webm', '.mov', '.m4v'] as const;

/**
 * 可信赖的视频 CDN 域名白名单（自家 / 备案过的合规 CDN）。
 * 自录视频走自家 CDN 时在这里加一行。
 */
const PLAYABLE_HOSTS = [
  'cdn.selfwell.app',
  'media.selfwell.app',
  // 腾讯云点播默认域名（按需加）
  // 'xxxx.vod2.myqcloud.com',
] as const;

/**
 * 判定 videoUrl 类型。
 *
 * @example
 *   classifyVideoUrl('')                                  // 'empty'
 *   classifyVideoUrl('https://cdn.x.com/v.mp4')           // 'playable'
 *   classifyVideoUrl('https://www.bilibili.com/video/BV1')
 *                                                            // 'external'
 *   classifyVideoUrl('http://cdn.x.com/v.mp4')             // 'external' (http)
 *   classifyVideoUrl('https://xhslink.com/a/xxx')         // 'external'
 */
export function classifyVideoUrl(videoUrl: unknown): VideoUrlType {
  if (typeof videoUrl !== 'string') return 'empty';
  const url = videoUrl.trim();
  if (!url) return 'empty';

  // 1. 必须是 HTTPS（小程序 <video> / <web-view> 都强制 HTTPS）
  if (!url.toLowerCase().startsWith('https://')) return 'external';

  // 2. 尝试解析 URL
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return 'external';
  }
  const hostname = parsed.hostname.toLowerCase();
  if (!hostname) return 'external';

  // 3. 白名单域名 → playable
  if (PLAYABLE_HOSTS.some((h) => hostname === h || hostname.endsWith(`.${h}`))) {
    return 'playable';
  }

  // 4. 路径含直链扩展名 → playable
  const pathname = parsed.pathname.toLowerCase();
  if (DIRECT_EXTENSIONS.some((ext) => pathname.endsWith(ext))) {
    return 'playable';
  }

  // 5. 其它 → external（xhslink / bilibili / xiaohongshu / 抖音 / 快手等）
  return 'external';
}

/**
 * 提取纯主机名（用于埋点 / 提示文案）。
 * 解析失败返回空串。
 */
export function extractHost(videoUrl: string | undefined | null): string {
  if (!videoUrl) return '';
  try {
    return new URL(videoUrl).hostname.toLowerCase();
  } catch {
    return '';
  }
}